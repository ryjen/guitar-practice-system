#!/usr/bin/env python3
"""Compatibility module for deterministic backing-track rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script imports predate the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import backing as _domain  # noqa: E402

DEFAULT_GROOVE_CATALOG = ROOT / "catalogs" / "grooves" / "catalog.json"
ArrangementCycle = _domain.ArrangementCycle
_int_field = _domain._int_field
_bar_list = _domain._bar_list
parse_arrangement_cycle = _domain.parse_arrangement_cycle
arrangement_muted_bars = _domain.arrangement_muted_bars
_groove_specs = _domain._groove_specs
_reference_groove = _domain._reference_groove
_count_in_hits = _domain._count_in_hits
_generate_groove_drum_track = _domain._generate_groove_drum_track
_generate_legacy_drum_track = _domain._generate_legacy_drum_track


def _catalog(path: Path = DEFAULT_GROOVE_CATALOG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_track(track: dict[str, Any], meter: list[int]) -> dict[str, Any]:
    return _domain.resolve_track(track, meter, _catalog())


def validate_manifest(manifest: dict[str, Any]) -> None:
    _domain.validate_manifest(manifest, _catalog())


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = _domain.render(manifest, _catalog())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
