"""Deterministic backing-track arrangement and rendering rules."""

from __future__ import annotations

import copy
import struct
from dataclasses import dataclass
from typing import Any

from guitar_practice.domain import bass, groove, midi


@dataclass(frozen=True)
class ArrangementCycle:
    length: int
    mute_bars: tuple[int, ...]


def _int_field(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi.ManifestError(f"{name} must be between {minimum} and {maximum}")
    return value


def _bar_list(value: Any, *, name: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        isinstance(bar, bool) or not isinstance(bar, int) for bar in value
    ):
        raise midi.ManifestError(f"{name} must be a list of integers")
    if len(set(value)) != len(value):
        raise midi.ManifestError(f"{name} cannot contain duplicate bars")
    if any(bar < 0 or bar >= maximum for bar in value):
        raise midi.ManifestError(f"{name} bars must be between 0 and {maximum - 1}")
    return tuple(sorted(value))


def parse_arrangement_cycle(manifest: dict[str, Any]) -> ArrangementCycle | None:
    arrangement = manifest.get("arrangement")
    if arrangement is None:
        return None
    if not isinstance(arrangement, dict):
        raise midi.ManifestError("arrangement must be an object")
    unknown = set(arrangement) - {"bar_cycle"}
    if unknown:
        raise midi.ManifestError(
            f"arrangement has unsupported fields: {sorted(unknown)}"
        )

    raw = arrangement.get("bar_cycle")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise midi.ManifestError("arrangement.bar_cycle must be an object")
    unknown = set(raw) - {"length", "mute_bars"}
    if unknown:
        raise midi.ManifestError(
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
    """Return absolute accompaniment bars muted by the arrangement cycle."""
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


def resolve_track(
    track: dict[str, Any],
    meter: list[int],
    groove_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Expand a named groove preset into an isolated concrete groove definition."""
    has_inline = "groove" in track
    has_preset = "groove_preset" in track
    if has_inline and has_preset:
        raise midi.ManifestError("drum track cannot define both groove and groove_preset")
    if (has_inline or has_preset) and track["role"] != "drums":
        raise midi.ManifestError(
            "groove and groove_preset are only supported on drum tracks"
        )
    if "bass" in track and track["role"] != "bass":
        raise midi.ManifestError("bass spec is only supported on bass tracks")

    resolved = copy.deepcopy(track)
    if has_preset:
        preset_id = track["groove_preset"]
        if not isinstance(preset_id, str) or not preset_id:
            raise midi.ManifestError("groove_preset must be a non-empty string")
        preset = groove.get_preset(groove_catalog, preset_id)
        if preset["meter"] != meter:
            raise midi.ManifestError(
                f"groove preset {preset_id!r} uses meter "
                f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
            )
        resolved["groove"] = groove.resolved_groove(groove_catalog, preset_id)
        resolved.pop("groove_preset", None)

    if "groove" in resolved:
        groove.parse_groove(
            resolved["groove"],
            meter=meter,
            default_velocity=int(resolved.get("velocity", 78)),
        )
    if "bass" in resolved:
        bass.parse_bass(resolved["bass"])
    return resolved


def _groove_specs(
    tracks: list[dict[str, Any]],
    meter: list[int],
) -> list[groove.GrooveSpec]:
    return [
        groove.parse_groove(
            track["groove"],
            meter=meter,
            default_velocity=int(track.get("velocity", 78)),
        )
        for track in tracks
        if track["role"] == "drums" and "groove" in track
    ]


def _reference_groove(
    tracks: list[dict[str, Any]],
    meter: list[int],
) -> groove.GrooveSpec | None:
    specs = _groove_specs(tracks, meter)
    return specs[0] if len(specs) == 1 else None


def validate_manifest(
    manifest: dict[str, Any],
    groove_catalog: dict[str, Any],
) -> None:
    midi.validate_manifest(manifest)
    groove.validate_catalog(groove_catalog)
    parse_arrangement_cycle(manifest)
    resolved = [
        resolve_track(track, manifest["meter"], groove_catalog)
        for track in manifest["tracks"]
    ]
    groove_specs = _groove_specs(resolved, manifest["meter"])

    for track in resolved:
        if track["role"] != "bass" or "bass" not in track:
            continue
        spec = bass.parse_bass(track["bass"])
        if bass.requires_groove(spec) and len(groove_specs) != 1:
            raise midi.ManifestError(
                f"bass style {spec.style!r} requires exactly one groove-aware drum track"
            )


def _count_in_hits(
    spec: groove.GrooveSpec,
    *,
    meter: list[int],
    beat_ticks: int,
) -> list[groove.GrooveHit]:
    if spec.count_in == "none":
        return []
    numerator, _ = meter
    return [
        groove.GrooveHit(
            tick=beat * beat_ticks,
            note=groove.GENERAL_MIDI_DRUMS["side_stick"],
            velocity=96 if beat == 0 else 78,
        )
        for beat in range(numerator)
    ]


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
    spec = groove.parse_groove(
        track["groove"],
        meter=meter,
        default_velocity=int(track.get("velocity", 78)),
    )
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(0, 0, midi.meta(0x03, track["name"].encode()))
    ]
    bar_steps = groove.steps_per_bar(meter, spec.subdivision)
    note_duration = max(24, min(90, bar_ticks // bar_steps // 2))

    for absolute_bar in range(total_bars):
        if absolute_bar in muted_bars:
            hits: list[groove.GrooveHit] = []
        elif absolute_bar < count_in_bars and spec.count_in != "groove":
            hits = _count_in_hits(spec, meter=meter, beat_ticks=beat_ticks)
        else:
            musical_bar = max(0, absolute_bar - count_in_bars)
            hits = groove.render_bar(
                spec,
                bar_index=musical_bar,
                meter=meter,
                bar_ticks=bar_ticks,
                tempo_bpm=tempo_bpm,
            )

        start = absolute_bar * bar_ticks
        for hit in hits:
            events.extend(
                midi.note_events(
                    channel=midi.DRUM_CHANNEL,
                    note=hit.note,
                    velocity=hit.velocity,
                    start=start + hit.tick,
                    duration=note_duration,
                )
            )
    return midi.track_bytes(events)


def _generate_legacy_drum_track(
    track: dict[str, Any],
    *,
    total_bars: int,
    bar_ticks: int,
    beat_ticks: int,
    muted_bars: set[int],
) -> bytes:
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(0, 0, midi.meta(0x03, track["name"].encode()))
    ]
    for bar_index in range(total_bars):
        if bar_index in muted_bars:
            continue
        start = bar_index * bar_ticks
        for beat in range(bar_ticks // beat_ticks):
            tick = start + beat * beat_ticks
            events.extend(
                midi.note_events(
                    channel=midi.DRUM_CHANNEL,
                    note=42,
                    velocity=56,
                    start=tick,
                    duration=60,
                )
            )
            if beat in {0, 2}:
                events.extend(
                    midi.note_events(
                        channel=midi.DRUM_CHANNEL,
                        note=36,
                        velocity=88,
                        start=tick,
                        duration=90,
                    )
                )
            if beat in {1, 3}:
                events.extend(
                    midi.note_events(
                        channel=midi.DRUM_CHANNEL,
                        note=38,
                        velocity=82,
                        start=tick,
                        duration=90,
                    )
                )
    return midi.track_bytes(events)


def render(manifest: dict[str, Any], groove_catalog: dict[str, Any]) -> bytes:
    """Render a resolved BackingTrackSpec to deterministic Type 1 MIDI bytes."""
    validate_manifest(manifest, groove_catalog)

    numerator, denominator = manifest["meter"]
    beat_ticks = midi.TPQN * 4 // denominator
    bar_ticks = numerator * beat_ticks
    chords = midi.arrangement_chords(manifest)
    muted_bars = arrangement_muted_bars(manifest)
    masked_chords = [
        "N.C." if index in muted_bars else chord
        for index, chord in enumerate(chords)
    ]
    resolved_tracks = [
        resolve_track(track, manifest["meter"], groove_catalog)
        for track in manifest["tracks"]
    ]
    reference_groove = _reference_groove(resolved_tracks, manifest["meter"])

    tracks = [midi.conductor_track(manifest, bar_ticks)]
    for track in resolved_tracks:
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
        elif track["role"] == "bass" and "bass" in track:
            tracks.append(
                bass.generate_track(
                    track,
                    chords=masked_chords,
                    count_in_bars=manifest["count_in_bars"],
                    meter=manifest["meter"],
                    bar_ticks=bar_ticks,
                    beat_ticks=beat_ticks,
                    tempo_bpm=manifest["tempo_bpm"],
                    groove_spec=reference_groove,
                )
            )
        else:
            tracks.append(midi.generate_track(track, masked_chords, bar_ticks, beat_ticks))

    header = midi.midi_chunk(
        b"MThd",
        struct.pack(">HHH", 1, len(tracks), midi.TPQN),
    )
    return header + b"".join(tracks)
