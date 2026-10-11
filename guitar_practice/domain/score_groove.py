"""Read-only Score IR rhythm guides derived from Groove Engine presets."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from guitar_practice.domain import groove, midi, score


class ScoreGrooveError(ValueError):
    """A groove preset cannot be used safely as a Score IR rhythm guide."""


def _active_meter(document: Mapping[str, Any], bar: int) -> tuple[int, int]:
    if isinstance(bar, bool) or not isinstance(bar, int) or bar < 1:
        raise ScoreGrooveError("bar must be a positive integer")
    if bar > len(document["bars"]):
        raise ScoreGrooveError(
            f"bar {bar} exceeds score bar count ({len(document['bars'])})"
        )

    active = document["meter_map"][0]
    for candidate in document["meter_map"][1:]:
        if candidate["bar"] > bar:
            break
        active = candidate
    return int(active["beats"]), int(active["beat_unit"])


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def rhythm_guide(
    document: Mapping[str, Any],
    preset: Mapping[str, Any],
    *,
    bar: int,
) -> dict[str, Any]:
    """Resolve one validated groove preset as transient Score IR rhythm guidance."""

    canonical = copy.deepcopy(dict(document))
    try:
        score.validate(canonical)
    except score.ScoreError as exc:
        raise ScoreGrooveError(str(exc)) from exc

    meter = _active_meter(canonical, bar)
    preset_meter = preset.get("meter")
    if preset_meter != [meter[0], meter[1]]:
        raise ScoreGrooveError(
            f"groove meter {preset_meter!r} does not match score meter "
            f"{meter[0]}/{meter[1]} at bar {bar}"
        )

    try:
        spec = groove.parse_groove(preset.get("groove"), meter=meter)
        step_count = groove.steps_per_bar(meter, spec.subdivision)
    except midi.ManifestError as exc:
        raise ScoreGrooveError(str(exc)) from exc

    locations = []
    for step in range(step_count):
        beat = Fraction(1, 1) + Fraction(step * meter[1], spec.subdivision)
        locations.append(
            {
                "step": step,
                "beat": _pair(beat),
                "swung": bool(spec.swing and step % 2 == 1),
            }
        )

    instruments: list[dict[str, Any]] = []
    for instrument in spec.instruments:
        variation = None
        if instrument.variation_every_bars is not None:
            variation = {
                "every_bars": instrument.variation_every_bars,
                "steps": list(instrument.variation_steps),
            }
        instruments.append(
            {
                "name": instrument.name,
                "note": instrument.note,
                "steps": list(instrument.steps),
                "velocity": instrument.velocity,
                "accent_steps": list(instrument.accent_steps),
                "accent_velocity": instrument.accent_velocity,
                "variation": variation,
            }
        )

    bar_cycle = None
    if spec.bar_cycle_length is not None:
        bar_cycle = {
            "length": spec.bar_cycle_length,
            "mute_bars": list(spec.bar_cycle_mute_bars),
        }

    return {
        "score_id": canonical["id"],
        "bar": bar,
        "meter": [meter[0], meter[1]],
        "preset": {
            "id": preset["id"],
            "title": preset["title"],
            "tags": list(preset["tags"]),
            "practice_intents": list(preset["practice_intents"]),
        },
        "grid": {
            "subdivision": spec.subdivision,
            "steps_per_bar": step_count,
            "locations": locations,
        },
        "feel": {
            "swing": spec.swing,
            "humanize_ms": spec.humanize_ms,
            "velocity_variance": spec.velocity_variance,
            "seed": spec.seed,
            "count_in": spec.count_in,
        },
        "bar_cycle": bar_cycle,
        "instruments": instruments,
    }
