#!/usr/bin/env python3
"""Compatibility module for deterministic bass accompaniment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script imports predate the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import bass as _domain  # noqa: E402
from guitar_practice.domain import groove as _groove  # noqa: E402

SUPPORTED_STYLES = _domain.SUPPORTED_STYLES
KICK_NOTE = _domain.KICK_NOTE
BassSpec = _domain.BassSpec
BassHit = _domain.BassHit
_int_field = _domain._int_field
parse_bass = _domain.parse_bass
requires_groove = _domain.requires_groove
_bass_notes = _domain._bass_notes
_note_for_style = _domain._note_for_style
_velocity = _domain._velocity
_duration = _domain._duration


def _kick_reference_hits(
    groove: _groove.GrooveSpec,
    *,
    bar_index: int,
    meter: list[int] | tuple[int, int],
    bar_ticks: int,
    tempo_bpm: int,
) -> list[_groove.GrooveHit]:
    return _domain._kick_reference_hits(
        groove,
        bar_index=bar_index,
        meter=meter,
        bar_ticks=bar_ticks,
        tempo_bpm=tempo_bpm,
    )


def render_bar(
    spec: BassSpec,
    *,
    chord: str,
    bar_index: int,
    meter: list[int] | tuple[int, int],
    bar_ticks: int,
    beat_ticks: int,
    tempo_bpm: int,
    base_velocity: int,
    groove: _groove.GrooveSpec | None = None,
) -> list[BassHit]:
    return _domain.render_bar(
        spec,
        chord=chord,
        bar_index=bar_index,
        meter=meter,
        bar_ticks=bar_ticks,
        beat_ticks=beat_ticks,
        tempo_bpm=tempo_bpm,
        base_velocity=base_velocity,
        groove_spec=groove,
    )


def generate_track(
    track: dict[str, Any],
    *,
    chords: list[str],
    count_in_bars: int,
    meter: list[int],
    bar_ticks: int,
    beat_ticks: int,
    tempo_bpm: int,
    groove: _groove.GrooveSpec | None,
) -> bytes:
    return _domain.generate_track(
        track,
        chords=chords,
        count_in_bars=count_in_bars,
        meter=meter,
        bar_ticks=bar_ticks,
        beat_ticks=beat_ticks,
        tempo_bpm=tempo_bpm,
        groove_spec=groove,
    )
