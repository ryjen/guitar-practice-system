#!/usr/bin/env python3
"""Resolve backing-track specs into deterministic Type 1 MIDI.

This layer composes the existing MIDI renderer, GrooveSpec renderer, and named
groove catalog. It owns backing-track-level concerns such as preset references
and arrangement-wide gap cycles; the lower-level groove engine remains focused
on drum timing and feel.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import groove_catalog
import groove_engine
import midi_workflow


@dataclass(frozen=True)
class ArrangementCycle:
    length: int
    mute_bars: tuple[int, ...]


def _int_field(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi_workflow.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi_workflow.ManifestError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def _bar_list(value: Any, *, name: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        isinstance(bar, bool) or not isinstance(bar, int) for bar in value
    ):
        raise midi_workflow.ManifestError(f"{name} must be a list of integers")
    if len(set(value)) != len(value):
        raise midi_workflow.ManifestError(f"{name} cannot contain duplicate bars")
    if any(bar < 0 or bar >= maximum for bar in value):
        raise midi_workflow.ManifestError(
            f"{name} bars must be between 0 and {maximum - 1}"
        )
    return tuple(sorted(value))


def parse_arrangement_cycle(manifest: dict[str, Any]) -> ArrangementCycle | None:
    arrangement = manifest.get("arrangement")
    if arrangement is None:
        return None
    if not isinstance(arrangement, dict):
        raise midi_workflow.ManifestError("arrangement must be an object")
    unknown = set(arrangement) - {"bar_cycle"}
    if unknown:
        raise midi_workflow.ManifestError(
            f"arrangement has unsupported fields: {sorted(unknown)}"
        )

    raw = arrangement.get("bar_cycle")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise midi_workflow.ManifestError("arrangement.bar_cycle must be an object")
    unknown = set(raw) - {"length", "mute_bars"}
    if unknown:
        raise midi_workflow.ManifestError(
            f"arrangement.bar_cycle has unsupported fields: {sorted(unknown)}"
        )

    length = _int_field(
        raw.get("length"),
        name="arrangement.bar_cycle.length",
        minimum=1,
        maximum=64,
    )
    mute_bars = _bar_list(
        raw.get("mute_bars", []),
        name="arrangement.bar_cycle.mute_bars",
        maximum=length,
    )
    return ArrangementCycle(length=length, mute_bars=mute_bars)


def arrangement_muted_bars(manifest: dict[str, Any]) -> set[int]:
    """Return absolute bar indexes muted for every accompaniment track.

    Count-in bars are intentionally outside the cycle. Bar zero of the cycle is
    the first musical bar after count-in.
    """
    cycle = parse_arrangement_cycle(manifest)
    if cycle is None or not cycle.mute_bars:
        return set()

    count_in = manifest["count_in_bars"]
    musical_bars = sum(section["bars"] for section in manifest["sections"])
    return {
        count_in + bar
        for bar in range(musical_bars)
        if bar % cycle.length in cycle.mute_bars
    }


def resolve_track(track: dict[str, Any], meter: list[int]) -> dict[str, Any]:
    """Return an isolated track with any groove preset expanded to GrooveSpec."""
    has_inline = "groove" in track
    has_preset = "groove_preset" in track
    if has_inline and has_preset:
        raise midi_workflow.ManifestError(
            "drum track cannot define both groove and groove_preset"
        )
    if (has_inline or has_preset) and track["role"] != "drums":
        raise midi_workflow.ManifestError(
            "groove and groove_preset are only supported on drum tracks"
        )

    resolved = json.loads(json.dumps(track))
    if has_preset:
        preset_id = track["groove_preset"]
        if not isinstance(preset_id, str) or not preset_id:
            raise midi_workflow.ManifestError("groove_preset must be a non-empty string")
        preset = groove_catalog.get_preset(preset_id)
        if preset["meter"] != meter:
            raise midi_workflow.ManifestError(
                f"groove preset {preset_id!r} uses meter "
                f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
            )
        resolved["groove"] = groove_catalog.resolved_groove(preset_id)
        resolved.pop("groove_preset", None)

    if "groove" in resolved:
        groove_engine.parse_groove(
            resolved["groove"],
            meter=meter,
            default_velocity=int(resolved.get("velocity", 78)),
        )
    return resolved


def validate_manifest(manifest: dict[str, Any]) -> None:
    midi_workflow.validate_manifest(manifest)
    parse_arrangement_cycle(manifest)
    for track in manifest["tracks"]:
        resolve_track(track, manifest["meter"])


def _generate_groove_drum_track(
    track: dict[str, Any],
    *,
    total_bars: int,
    count_in_bars: int,
    meter: list[int],
    bar_ticks: int,
    beat_ticks: int,
    tempo_bpm: int,
    muted_bars: set[int],
) -> bytes:
    spec = groove_engine.parse_groove(
        track["groove"],
        meter=meter,
        default_velocity=int(track.get("velocity", 78)),
    )
    events: list[midi_workflow.TimedEvent] = [
        midi_workflow.TimedEvent(
            0,
            0,
            midi_workflow.meta(0x03, track["name"].encode()),
        )
    ]
    bar_steps = groove_engine.steps_per_bar(meter, spec.subdivision)
    note_duration = max(24, min(90, bar_ticks // bar_steps // 2))

    for absolute_bar in range(total_bars):
        if absolute_bar in muted_bars:
            hits: list[groove_engine.GrooveHit] = []
        elif absolute_bar < count_in_bars and spec.count_in != "groove":
            hits = groove_engine._count_in_hits(
                spec,
                meter=meter,
                beat_ticks=beat_ticks,
            )
        else:
            musical_bar = max(0, absolute_bar - count_in_bars)
            hits = groove_engine.render_bar(
                spec,
                bar_index=musical_bar,
                meter=meter,
                bar_ticks=bar_ticks,
                tempo_bpm=tempo_bpm,
            )

        start = absolute_bar * bar_ticks
        for hit in hits:
            events.extend(
                midi_workflow.note_events(
                    channel=midi_workflow.DRUM_CHANNEL,
                    note=hit.note,
                    velocity=hit.velocity,
                    start=start + hit.tick,
                    duration=note_duration,
                )
            )
    return midi_workflow.track_bytes(events)


def _generate_legacy_drum_track(
    track: dict[str, Any],
    *,
    total_bars: int,
    bar_ticks: int,
    beat_ticks: int,
    muted_bars: set[int],
) -> bytes:
    events: list[midi_workflow.TimedEvent] = [
        midi_workflow.TimedEvent(
            0,
            0,
            midi_workflow.meta(0x03, track["name"].encode()),
        )
    ]
    for bar_index in range(total_bars):
        if bar_index in muted_bars:
            continue
        start = bar_index * bar_ticks
        for beat in range(bar_ticks // beat_ticks):
            tick = start + beat * beat_ticks
            events.extend(
                midi_workflow.note_events(
                    channel=midi_workflow.DRUM_CHANNEL,
                    note=42,
                    velocity=56,
                    start=tick,
                    duration=60,
                )
            )
            if beat in {0, 2}:
                events.extend(
                    midi_workflow.note_events(
                        channel=midi_workflow.DRUM_CHANNEL,
                        note=36,
                        velocity=88,
                        start=tick,
                        duration=90,
                    )
                )
            if beat in {1, 3}:
                events.extend(
                    midi_workflow.note_events(
                        channel=midi_workflow.DRUM_CHANNEL,
                        note=38,
                        velocity=82,
                        start=tick,
                        duration=90,
                    )
                )
    return midi_workflow.track_bytes(events)


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)

    numerator, denominator = manifest["meter"]
    beat_ticks = midi_workflow.TPQN * 4 // denominator
    bar_ticks = numerator * beat_ticks
    chords = midi_workflow.arrangement_chords(manifest)
    muted_bars = arrangement_muted_bars(manifest)
    masked_chords = [
        "N.C." if index in muted_bars else chord
        for index, chord in enumerate(chords)
    ]

    tracks = [midi_workflow.conductor_track(manifest, bar_ticks)]
    for source_track in manifest["tracks"]:
        track = resolve_track(source_track, manifest["meter"])
        if track["role"] == "drums" and "groove" in track:
            tracks.append(
                _generate_groove_drum_track(
                    track,
                    total_bars=len(chords),
                    count_in_bars=manifest["count_in_bars"],
                    meter=manifest["meter"],
                    bar_ticks=bar_ticks,
                    beat_ticks=beat_ticks,
                    tempo_bpm=manifest["tempo_bpm"],
                    muted_bars=muted_bars,
                )
            )
        elif track["role"] == "drums" and muted_bars:
            tracks.append(
                _generate_legacy_drum_track(
                    track,
                    total_bars=len(chords),
                    bar_ticks=bar_ticks,
                    beat_ticks=beat_ticks,
                    muted_bars=muted_bars,
                )
            )
        else:
            tracks.append(
                midi_workflow.generate_track(
                    track,
                    masked_chords,
                    bar_ticks,
                    beat_ticks,
                )
            )

    header = midi_workflow.midi_chunk(
        b"MThd",
        struct.pack(">HHH", 1, len(tracks), midi_workflow.TPQN),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + b"".join(tracks))
