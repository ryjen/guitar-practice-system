#!/usr/bin/env python3
"""Validate and inspect the deterministic groove preset catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import groove_engine
import midi_workflow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "catalogs" / "grooves" / "catalog.json"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require(value: Any, expected: type, name: str) -> Any:
    if not isinstance(value, expected):
        raise midi_workflow.ManifestError(f"{name} must be {expected.__name__}")
    return value


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_catalog(data)
    return data


def validate_catalog(data: dict[str, Any]) -> None:
    _require(data, dict, "catalog")
    if data.get("version") != 1:
        raise midi_workflow.ManifestError("catalog.version must be 1")
    presets = _require(data.get("presets"), list, "catalog.presets")
    if not presets:
        raise midi_workflow.ManifestError("catalog.presets cannot be empty")

    ids: set[str] = set()
    for index, preset in enumerate(presets):
        prefix = f"catalog.presets[{index}]"
        _require(preset, dict, prefix)
        preset_id = _require(preset.get("id"), str, f"{prefix}.id")
        if not ID_PATTERN.fullmatch(preset_id):
            raise midi_workflow.ManifestError(
                f"{prefix}.id must be lowercase kebab-case"
            )
        if preset_id in ids:
            raise midi_workflow.ManifestError(f"duplicate groove preset id: {preset_id}")
        ids.add(preset_id)

        _require(preset.get("title"), str, f"{prefix}.title")
        _require(preset.get("description"), str, f"{prefix}.description")
        meter = _require(preset.get("meter"), list, f"{prefix}.meter")
        if len(meter) != 2 or not all(
            isinstance(value, int) and not isinstance(value, bool) for value in meter
        ):
            raise midi_workflow.ManifestError(
                f"{prefix}.meter must be [numerator, denominator]"
            )
        numerator, denominator = meter
        if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
            raise midi_workflow.ManifestError(f"{prefix}.meter is unsupported")

        default_tempo = preset.get("default_tempo_bpm")
        if isinstance(default_tempo, bool) or not isinstance(default_tempo, int):
            raise midi_workflow.ManifestError(
                f"{prefix}.default_tempo_bpm must be an integer"
            )
        tempo_range = _require(
            preset.get("tempo_range_bpm"),
            list,
            f"{prefix}.tempo_range_bpm",
        )
        if len(tempo_range) != 2 or not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in tempo_range
        ):
            raise midi_workflow.ManifestError(
                f"{prefix}.tempo_range_bpm must be [min, max]"
            )
        minimum, maximum = tempo_range
        if not 20 <= minimum <= default_tempo <= maximum <= 300:
            raise midi_workflow.ManifestError(
                f"{prefix}.default_tempo_bpm must fall inside a 20..300 BPM range"
            )

        tags = _require(preset.get("tags"), list, f"{prefix}.tags")
        intents = _require(
            preset.get("practice_intents"),
            list,
            f"{prefix}.practice_intents",
        )
        if not tags or not all(isinstance(tag, str) and tag for tag in tags):
            raise midi_workflow.ManifestError(f"{prefix}.tags must contain strings")
        if not intents or not all(
            isinstance(intent, str) and intent for intent in intents
        ):
            raise midi_workflow.ManifestError(
                f"{prefix}.practice_intents must contain strings"
            )

        groove_engine.parse_groove(
            preset.get("groove"),
            meter=meter,
        )


def get_preset(
    preset_id: str,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = catalog if catalog is not None else load_catalog()
    for preset in source["presets"]:
        if preset["id"] == preset_id:
            return preset
    raise midi_workflow.ManifestError(f"unknown groove preset: {preset_id}")


def resolved_groove(
    preset_id: str,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an isolated GrooveSpec-shaped dictionary for the requested preset."""
    preset = get_preset(preset_id, catalog=catalog)
    return json.loads(json.dumps(preset["groove"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Path to groove catalog JSON",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("list")
    show = subparsers.add_parser("show")
    show.add_argument("preset_id")

    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "version": catalog["version"],
                        "presets": len(catalog["presets"]),
                        "ids": [preset["id"] for preset in catalog["presets"]],
                    },
                    indent=2,
                )
            )
        elif args.command == "list":
            print(
                json.dumps(
                    [
                        {
                            "id": preset["id"],
                            "title": preset["title"],
                            "meter": preset["meter"],
                            "default_tempo_bpm": preset["default_tempo_bpm"],
                            "tags": preset["tags"],
                        }
                        for preset in catalog["presets"]
                    ],
                    indent=2,
                )
            )
        else:
            print(json.dumps(get_preset(args.preset_id, catalog=catalog), indent=2))
    except (OSError, json.JSONDecodeError, midi_workflow.ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
