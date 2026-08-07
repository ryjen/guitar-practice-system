#!/usr/bin/env python3
"""Validate concrete metronome and tempo realizations.

The validator intentionally checks semantics that plain BPM values cannot express:
beat units, subdivisions, click pulse, compound/odd-meter grouping, and bounded
progression behavior. It does not score performances or mutate progress.
"""

from __future__ import annotations

from typing import Any

BEAT_UNITS = {
    "whole",
    "half",
    "quarter",
    "dotted-quarter",
    "eighth",
    "dotted-eighth",
    "sixteenth",
}
CLICK_MODES = {
    "every-beat",
    "accented-downbeat",
    "backbeat",
    "half-time",
    "one-per-bar",
    "off-beat",
    "gap",
    "count-in-silence",
    "additive-accents",
}
STRATEGIES = {"ladder", "pyramid", "burst", "subdivision", "loop-expansion", "sparse-click"}
SOURCES = {"session", "song-section", "backing-track", "exercise", "technique", "rhythm-definition", "fallback"}


class TimingError(ValueError):
    pass


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TimingError(f"{field} must be a positive number")
    return float(value)


def _meter(value: Any) -> tuple[int, int]:
    if not isinstance(value, str) or "/" not in value:
        raise TimingError("meter must use numerator/denominator form")
    numerator_text, denominator_text = value.split("/", 1)
    try:
        numerator = int(numerator_text)
        denominator = int(denominator_text)
    except ValueError as error:
        raise TimingError("meter must use integer numerator/denominator form") from error
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
        raise TimingError("meter has unsupported values")
    return numerator, denominator


def validate_timing(realization: dict[str, Any]) -> None:
    if not isinstance(realization, dict):
        raise TimingError("timing realization must be an object")

    numerator, denominator = _meter(realization.get("meter"))
    grouping = realization.get("grouping")
    if grouping is not None:
        if not isinstance(grouping, list) or not grouping or any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in grouping
        ):
            raise TimingError("grouping must be a non-empty list of positive integers")
        if sum(grouping) != numerator:
            raise TimingError("grouping must sum to the meter numerator")
    if denominator == 8 and numerator not in {3, 6, 9, 12} and grouping is None:
        raise TimingError("odd/additive eighth-note meters require grouping")

    for stage in ("start", "working", "target", "stretch"):
        value = realization.get(stage)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise TimingError(f"{stage} must be an object")
        _positive_number(value.get("bpm"), f"{stage}.bpm")
        if value.get("beat_unit") not in BEAT_UNITS:
            raise TimingError(f"{stage}.beat_unit must be explicit and supported")
    if "start" not in realization or "target" not in realization:
        raise TimingError("start and target realizations are required")

    subdivision = realization.get("subdivision")
    if not isinstance(subdivision, dict):
        raise TimingError("subdivision is required")
    if not isinstance(subdivision.get("value"), str) or not subdivision["value"]:
        raise TimingError("subdivision.value is required")
    _positive_number(subdivision.get("notes_per_beat"), "subdivision.notes_per_beat")

    click = realization.get("click")
    if not isinstance(click, dict):
        raise TimingError("click configuration is required")
    if click.get("mode") not in CLICK_MODES:
        raise TimingError("unsupported click mode")
    if click.get("pulse_unit") not in BEAT_UNITS:
        raise TimingError("click.pulse_unit must be explicit and supported")

    strategy = realization.get("strategy")
    if strategy not in STRATEGIES:
        raise TimingError("unsupported progression strategy")

    source = realization.get("source", "session")
    if source not in SOURCES:
        raise TimingError("unsupported timing source")

    for field in ("increment_bpm", "decrement_bpm", "clean_repetitions", "max_failed_attempts"):
        if field in realization:
            _positive_number(realization[field], field)

    if not isinstance(realization.get("stop_condition"), str) or not realization["stop_condition"].strip():
        raise TimingError("stop_condition is required")
    if not isinstance(realization.get("final_check"), str) or not realization["final_check"].strip():
        raise TimingError("final_check is required")


def effective_event_rate(bpm: float, notes_per_beat: float) -> float:
    """Return events per minute for comparable patterns only."""
    return _positive_number(bpm, "bpm") * _positive_number(notes_per_beat, "notes_per_beat")
