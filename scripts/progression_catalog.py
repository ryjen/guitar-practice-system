#!/usr/bin/env python3
"""Validate and resolve reusable chord-progression presets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import midi_workflow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "catalogs" / "progressions" / "catalog.json"
CATALOG_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ROMAN_PATTERN = re.compile(
    r"^(?P<accidental>[#b]?)(?P<degree>VII|VI|IV|III|II|V|I)(?P<quality>maj7|m7|7|5|m)?$"
)
DEGREE_SEMITONES = {
    "I": 0,
    "II": 2,
    "III": 4,
    "IV": 5,
    "V": 7,
    "VI": 9,
    "VII": 11,
}
SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
FLAT_KEYS = {"F", "BB", "EB", "AB", "DB", "GB", "CB"}
KEY_ROOTS = dict(midi_workflow.NOTE_NAMES)
KEY_ROOTS["CB"] = 11
CIRCLE_OF_FOURTHS_MAJOR = (
    "C",
    "F",
    "Bb",
    "Eb",
    "Ab",
    "Db",
    "Gb",
    "B",
    "E",
    "A",
    "D",
    "G",
)
CIRCLE_KEY_LOOKUP = {key.upper(): key for key in CIRCLE_OF_FOURTHS_MAJOR}
CIRCLE_KEY_LOOKUP["F#"] = "Gb"


class ProgressionError(midi_workflow.ManifestError):
    """Raised when a progression catalog entry is invalid."""


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _string(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProgressionError(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value) > maximum:
        raise ProgressionError(f"{name} must be at most {maximum} characters")
    return value


def _meter(value: Any, name: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ProgressionError(f"{name} must be [numerator, denominator]")
    numerator, denominator = value
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
        raise ProgressionError(f"{name} is unsupported")
    return [numerator, denominator]


def parse_change(change: str) -> tuple[int, str]:
    match = ROMAN_PATTERN.fullmatch(change)
    if match is None:
        raise ProgressionError(f"unsupported Roman-numeral change: {change!r}")
    accidental = match.group("accidental")
    offset = DEGREE_SEMITONES[match.group("degree")]
    if accidental == "#":
        offset += 1
    elif accidental == "b":
        offset -= 1
    quality = match.group("quality") or ""
    return offset % 12, quality


def _validate_invariants(preset: dict[str, Any]) -> None:
    invariants = preset.get("invariants")
    if invariants is None:
        return
    if not isinstance(invariants, dict):
        raise ProgressionError("invariants must be an object")
    unknown = set(invariants) - {"opening", "ending"}
    if unknown:
        raise ProgressionError(f"invariants has unsupported fields: {sorted(unknown)}")
    changes = preset["changes"]
    for name in ("opening", "ending"):
        expected = invariants.get(name)
        if expected is None:
            continue
        if not isinstance(expected, list) or not expected:
            raise ProgressionError(f"invariants.{name} must be a non-empty list")
        if any(not isinstance(change, str) for change in expected):
            raise ProgressionError(f"invariants.{name} must contain strings")
        actual = changes[: len(expected)] if name == "opening" else changes[-len(expected) :]
        if actual != expected:
            raise ProgressionError(
                f"preset {preset['id']!r} violates its {name} invariant: {actual}"
            )


def validate_catalog(catalog: dict[str, Any]) -> None:
    if not isinstance(catalog, dict):
        raise ProgressionError("catalog must be an object")
    if set(catalog) != {"version", "presets"}:
        raise ProgressionError("catalog must contain only version and presets")
    if catalog.get("version") != CATALOG_VERSION:
        raise ProgressionError(f"catalog.version must be {CATALOG_VERSION}")
    presets = catalog.get("presets")
    if not isinstance(presets, list) or not presets:
        raise ProgressionError("catalog.presets must be a non-empty list")

    ids: set[str] = set()
    for index, preset in enumerate(presets):
        if not isinstance(preset, dict):
            raise ProgressionError(f"presets[{index}] must be an object")
        allowed = {
            "id",
            "title",
            "family",
            "description",
            "bars",
            "meter",
            "changes",
            "tags",
            "invariants",
        }
        unknown = set(preset) - allowed
        if unknown:
            raise ProgressionError(
                f"presets[{index}] has unsupported fields: {sorted(unknown)}"
            )
        preset_id = _string(preset.get("id"), f"presets[{index}].id", 64)
        if not ID_PATTERN.fullmatch(preset_id):
            raise ProgressionError(f"invalid progression preset id: {preset_id!r}")
        if preset_id in ids:
            raise ProgressionError(f"duplicate progression preset id: {preset_id}")
        ids.add(preset_id)
        _string(preset.get("title"), f"presets[{index}].title", 120)
        _string(preset.get("family"), f"presets[{index}].family", 64)
        _string(preset.get("description"), f"presets[{index}].description", 300)
        bars = preset.get("bars")
        if isinstance(bars, bool) or not isinstance(bars, int) or not 1 <= bars <= 128:
            raise ProgressionError(f"presets[{index}].bars must be between 1 and 128")
        _meter(preset.get("meter"), f"presets[{index}].meter")
        changes = preset.get("changes")
        if not isinstance(changes, list) or len(changes) != bars:
            raise ProgressionError(
                f"preset {preset_id!r} must define exactly one change per bar"
            )
        for change in changes:
            if not isinstance(change, str):
                raise ProgressionError(f"preset {preset_id!r} changes must be strings")
            parse_change(change)
        tags = preset.get("tags")
        if (
            not isinstance(tags, list)
            or not tags
            or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
            or len(set(tags)) != len(tags)
        ):
            raise ProgressionError(f"preset {preset_id!r} tags must be unique strings")
        _validate_invariants(preset)


def get_preset(preset_id: str, path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    catalog = load_catalog(path)
    validate_catalog(catalog)
    for preset in catalog["presets"]:
        if preset["id"] == preset_id:
            return json.loads(json.dumps(preset))
    raise ProgressionError(f"unknown progression preset: {preset_id!r}")


def _major_key_root(key_signature: str) -> tuple[int, bool]:
    midi_workflow.key_signature_payload(key_signature)
    normalized = key_signature.strip().upper().replace("♭", "B").replace("♯", "#")
    normalized = normalized.replace("MIN", "M")
    if normalized.endswith("M"):
        raise ProgressionError(
            "progression presets currently require a major key signature"
        )
    if normalized not in KEY_ROOTS:
        raise ProgressionError(f"unsupported progression key: {key_signature!r}")
    return KEY_ROOTS[normalized], normalized in FLAT_KEYS


def _resolve_preset_in_key(
    preset: dict[str, Any],
    key_signature: str,
) -> list[str]:
    tonic, prefer_flats = _major_key_root(key_signature)
    names = FLAT_NAMES if prefer_flats else SHARP_NAMES
    chords: list[str] = []
    for change in preset["changes"]:
        offset, quality = parse_change(change)
        chord = f"{names[(tonic + offset) % 12]}{quality}"
        midi_workflow.chord_notes(chord)
        chords.append(chord)
    return chords


def resolve_progression(
    preset_id: str,
    key_signature: str,
    path: Path = DEFAULT_CATALOG,
) -> list[str]:
    preset = get_preset(preset_id, path)
    return _resolve_preset_in_key(preset, key_signature)


def _canonical_circle_key(key_signature: str) -> str:
    normalized = (
        _string(key_signature, "start_key", 8)
        .upper()
        .replace("♭", "B")
        .replace("♯", "#")
    )
    canonical = CIRCLE_KEY_LOOKUP.get(normalized)
    if canonical is None:
        raise ProgressionError(
            f"start_key must be one of {list(CIRCLE_OF_FOURTHS_MAJOR)} or F#"
        )
    return canonical


def resolve_circle_of_fourths(
    preset_id: str,
    *,
    start_key: str = "C",
    count: int = 12,
    path: Path = DEFAULT_CATALOG,
) -> list[dict[str, Any]]:
    """Resolve a progression through a bounded major-key circle-of-fourths traversal."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 12:
        raise ProgressionError("count must be an integer between 1 and 12")

    preset = get_preset(preset_id, path)
    canonical_start = _canonical_circle_key(start_key)
    start_index = CIRCLE_OF_FOURTHS_MAJOR.index(canonical_start)
    positions: list[dict[str, Any]] = []
    for offset in range(count):
        key_signature = CIRCLE_OF_FOURTHS_MAJOR[
            (start_index + offset) % len(CIRCLE_OF_FOURTHS_MAJOR)
        ]
        positions.append(
            {
                "key_signature": key_signature,
                "chords": _resolve_preset_in_key(preset, key_signature),
            }
        )
    return positions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("list")
    show = subparsers.add_parser("show")
    show.add_argument("preset_id")
    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("preset_id")
    resolve.add_argument("key_signature")
    fourths = subparsers.add_parser("fourths")
    fourths.add_argument("preset_id")
    fourths.add_argument("--start-key", default="C")
    fourths.add_argument("--count", type=int, default=12)
    args = parser.parse_args(argv)

    try:
        catalog = load_catalog()
        validate_catalog(catalog)
        if args.command == "validate":
            print(f"validated {len(catalog['presets'])} progression presets")
        elif args.command == "list":
            for preset in catalog["presets"]:
                print(preset["id"])
        elif args.command == "show":
            print(json.dumps(get_preset(args.preset_id), indent=2, sort_keys=True))
        elif args.command == "resolve":
            payload = {
                "preset": args.preset_id,
                "key_signature": args.key_signature,
                "chords": resolve_progression(args.preset_id, args.key_signature),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            positions = resolve_circle_of_fourths(
                args.preset_id,
                start_key=args.start_key,
                count=args.count,
            )
            payload = {
                "preset": args.preset_id,
                "traversal": "circle-of-fourths",
                "start_key": positions[0]["key_signature"],
                "count": len(positions),
                "positions": positions,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
    except (OSError, json.JSONDecodeError, ProgressionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
