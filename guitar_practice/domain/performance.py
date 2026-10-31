"""Bounded, section-local authored drum fills and bass phrases.

Overrides are source data, not opaque performance inference. They use the active
groove's subdivision and swing, and are indexed by 1-based bars within a section.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.domain import bass, groove, midi

MAX_EVENTS_PER_BAR = 16
MIN_OFFSET = -12
MAX_OFFSET = 12
MIN_VELOCITY = 1
MAX_VELOCITY = 127
DEFAULT_GATE_PERCENT = 72


@dataclass(frozen=True)
class DrumFill:
    replace_notes: frozenset[int]
    hits: tuple[groove.GrooveHit, ...]


@dataclass(frozen=True)
class RiffNote:
    step: int
    offset: int
    velocity: int | None


@dataclass(frozen=True)
class Performance:
    drum_fills: dict[int, DrumFill]
    bass_riffs: dict[int, tuple[RiffNote, ...]]


def _object(value: Any, name: str, allowed: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise midi.ManifestError(f"{name} must be an object")
    unknown = set(value) - allowed
    if unknown:
        raise midi.ManifestError(f"{name} has unsupported fields: {sorted(unknown)}")
    return value


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise midi.ManifestError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _items(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_EVENTS_PER_BAR:
        raise midi.ManifestError(f"{name} requires 1..{MAX_EVENTS_PER_BAR} entries")
    return value


def _instrument(value: Any, name: str) -> int:
    if not isinstance(value, str) or value not in groove.GENERAL_MIDI_DRUMS:
        raise midi.ManifestError(f"{name} must be a supported groove instrument")
    return groove.GENERAL_MIDI_DRUMS[value]


def _tick(step: int, *, steps: int, bar_ticks: int, swing: float) -> int:
    step_ticks = bar_ticks // steps
    return step * step_ticks + (round(step_ticks * swing) if step % 2 else 0)


def parse(
    manifest: dict[str, Any],
    *,
    groove_spec: groove.GrooveSpec | None,
    has_bass: bool,
) -> Performance:
    """Validate all section-local overrides and return zero-based musical-bar maps."""
    fills: dict[int, DrumFill] = {}
    riffs: dict[int, tuple[RiffNote, ...]] = {}
    offset = 0
    meter = manifest["meter"]
    beat_ticks = midi.TPQN * 4 // meter[1]
    bar_ticks = meter[0] * beat_ticks
    steps = groove.steps_per_bar(meter, groove_spec.subdivision) if groove_spec else 0
    if steps and bar_ticks % steps:
        raise midi.ManifestError("groove subdivision cannot align with MIDI resolution")

    for section in manifest["sections"]:
        for kind, target in (("drum_fills", fills), ("bass_riffs", riffs)):
            entries = section.get(kind, [])
            if not isinstance(entries, list) or len(entries) > section["bars"]:
                raise midi.ManifestError(f"section.{kind} must be a bounded list")
            if entries and groove_spec is None:
                raise midi.ManifestError(f"section.{kind} requires exactly one groove-aware drum track")
            if kind == "bass_riffs" and entries and not has_bass:
                raise midi.ManifestError("section.bass_riffs requires a generated bass track")

            for entry in entries:
                allowed = (
                    frozenset({"bar", "replace", "hits"})
                    if kind == "drum_fills"
                    else frozenset({"bar", "notes"})
                )
                obj = _object(entry, f"section.{kind} entry", allowed)
                bar = _integer(obj.get("bar"), f"section.{kind}.bar", 1, section["bars"])
                absolute = offset + bar - 1
                if absolute in target:
                    raise midi.ManifestError(f"duplicate {kind} for musical bar {absolute + 1}")

                if kind == "drum_fills":
                    replacements = obj.get("replace", [])
                    if not isinstance(replacements, list) or len(replacements) > len(groove.GENERAL_MIDI_DRUMS):
                        raise midi.ManifestError("drum_fills.replace must be a bounded list")
                    replace_notes = [_instrument(name, "drum_fills.replace") for name in replacements]
                    if len(replace_notes) != len(set(replace_notes)):
                        raise midi.ManifestError("drum_fills.replace contains duplicates")
                    hits = []
                    seen = set()
                    for item in _items(obj.get("hits"), "drum_fills.hits"):
                        h = _object(
                            item,
                            "drum fill hit",
                            frozenset({"instrument", "step", "triplet_step", "velocity"}),
                        )
                        note = _instrument(h.get("instrument"), "drum_fills.hits.instrument")
                        if ("step" in h) == ("triplet_step" in h):
                            raise midi.ManifestError(
                                "drum_fills.hits requires exactly one of step or triplet_step"
                            )
                        if "triplet_step" in h:
                            triplet_step = _integer(
                                h["triplet_step"], "drum_fills.hits.triplet_step",
                                0, meter[0] * 3 - 1,
                            )
                            if beat_ticks % 3:
                                raise midi.ManifestError(
                                    "triplet timing cannot align with MIDI resolution"
                                )
                            tick = triplet_step * (beat_ticks // 3)
                        else:
                            step = _integer(h["step"], "drum_fills.hits.step", 0, steps - 1)
                            tick = _tick(
                                step, steps=steps, bar_ticks=bar_ticks,
                                swing=groove_spec.swing,
                            )
                        velocity = _integer(
                            h.get("velocity"), "drum_fills.hits.velocity",
                            MIN_VELOCITY, MAX_VELOCITY,
                        )
                        if (note, tick) in seen:
                            raise midi.ManifestError(
                                "duplicate drum hit at one instrument/tick"
                            )
                        seen.add((note, tick))
                        hits.append(
                            groove.GrooveHit(
                                tick, note, velocity,
                                max_duration_ticks=(beat_ticks // 3 if "triplet_step" in h else None),
                            )
                        )
                    fills[absolute] = DrumFill(frozenset(replace_notes), tuple(hits))
                else:
                    notes = []
                    seen = set()
                    for item in _items(obj.get("notes"), "bass_riffs.notes"):
                        n = _object(item, "bass riff note", frozenset({"step", "offset", "velocity"}))
                        step = _integer(n.get("step"), "bass_riffs.notes.step", 0, steps - 1)
                        semitones = _integer(n.get("offset"), "bass_riffs.notes.offset", MIN_OFFSET, MAX_OFFSET)
                        velocity = n.get("velocity")
                        if velocity is not None:
                            velocity = _integer(velocity, "bass_riffs.notes.velocity", MIN_VELOCITY, MAX_VELOCITY)
                        if step in seen:
                            raise midi.ManifestError("duplicate bass note at one step")
                        seen.add(step)
                        notes.append(RiffNote(step, semitones, velocity))
                    riffs[absolute] = tuple(sorted(notes, key=lambda n: n.step))
        offset += section["bars"]
    return Performance(fills, riffs)


def apply_drum_fill(hits: list[groove.GrooveHit], fill: DrumFill) -> list[groove.GrooveHit]:
    """Replace selected kit voices, keeping any untouched groove instruments."""
    result = [hit for hit in hits if hit.note not in fill.replace_notes]
    return sorted([*result, *fill.hits], key=lambda hit: (hit.tick, hit.note))


def render_bass_riff(
    notes: tuple[RiffNote, ...],
    *,
    chord: str,
    groove_spec: groove.GrooveSpec,
    meter: list[int],
    bar_ticks: int,
    base_velocity: int,
    gate_percent: int = DEFAULT_GATE_PERCENT,
) -> list[bass.BassHit]:
    if chord == "N.C.":
        return []
    root = midi.chord_notes(chord)[0] - 12
    steps = groove.steps_per_bar(meter, groove_spec.subdivision)
    positioned = [(_tick(n.step, steps=steps, bar_ticks=bar_ticks, swing=groove_spec.swing), n) for n in notes]
    result = []
    for i, (tick, note) in enumerate(positioned):
        end = positioned[i + 1][0] if i + 1 < len(positioned) else bar_ticks
        length = max(1, round((end - tick) * gate_percent / 100))
        midi_note = root + note.offset
        if not 0 <= midi_note <= 127:
            raise midi.ManifestError(f"bass riff note outside MIDI range: {midi_note}")
        result.append(bass.BassHit(tick, midi_note, note.velocity or base_velocity, min(length, bar_ticks - tick)))
    return result
