"""Deterministic Type-1 MIDI rendering directly from canonical Score IR."""

from __future__ import annotations

import struct
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from guitar_practice.domain import midi, score


class ScoreMidiError(ValueError):
    """Score IR cannot be represented safely at the repository MIDI resolution."""


def _fraction(value: Any, label: str) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ScoreMidiError(f"{label} must be a rational pair")
    numerator, denominator = value
    if denominator <= 0:
        raise ScoreMidiError(f"{label} denominator must be positive")
    return Fraction(numerator, denominator)


def _meter_for_bar(document: Mapping[str, Any], bar: int) -> tuple[int, int]:
    active = document["meter_map"][0]
    for candidate in document["meter_map"][1:]:
        if candidate["bar"] > bar:
            break
        active = candidate
    return int(active["beats"]), int(active["beat_unit"])


def _bar_starts_quarters(document: Mapping[str, Any]) -> tuple[Fraction, ...]:
    starts = [Fraction(0)]
    for bar in range(1, len(document["bars"]) + 1):
        beats, beat_unit = _meter_for_bar(document, bar)
        starts.append(starts[-1] + Fraction(beats * 4, beat_unit))
    return tuple(starts)


def _location_quarters(
    document: Mapping[str, Any],
    location: Mapping[str, Any],
    starts: tuple[Fraction, ...],
) -> Fraction:
    bar = int(location["bar"])
    beat = _fraction(location["beat"], "location beat")
    _, beat_unit = _meter_for_bar(document, bar)
    return starts[bar - 1] + (beat - 1) * Fraction(4, beat_unit)


def _ticks(quarters: Fraction, label: str) -> int:
    exact = quarters * midi.TPQN
    if exact.denominator != 1:
        raise ScoreMidiError(
            f"{label} cannot be represented exactly at {midi.TPQN} PPQN"
        )
    return exact.numerator


def _tempo_event(
    document: Mapping[str, Any],
    point: Mapping[str, Any],
    starts: tuple[Fraction, ...],
) -> midi.TimedEvent:
    bpm = float(point["bpm"])
    beat_unit = _fraction(point["beat_unit"], "tempo beat_unit")
    quarter_bpm = bpm * float(beat_unit * 4)
    if quarter_bpm <= 0:
        raise ScoreMidiError("tempo must resolve to positive quarter-note BPM")
    micros = round(60_000_000 / quarter_bpm)
    if not 1 <= micros <= 0xFFFFFF:
        raise ScoreMidiError(f"tempo cannot be encoded in MIDI: {bpm}")
    return midi.TimedEvent(
        _ticks(
            _location_quarters(document, point["location"], starts),
            "tempo location",
        ),
        1,
        midi.meta(0x51, int(micros).to_bytes(3, "big")),
    )


def _meter_event(
    starts: tuple[Fraction, ...],
    point: Mapping[str, Any],
) -> midi.TimedEvent:
    denominator = int(point["beat_unit"])
    denominator_power = denominator.bit_length() - 1
    return midi.TimedEvent(
        _ticks(starts[int(point["bar"]) - 1], "meter location"),
        2,
        midi.meta(
            0x58,
            bytes([int(point["beats"]), denominator_power, 24, 8]),
        ),
    )


def _key_event(
    starts: tuple[Fraction, ...],
    point: Mapping[str, Any],
) -> midi.TimedEvent | None:
    mode = str(point["mode"]).casefold()
    if mode not in {"major", "minor"}:
        return None
    return midi.TimedEvent(
        _ticks(starts[int(point["bar"]) - 1], "key location"),
        3,
        midi.meta(
            0x59,
            struct.pack("bb", int(point["fifths"]), 1 if mode == "minor" else 0),
        ),
    )


def _marker_events(
    document: Mapping[str, Any],
    starts: tuple[Fraction, ...],
) -> list[midi.TimedEvent]:
    events: list[midi.TimedEvent] = []
    if document.get("rehearsal_marks"):
        for item in document["rehearsal_marks"]:
            events.append(
                midi.TimedEvent(
                    _ticks(
                        _location_quarters(document, item["location"], starts),
                        "rehearsal location",
                    ),
                    4,
                    midi.meta(0x06, str(item["label"]).encode("utf-8")),
                )
            )
    elif document.get("sections"):
        for section in document["sections"]:
            events.append(
                midi.TimedEvent(
                    _ticks(
                        starts[int(section["start_bar"]) - 1],
                        "section location",
                    ),
                    4,
                    midi.meta(0x06, str(section["label"]).encode("utf-8")),
                )
            )
    events.append(
        midi.TimedEvent(
            _ticks(starts[-1], "score end"),
            4,
            midi.meta(0x06, b"END"),
        )
    )
    return events


def _conductor(
    document: Mapping[str, Any],
    starts: tuple[Fraction, ...],
) -> bytes:
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(0, 0, midi.meta(0x03, b"Conductor")),
    ]
    events.extend(
        _tempo_event(document, point, starts)
        for point in document["tempo_map"]
    )
    events.extend(
        _meter_event(starts, point)
        for point in document["meter_map"]
    )
    for point in document.get("key_map", []):
        event = _key_event(starts, point)
        if event is not None:
            events.append(event)
    events.extend(_marker_events(document, starts))
    return midi.track_bytes(events)


_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _midi_note(pitch: Mapping[str, Any]) -> int:
    value = (
        12 * (int(pitch["octave"]) + 1)
        + _PITCH_CLASS[str(pitch["step"])]
        + int(pitch["alter"])
    )
    if not 0 <= value <= 127:
        raise ScoreMidiError("pitch is outside MIDI range")
    return value


def _channel_for(part: Mapping[str, Any], fallback_index: int) -> int:
    identity = part["instrument"].get("midi", {})
    if identity.get("percussion") is True or part["role"] == "drums":
        return midi.DRUM_CHANNEL
    if "channel" in identity:
        return int(identity["channel"]) - 1
    melodic = tuple(channel for channel in range(16) if channel != midi.DRUM_CHANNEL)
    return melodic[fallback_index % len(melodic)]


def _program_for(part: Mapping[str, Any]) -> int | None:
    identity = part["instrument"].get("midi", {})
    value = identity.get("program")
    return int(value) if value is not None else None


def _note_timing(
    document: Mapping[str, Any],
    event: Mapping[str, Any],
    starts: tuple[Fraction, ...],
) -> tuple[int, int]:
    start_quarters = _location_quarters(document, event["location"], starts)
    duration_quarters = _fraction(event["duration"], "note duration") * 4
    start = _ticks(start_quarters, "note location")
    duration = _ticks(duration_quarters, "note duration")
    if duration <= 0:
        raise ScoreMidiError("note duration must be positive")
    return start, duration


def _part_note_events(
    document: Mapping[str, Any],
    part: Mapping[str, Any],
    channel: int,
    starts: tuple[Fraction, ...],
) -> list[midi.TimedEvent]:
    notes: list[tuple[int, int, int, int, str | None]] = []
    for event in part["events"]:
        if event["kind"] != "note":
            continue
        start, duration = _note_timing(document, event, starts)
        notes.append(
            (
                start,
                duration,
                int(event["voice"]),
                _midi_note(event["pitch"]),
                event.get("tie"),
            )
        )
    notes.sort(key=lambda item: (item[0], item[2], item[3]))

    result: list[midi.TimedEvent] = []
    pending: dict[tuple[int, int], tuple[int, int]] = {}
    for start, duration, voice, pitch, tie in notes:
        key = (voice, pitch)
        end = start + duration
        if tie == "start":
            if key in pending:
                raise ScoreMidiError("tie starts before the previous tie chain closes")
            pending[key] = (start, end)
            continue
        if tie in {"continue", "stop"}:
            if key not in pending:
                raise ScoreMidiError("tie continuation has no matching start")
            chain_start, chain_end = pending[key]
            if chain_end != start:
                raise ScoreMidiError("tie chain is not temporally contiguous")
            if tie == "continue":
                pending[key] = (chain_start, end)
                continue
            del pending[key]
            result.extend(
                midi.note_events(
                    channel=channel,
                    note=pitch,
                    velocity=80,
                    start=chain_start,
                    duration=end - chain_start,
                )
            )
            continue

        if key in pending:
            raise ScoreMidiError("untied note occurs before tie chain closes")
        result.extend(
            midi.note_events(
                channel=channel,
                note=pitch,
                velocity=80,
                start=start,
                duration=duration,
            )
        )

    if pending:
        raise ScoreMidiError("score contains an unterminated tie chain")
    return result


def _part_track(
    document: Mapping[str, Any],
    part: Mapping[str, Any],
    fallback_index: int,
    starts: tuple[Fraction, ...],
) -> bytes:
    channel = _channel_for(part, fallback_index)
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(
            0,
            0,
            midi.meta(0x03, str(part["name"]).encode("utf-8")),
        )
    ]
    program = _program_for(part)
    if channel != midi.DRUM_CHANNEL and program is not None:
        events.append(
            midi.TimedEvent(
                0,
                5,
                bytes([0xC0 | channel, program]),
            )
        )
    events.extend(_part_note_events(document, part, channel, starts))
    return midi.track_bytes(events)


def render_score_midi(document: Mapping[str, Any]) -> bytes:
    """Render one validated Score IR realization as deterministic Type-1 MIDI."""

    canonical = dict(document)
    try:
        score.validate(canonical)
    except score.ScoreError as exc:
        raise ScoreMidiError(str(exc)) from exc

    starts = _bar_starts_quarters(canonical)
    chunks = [_conductor(canonical, starts)]
    chunks.extend(
        _part_track(canonical, part, index, starts)
        for index, part in enumerate(canonical["parts"])
    )
    header = midi.midi_chunk(
        b"MThd",
        struct.pack(">HHH", 1, len(chunks), midi.TPQN),
    )
    return header + b"".join(chunks)
