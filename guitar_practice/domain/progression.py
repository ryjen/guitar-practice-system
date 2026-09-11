"""Pure chord-progression catalog validation and harmonic resolution."""

from __future__ import annotations

import json
import re
from typing import Any

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
FLAT_KEYS = frozenset({"F", "BB", "EB", "AB", "DB", "GB", "CB"})
KEY_ROOTS = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "CB": 11,
}
MAJOR_KEY_SIGNATURES = frozenset(
    {"CB", "GB", "DB", "AB", "EB", "BB", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"}
)
NATURAL_TONAL_CENTERS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
MODAL_PARENT_OFFSETS = {
    "dorian": -2,
    "mixolydian": -7,
}
CANONICAL_MAJOR_KEYS_BY_ROOT = {
    0: "C",
    1: "Db",
    2: "D",
    3: "Eb",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "Ab",
    9: "A",
    10: "Bb",
    11: "B",
}
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


class ProgressionError(ValueError):
    pass


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


def _validate_modal_context(preset: dict[str, Any]) -> None:
    context = preset.get("modal_context")
    if context is None:
        return
    if not isinstance(context, dict) or set(context) != {"mode"}:
        raise ProgressionError("modal_context must contain only mode")
    mode = _string(context.get("mode"), "modal_context.mode", 32)
    if mode not in MODAL_PARENT_OFFSETS:
        raise ProgressionError(
            f"modal_context.mode must be one of {sorted(MODAL_PARENT_OFFSETS)}"
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
            "modal_context",
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
        _validate_modal_context(preset)
        _validate_invariants(preset)


def get_preset(catalog: dict[str, Any], preset_id: str) -> dict[str, Any]:
    validate_catalog(catalog)
    for preset in catalog["presets"]:
        if preset["id"] == preset_id:
            return json.loads(json.dumps(preset))
    raise ProgressionError(f"unknown progression preset: {preset_id!r}")


def _normalized_major_key(key_signature: str) -> str:
    if not isinstance(key_signature, str):
        raise ProgressionError(f"unsupported progression key: {key_signature!r}")
    normalized = key_signature.strip().upper().replace("♭", "B").replace("♯", "#")
    normalized = normalized.replace("MIN", "M")
    if normalized.endswith("M"):
        raise ProgressionError(
            "progression presets currently require a major key signature"
        )
    if normalized not in MAJOR_KEY_SIGNATURES or normalized not in KEY_ROOTS:
        raise ProgressionError(f"unsupported progression key: {key_signature!r}")
    return normalized


def _major_key_root(key_signature: str) -> tuple[int, bool]:
    normalized = _normalized_major_key(key_signature)
    return KEY_ROOTS[normalized], normalized in FLAT_KEYS


def _natural_tonal_center(tonal_center: str) -> tuple[str, int]:
    normalized = _string(tonal_center, "tonal_center", 8).upper()
    if normalized not in NATURAL_TONAL_CENTERS:
        raise ProgressionError(
            "tonal_center must be one of C, D, E, F, G, A, B in BackingTrackRequest v1"
        )
    return normalized, NATURAL_TONAL_CENTERS[normalized]


def expected_parent_major_key(mode: str, tonal_center: str) -> str:
    if mode not in MODAL_PARENT_OFFSETS:
        raise ProgressionError(f"unsupported modal context: {mode!r}")
    _, tonic = _natural_tonal_center(tonal_center)
    parent_root = (tonic + MODAL_PARENT_OFFSETS[mode]) % 12
    return CANONICAL_MAJOR_KEYS_BY_ROOT[parent_root]


def _resolve_changes(
    preset: dict[str, Any],
    *,
    tonic: int,
    prefer_flats: bool,
) -> list[str]:
    names = FLAT_NAMES if prefer_flats else SHARP_NAMES
    chords: list[str] = []
    for change in preset["changes"]:
        offset, quality = parse_change(change)
        chords.append(f"{names[(tonic + offset) % 12]}{quality}")
    return chords


def _resolve_preset_in_key(preset: dict[str, Any], key_signature: str) -> list[str]:
    tonic, prefer_flats = _major_key_root(key_signature)
    return _resolve_changes(preset, tonic=tonic, prefer_flats=prefer_flats)


def _resolve_modal_preset(
    preset: dict[str, Any],
    *,
    tonal_center: str,
    key_signature: str,
) -> list[str]:
    mode = preset["modal_context"]["mode"]
    normalized_tonal_center, tonic = _natural_tonal_center(tonal_center)
    expected_key = expected_parent_major_key(mode, normalized_tonal_center)
    requested_key = _normalized_major_key(key_signature)
    if requested_key != expected_key.upper():
        raise ProgressionError(
            f"{normalized_tonal_center} {mode} requires parent-major key signature "
            f"{expected_key}, not {key_signature.strip()}"
        )
    prefer_flats = requested_key in FLAT_KEYS
    return _resolve_changes(preset, tonic=tonic, prefer_flats=prefer_flats)


def resolve_progression(
    catalog: dict[str, Any],
    preset_id: str,
    key_signature: str,
    *,
    tonal_center: str | None = None,
) -> list[str]:
    preset = get_preset(catalog, preset_id)
    if "modal_context" in preset:
        if tonal_center is None:
            raise ProgressionError(
                f"modal progression preset {preset_id!r} requires tonal_center"
            )
        return _resolve_modal_preset(
            preset,
            tonal_center=tonal_center,
            key_signature=key_signature,
        )
    if tonal_center is not None:
        raise ProgressionError(
            f"tonal_center is only supported for modal progression presets, not {preset_id!r}"
        )
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
    catalog: dict[str, Any],
    preset_id: str,
    *,
    start_key: str = "C",
    count: int = 12,
) -> list[dict[str, Any]]:
    """Resolve a progression through a bounded major-key circle-of-fourths traversal."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 12:
        raise ProgressionError("count must be an integer between 1 and 12")

    preset = get_preset(catalog, preset_id)
    if "modal_context" in preset:
        raise ProgressionError("circle-of-fourths traversal does not accept modal presets")
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
