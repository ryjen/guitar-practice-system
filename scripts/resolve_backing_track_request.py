#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic BackingTrackRequest resolution."""

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

import midi_workflow as _midi_workflow  # noqa: E402
from guitar_practice.domain import backing_request as _domain  # noqa: E402

midi_workflow = _midi_workflow
REQUEST_VERSION = _domain.REQUEST_VERSION
ID_PATTERN = _domain.ID_PATTERN
SUPPORTED_INSTRUMENTATION = _domain.SUPPORTED_INSTRUMENTATION
SUPPORTED_REQUEST_BASS_STYLES = _domain.SUPPORTED_REQUEST_BASS_STYLES
AUTO_BASS_STYLE_BY_PRESET = _domain.AUTO_BASS_STYLE_BY_PRESET
TOP_LEVEL_FIELDS = _domain.TOP_LEVEL_FIELDS
FORM_FIELDS = _domain.FORM_FIELDS
TRACK_TEMPLATES = _domain.TRACK_TEMPLATES
_require = _domain._require
_int_field = _domain._int_field
_non_empty_string = _domain._non_empty_string
_unknown_fields = _domain._unknown_fields
_validate_meter = _domain._validate_meter
_validate_tonal_center = _domain._validate_tonal_center
_validate_progression = _domain._validate_progression
_validate_instrumentation = _domain._validate_instrumentation
_validate_arrangement = _domain._validate_arrangement
_resolve_bass_style = _domain._resolve_bass_style

GROOVE_CATALOG = ROOT / "catalogs" / "grooves" / "catalog.json"
PROGRESSION_CATALOG = ROOT / "catalogs" / "progressions" / "catalog.json"


def _catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_form_chords(
    form: dict[str, Any],
    *,
    bars: int,
    key_signature: str,
    tonal_center: str | None,
    meter: list[int],
) -> tuple[list[str], str | None]:
    return _domain._resolve_form_chords(
        form,
        bars=bars,
        key_signature=key_signature,
        tonal_center=tonal_center,
        meter=meter,
        progression_catalog=_catalog(PROGRESSION_CATALOG),
    )


def validate_request(request: dict[str, Any]) -> None:
    _domain.validate_request(
        request,
        _catalog(GROOVE_CATALOG),
        _catalog(PROGRESSION_CATALOG),
    )


def resolve_request(request: dict[str, Any]) -> dict[str, Any]:
    return _domain.resolve_request(
        request,
        _catalog(GROOVE_CATALOG),
        _catalog(PROGRESSION_CATALOG),
    )


def resolve_file(path: Path) -> dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    return resolve_request(request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        spec = resolve_file(args.request)
        payload = json.dumps(spec, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(payload, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
    except (OSError, json.JSONDecodeError, _midi_workflow.ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
