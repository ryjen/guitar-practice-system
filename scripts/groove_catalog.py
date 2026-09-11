#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic groove catalogs."""

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

from guitar_practice.domain import groove as _domain  # noqa: E402
from guitar_practice.domain import midi as _midi  # noqa: E402

DEFAULT_CATALOG = ROOT / "catalogs" / "grooves" / "catalog.json"
ID_PATTERN = _domain.ID_PATTERN
_require = _domain._require


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    _domain.validate_catalog(data)
    return data


def validate_catalog(data: dict[str, Any]) -> None:
    _domain.validate_catalog(data)


def get_preset(
    preset_id: str,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = catalog if catalog is not None else load_catalog()
    return _domain.get_preset(source, preset_id)


def resolved_groove(
    preset_id: str,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = catalog if catalog is not None else load_catalog()
    return _domain.resolved_groove(source, preset_id)


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
    except (OSError, json.JSONDecodeError, _midi.ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
