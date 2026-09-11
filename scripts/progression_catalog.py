#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic progression catalogs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script execution predates the installable package.
    sys.path.insert(0, str(ROOT))

import midi_workflow  # noqa: E402
from guitar_practice.domain import progression as _domain  # noqa: E402

DEFAULT_CATALOG = ROOT / "catalogs" / "progressions" / "catalog.json"
CATALOG_VERSION = _domain.CATALOG_VERSION
ID_PATTERN = _domain.ID_PATTERN
ROMAN_PATTERN = _domain.ROMAN_PATTERN
DEGREE_SEMITONES = _domain.DEGREE_SEMITONES
SHARP_NAMES = _domain.SHARP_NAMES
FLAT_NAMES = _domain.FLAT_NAMES
FLAT_KEYS = _domain.FLAT_KEYS
KEY_ROOTS = _domain.KEY_ROOTS
NATURAL_TONAL_CENTERS = _domain.NATURAL_TONAL_CENTERS
MODAL_PARENT_OFFSETS = _domain.MODAL_PARENT_OFFSETS
CANONICAL_MAJOR_KEYS_BY_ROOT = _domain.CANONICAL_MAJOR_KEYS_BY_ROOT
CIRCLE_OF_FOURTHS_MAJOR = _domain.CIRCLE_OF_FOURTHS_MAJOR
CIRCLE_KEY_LOOKUP = _domain.CIRCLE_KEY_LOOKUP


class ProgressionError(_domain.ProgressionError, midi_workflow.ManifestError):
    """Legacy error type preserving the former MIDI-manifest compatibility."""


_string = _domain._string
_meter = _domain._meter
parse_change = _domain.parse_change
_validate_invariants = _domain._validate_invariants
_validate_modal_context = _domain._validate_modal_context
_normalized_major_key = _domain._normalized_major_key
_major_key_root = _domain._major_key_root
_natural_tonal_center = _domain._natural_tonal_center
_resolve_changes = _domain._resolve_changes
_resolve_preset_in_key = _domain._resolve_preset_in_key
_resolve_modal_preset = _domain._resolve_modal_preset
_canonical_circle_key = _domain._canonical_circle_key


def _translate(error: _domain.ProgressionError) -> ProgressionError:
    return ProgressionError(str(error))


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_catalog(catalog: dict[str, Any]) -> None:
    try:
        _domain.validate_catalog(catalog)
    except _domain.ProgressionError as error:
        raise _translate(error) from error


def get_preset(preset_id: str, path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    try:
        return _domain.get_preset(load_catalog(path), preset_id)
    except _domain.ProgressionError as error:
        raise _translate(error) from error


def expected_parent_major_key(mode: str, tonal_center: str) -> str:
    try:
        return _domain.expected_parent_major_key(mode, tonal_center)
    except _domain.ProgressionError as error:
        raise _translate(error) from error


def resolve_progression(
    preset_id: str,
    key_signature: str,
    path: Path = DEFAULT_CATALOG,
    *,
    tonal_center: str | None = None,
) -> list[str]:
    try:
        return _domain.resolve_progression(
            load_catalog(path),
            preset_id,
            key_signature,
            tonal_center=tonal_center,
        )
    except _domain.ProgressionError as error:
        raise _translate(error) from error


def resolve_circle_of_fourths(
    preset_id: str,
    *,
    start_key: str = "C",
    count: int = 12,
    path: Path = DEFAULT_CATALOG,
) -> list[dict[str, Any]]:
    try:
        return _domain.resolve_circle_of_fourths(
            load_catalog(path),
            preset_id,
            start_key=start_key,
            count=count,
        )
    except _domain.ProgressionError as error:
        raise _translate(error) from error


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
    resolve.add_argument("--tonal-center")
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
                "chords": resolve_progression(
                    args.preset_id,
                    args.key_signature,
                    tonal_center=args.tonal_center,
                ),
            }
            if args.tonal_center is not None:
                payload["tonal_center"] = args.tonal_center
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
