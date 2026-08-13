#!/usr/bin/env python3
"""Deterministic bass accompaniment patterns for backing-track MIDI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import groove_engine
import midi_workflow


SUPPORTED_STYLES = {
    "kick-root",
    "kick-root-fifth",
    "kick-root-octave",
    "walking",
}
KICK_NOTE = groove_engine.GENERAL_MIDI_DRUMS["kick"]


@dataclass(frozen=True)
class BassSpec:
    style: str
    gate_percent: int
    follow_kick_velocity: bool


@dataclass(frozen=True)
class BassHit:
    tick: int
    note: int
    velocity: int
    duration: int


def _int_field(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi_workflow.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi_workflow.ManifestError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def parse_bass(raw: Any) -> BassSpec:
    if not isinstance(raw, dict):
        raise midi_workflow.ManifestError("bass must be an object")
    unknown = set(raw) - {"style", "gate_percent", "follow_kick_velocity"}
    if unknown:
        raise midi_workflow.ManifestError(
            f"bass has unsupported fields: {sorted(unknown)}"
        )

    style = raw.get("style")
    if not isinstance(style, str) or style not in SUPPORTED_STYLES:
        raise midi_workflow.ManifestError(
            f"bass.style must be one of {sorted(SUPPORTED_STYLES)}"
        )
    gate_percent = _int_field(
        raw.get("gate_percent", 72),
        name="bass.gate_percent",
        minimum=20,
        maximum=95,
    )
    follow = raw.get("follow_kick_velocity", style.startswith("kick-"))
    if not isinstance(follow, bool):
        raise midi_workflow.ManifestError(
            "bass.follow_kick_velocity must be boolean"
        )
    if style == "walking" and follow:
        raise midi_workflow.ManifestError(
            "walking bass cannot follow kick velocity"
        )
    return BassSpec(
        style=style,
        gate_percent=gate_percent,
        follow_kick_velocity=follow,
    )


def requires_groove(spec: BassSpec) -> bool:
    return spec.style.startswith("kick-")


def _bass_notes(chord: str) -> tuple[int, int, int, tuple[int, ...]]:
    notes = midi_workflow.chord_notes(chord)
    root = notes[0] - 12
    fifth = root + 7
    octave = root + 12
    lowered = tuple(note - 12 for note in notes)
    return root, fifth, octave, lowered


def _kick_reference_hits(
    groove: groove_engine.GrooveSpec,
    *,
    bar_index: int,
    meter: list[int] | tuple[int, int],
    bar_ticks: int,
    tempo_bpm: int,
) -> list[groove_engine.GrooveHit]:
    """Render the underlying kick pattern without applying drum-only gap cycles."""
    reference = replace(
        groove,
        bar_cycle_length=None,
        bar_cycle_mute_bars=(),
    )
    return [
        hit
        for hit in groove_engine.render_bar(
            reference,
            bar_index=bar_index,
            meter=meter,
            bar_ticks=bar_ticks,
            tempo_bpm=tempo_bpm,
        )
        if hit.note == KICK_NOTE
    ]


def _note_for_style(
    style: str,
    index: int,
    *,
    root: int,
    fifth: int,
    octave: int,
) -> int:
    if style == "kick-root":
        return root
    if style == "kick-root-fifth":
        return root if index % 2 == 0 else fifth
    if style == "kick-root-octave":
        return root if index % 2 == 0 else octave
    raise midi_workflow.ManifestError(f"unsupported kick-locked bass style: {style}")


def _velocity(base: int, kick_velocity: int, follow: bool) -> int:
    if not follow:
        return base
    adjusted = base + round((kick_velocity - 88) * 0.25)
    return max(1, min(127, adjusted))


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
    groove: groove_engine.GrooveSpec | None = None,
) -> list[BassHit]:
    if bar_index < 0:
        raise midi_workflow.ManifestError("bar_index cannot be negative")
    if chord == "N.C.":
        return []

    root, fifth, octave, chord_tones = _bass_notes(chord)
    hits: list[BassHit] = []

    if spec.style == "walking":
        beats = bar_ticks // beat_ticks
        pattern = chord_tones if len(chord_tones) >= 3 else (root, fifth, octave)
        if len(pattern) == 3:
            pattern = pattern + (octave,)
        for beat in range(beats):
            tick = beat * beat_ticks
            note = pattern[beat % len(pattern)]
            duration = max(24, round(beat_ticks * spec.gate_percent / 100))
            duration = min(duration, max(24, bar_ticks - tick - 1))
            hits.append(
                BassHit(
                    tick=tick,
                    note=note,
                    velocity=base_velocity,
                    duration=duration,
                )
            )
        return hits

    if groove is None:
        raise midi_workflow.ManifestError(
            f"bass style {spec.style!r} requires one groove-aware drum track"
        )
    kick_hits = _kick_reference_hits(
        groove,
        bar_index=bar_index,
        meter=meter,
        bar_ticks=bar_ticks,
        tempo_bpm=tempo_bpm,
    )

    for index, kick in enumerate(kick_hits):
        next_tick = (
            kick_hits[index + 1].tick
            if index + 1 < len(kick_hits)
            else min(bar_ticks, kick.tick + beat_ticks)
        )
        available = max(25, next_tick - kick.tick)
        duration = max(24, round(available * spec.gate_percent / 100))
        duration = min(duration, max(24, bar_ticks - kick.tick - 1))
        hits.append(
            BassHit(
                tick=kick.tick,
                note=_note_for_style(
                    spec.style,
                    index,
                    root=root,
                    fifth=fifth,
                    octave=octave,
                ),
                velocity=_velocity(
                    base_velocity,
                    kick.velocity,
                    spec.follow_kick_velocity,
                ),
                duration=duration,
            )
        )
    return hits


def generate_track(
    track: dict[str, Any],
    *,
    chords: list[str],
    count_in_bars: int,
    meter: list[int],
    bar_ticks: int,
    beat_ticks: int,
    tempo_bpm: int,
    groove: groove_engine.GrooveSpec | None,
) -> bytes:
    if track.get("role") != "bass":
        raise midi_workflow.ManifestError("bass spec is only supported on bass tracks")
    spec = parse_bass(track.get("bass"))
    if requires_groove(spec) and groove is None:
        raise midi_workflow.ManifestError(
            f"bass style {spec.style!r} requires one groove-aware drum track"
        )

    channel = int(track["channel"])
    velocity = int(track.get("velocity", 78))
    events: list[midi_workflow.TimedEvent] = [
        midi_workflow.TimedEvent(
            0,
            0,
            midi_workflow.meta(0x03, track["name"].encode()),
        ),
        midi_workflow.TimedEvent(
            0,
            5,
            bytes([0xC0 | channel, int(track.get("program", 34))]),
        ),
    ]

    for absolute_bar, chord in enumerate(chords):
        if chord == "N.C.":
            continue
        musical_bar = max(0, absolute_bar - count_in_bars)
        start = absolute_bar * bar_ticks
        for hit in render_bar(
            spec,
            chord=chord,
            bar_index=musical_bar,
            meter=meter,
            bar_ticks=bar_ticks,
            beat_ticks=beat_ticks,
            tempo_bpm=tempo_bpm,
            base_velocity=velocity,
            groove=groove,
        ):
            events.extend(
                midi_workflow.note_events(
                    channel=channel,
                    note=hit.note,
                    velocity=hit.velocity,
                    start=start + hit.tick,
                    duration=hit.duration,
                )
            )
    return midi_workflow.track_bytes(events)
