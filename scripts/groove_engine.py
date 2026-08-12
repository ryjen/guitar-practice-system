#!/usr/bin/env python3
"""Deterministic groove-aware backing-track MIDI generation.

This module adds a reusable groove domain model above ``midi_workflow``.
Backing-track manifests remain the source of truth; a drum track may opt into
an explicit ``groove`` object while legacy manifests keep the existing MIDI
renderer behavior.
"""

from __future__ import annotations

import json
import random
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import midi_workflow


GENERAL_MIDI_DRUMS = {
    "kick": 36,
    "side_stick": 37,
    "snare": 38,
    "clap": 39,
    "closed_hat": 42,
    "pedal_hat": 44,
    "open_hat": 46,
    "low_tom": 45,
    "mid_tom": 47,
    "high_tom": 50,
    "crash": 49,
    "ride": 51,
}
SUPPORTED_SUBDIVISIONS = {4, 8, 16, 32}
COUNT_IN_MODES = {"click", "groove", "none"}


@dataclass(frozen=True)
class GrooveInstrument:
    name: str
    note: int
    steps: tuple[int, ...]
    velocity: int
    accent_steps: tuple[int, ...]
    accent_velocity: int
    variation_every_bars: int | None = None
    variation_steps: tuple[int, ...] = ()


@dataclass(frozen=True)
class GrooveSpec:
    subdivision: int
    swing: float
    humanize_ms: int
    velocity_variance: int
    seed: int
    count_in: str
    instruments: tuple[GrooveInstrument, ...]


@dataclass(frozen=True)
class GrooveHit:
    tick: int
    note: int
    velocity: int


def steps_per_bar(meter: list[int] | tuple[int, int], subdivision: int) -> int:
    numerator, denominator = meter
    product = numerator * subdivision
    if product % denominator:
        raise midi_workflow.ManifestError(
            f"subdivision {subdivision} does not divide meter {numerator}/{denominator}"
        )
    return product // denominator


def _int_field(
    value: Any,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi_workflow.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi_workflow.ManifestError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def _step_list(value: Any, *, name: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        isinstance(step, bool) or not isinstance(step, int) for step in value
    ):
        raise midi_workflow.ManifestError(f"{name} must be a list of integers")
    if len(set(value)) != len(value):
        raise midi_workflow.ManifestError(f"{name} cannot contain duplicate steps")
    if any(step < 0 or step >= maximum for step in value):
        raise midi_workflow.ManifestError(
            f"{name} steps must be between 0 and {maximum - 1}"
        )
    return tuple(sorted(value))


def parse_groove(
    raw: Any,
    *,
    meter: list[int] | tuple[int, int],
    default_velocity: int = 78,
) -> GrooveSpec:
    if not isinstance(raw, dict):
        raise midi_workflow.ManifestError("groove must be an object")

    subdivision = _int_field(
        raw.get("subdivision", 16),
        name="groove.subdivision",
        minimum=4,
        maximum=32,
    )
    if subdivision not in SUPPORTED_SUBDIVISIONS:
        raise midi_workflow.ManifestError(
            f"groove.subdivision must be one of {sorted(SUPPORTED_SUBDIVISIONS)}"
        )
    bar_steps = steps_per_bar(meter, subdivision)

    swing_raw = raw.get("swing", 0.0)
    if isinstance(swing_raw, bool) or not isinstance(swing_raw, (int, float)):
        raise midi_workflow.ManifestError("groove.swing must be numeric")
    swing = float(swing_raw)
    if not 0.0 <= swing <= 0.5:
        raise midi_workflow.ManifestError("groove.swing must be between 0.0 and 0.5")

    humanize_ms = _int_field(
        raw.get("humanize_ms", 0),
        name="groove.humanize_ms",
        minimum=0,
        maximum=30,
    )
    velocity_variance = _int_field(
        raw.get("velocity_variance", 0),
        name="groove.velocity_variance",
        minimum=0,
        maximum=24,
    )
    seed = _int_field(
        raw.get("seed", 0),
        name="groove.seed",
        minimum=0,
        maximum=2_147_483_647,
    )

    count_in = raw.get("count_in", "click")
    if not isinstance(count_in, str) or count_in not in COUNT_IN_MODES:
        raise midi_workflow.ManifestError(
            f"groove.count_in must be one of {sorted(COUNT_IN_MODES)}"
        )

    instruments_raw = raw.get("instruments")
    if not isinstance(instruments_raw, dict) or not instruments_raw:
        raise midi_workflow.ManifestError("groove.instruments must be a non-empty object")

    instruments: list[GrooveInstrument] = []
    for name, config in instruments_raw.items():
        if name not in GENERAL_MIDI_DRUMS:
            raise midi_workflow.ManifestError(f"unsupported groove instrument: {name}")
        if not isinstance(config, dict):
            raise midi_workflow.ManifestError(
                f"groove.instruments.{name} must be an object"
            )

        steps = _step_list(
            config.get("steps", []),
            name=f"groove.instruments.{name}.steps",
            maximum=bar_steps,
        )
        velocity = _int_field(
            config.get("velocity", default_velocity),
            name=f"groove.instruments.{name}.velocity",
            minimum=1,
            maximum=127,
        )
        accent_steps = _step_list(
            config.get("accent_steps", []),
            name=f"groove.instruments.{name}.accent_steps",
            maximum=bar_steps,
        )
        accent_velocity = _int_field(
            config.get("accent_velocity", min(127, velocity + 12)),
            name=f"groove.instruments.{name}.accent_velocity",
            minimum=1,
            maximum=127,
        )

        variation_every_bars: int | None = None
        variation_steps: tuple[int, ...] = ()
        variation = config.get("variation")
        if variation is not None:
            if not isinstance(variation, dict):
                raise midi_workflow.ManifestError(
                    f"groove.instruments.{name}.variation must be an object"
                )
            variation_every_bars = _int_field(
                variation.get("every_bars"),
                name=f"groove.instruments.{name}.variation.every_bars",
                minimum=1,
                maximum=64,
            )
            variation_steps = _step_list(
                variation.get("steps", []),
                name=f"groove.instruments.{name}.variation.steps",
                maximum=bar_steps,
            )

        instruments.append(
            GrooveInstrument(
                name=name,
                note=GENERAL_MIDI_DRUMS[name],
                steps=steps,
                velocity=velocity,
                accent_steps=accent_steps,
                accent_velocity=accent_velocity,
                variation_every_bars=variation_every_bars,
                variation_steps=variation_steps,
            )
        )

    return GrooveSpec(
        subdivision=subdivision,
        swing=swing,
        humanize_ms=humanize_ms,
        velocity_variance=velocity_variance,
        seed=seed,
        count_in=count_in,
        instruments=tuple(instruments),
    )


def validate_manifest(manifest: dict[str, Any]) -> None:
    midi_workflow.validate_manifest(manifest)
    meter = manifest["meter"]
    for track in manifest["tracks"]:
        groove = track.get("groove")
        if groove is None:
            continue
        if track["role"] != "drums":
            raise midi_workflow.ManifestError("groove is only supported on drum tracks")
        parse_groove(
            groove,
            meter=meter,
            default_velocity=int(track.get("velocity", 78)),
        )


def _stable_rng(seed: int, *, bar_index: int, note: int, step: int) -> random.Random:
    mixed = (
        seed
        ^ ((bar_index + 1) * 0x9E3779B1)
        ^ (note * 0x85EBCA6B)
        ^ (step * 0xC2B2AE35)
    ) & 0xFFFFFFFF
    return random.Random(mixed)


def render_bar(
    spec: GrooveSpec,
    *,
    bar_index: int,
    meter: list[int] | tuple[int, int],
    bar_ticks: int,
    tempo_bpm: int,
) -> list[GrooveHit]:
    bar_steps = steps_per_bar(meter, spec.subdivision)
    if bar_ticks % bar_steps:
        raise midi_workflow.ManifestError(
            "groove subdivision cannot be represented exactly at the current MIDI resolution"
        )
    step_ticks = bar_ticks // bar_steps
    humanize_ticks = round(
        spec.humanize_ms * midi_workflow.TPQN * tempo_bpm / 60_000
    )

    hits: list[GrooveHit] = []
    for instrument in spec.instruments:
        steps = instrument.steps
        if (
            instrument.variation_every_bars is not None
            and (bar_index + 1) % instrument.variation_every_bars == 0
        ):
            steps = instrument.variation_steps

        for step in steps:
            rng = _stable_rng(
                spec.seed,
                bar_index=bar_index,
                note=instrument.note,
                step=step,
            )
            tick = step * step_ticks
            if step % 2 == 1 and spec.swing:
                tick += round(step_ticks * spec.swing)
            if humanize_ticks:
                tick += rng.randint(-humanize_ticks, humanize_ticks)
            tick = max(0, min(bar_ticks - 1, tick))

            velocity = (
                instrument.accent_velocity
                if step in instrument.accent_steps
                else instrument.velocity
            )
            if spec.velocity_variance:
                velocity += rng.randint(
                    -spec.velocity_variance,
                    spec.velocity_variance,
                )
            velocity = max(1, min(127, velocity))
            hits.append(
                GrooveHit(
                    tick=tick,
                    note=instrument.note,
                    velocity=velocity,
                )
            )

    return sorted(hits, key=lambda hit: (hit.tick, hit.note))


def _count_in_hits(
    spec: GrooveSpec,
    *,
    meter: list[int] | tuple[int, int],
    beat_ticks: int,
) -> list[GrooveHit]:
    if spec.count_in == "none":
        return []
    numerator, _ = meter
    hits: list[GrooveHit] = []
    for beat in range(numerator):
        hits.append(
            GrooveHit(
                tick=beat * beat_ticks,
                note=GENERAL_MIDI_DRUMS["side_stick"],
                velocity=96 if beat == 0 else 78,
            )
        )
    return hits


def generate_drum_track(
    track: dict[str, Any],
    *,
    total_bars: int,
    count_in_bars: int,
    meter: list[int] | tuple[int, int],
    bar_ticks: int,
    beat_ticks: int,
    tempo_bpm: int,
) -> bytes:
    spec = parse_groove(
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
    bar_steps = steps_per_bar(meter, spec.subdivision)
    note_duration = max(24, min(90, bar_ticks // bar_steps // 2))

    for absolute_bar in range(total_bars):
        if absolute_bar < count_in_bars and spec.count_in != "groove":
            hits = _count_in_hits(spec, meter=meter, beat_ticks=beat_ticks)
        else:
            musical_bar = max(0, absolute_bar - count_in_bars)
            hits = render_bar(
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


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)

    numerator, denominator = manifest["meter"]
    beat_ticks = midi_workflow.TPQN * 4 // denominator
    bar_ticks = numerator * beat_ticks
    chords = midi_workflow.arrangement_chords(manifest)

    tracks = [midi_workflow.conductor_track(manifest, bar_ticks)]
    for track in manifest["tracks"]:
        if track["role"] == "drums" and "groove" in track:
            tracks.append(
                generate_drum_track(
                    track,
                    total_bars=len(chords),
                    count_in_bars=manifest["count_in_bars"],
                    meter=manifest["meter"],
                    bar_ticks=bar_ticks,
                    beat_ticks=beat_ticks,
                    tempo_bpm=manifest["tempo_bpm"],
                )
            )
        else:
            tracks.append(
                midi_workflow.generate_track(
                    track,
                    chords,
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
