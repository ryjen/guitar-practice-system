#!/usr/bin/env python3
"""Compatibility module for deterministic groove rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script imports predate the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import groove as _domain  # noqa: E402

GENERAL_MIDI_DRUMS = _domain.GENERAL_MIDI_DRUMS
SUPPORTED_SUBDIVISIONS = _domain.SUPPORTED_SUBDIVISIONS
COUNT_IN_MODES = _domain.COUNT_IN_MODES
GrooveInstrument = _domain.GrooveInstrument
GrooveSpec = _domain.GrooveSpec
GrooveHit = _domain.GrooveHit
steps_per_bar = _domain.steps_per_bar
_int_field = _domain._int_field
_step_list = _domain._step_list
_parse_bar_cycle = _domain._parse_bar_cycle
parse_groove = _domain.parse_groove
validate_manifest = _domain.validate_manifest
_stable_rng = _domain._stable_rng
_bar_is_muted = _domain._bar_is_muted
render_bar = _domain.render_bar
_count_in_hits = _domain._count_in_hits
generate_drum_track = _domain.generate_drum_track


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = _domain.render(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
