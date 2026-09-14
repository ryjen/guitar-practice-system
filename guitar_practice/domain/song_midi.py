"""Deterministic Type-1 MIDI rendering for imported Song stems."""

from __future__ import annotations

import struct
from collections.abc import Sequence

from guitar_practice.domain import midi
from guitar_practice.domain.song import MeterPoint, Song, SongTrack, TempoPoint, TrackRole


def _tick(position: float) -> int:
    return round(position * midi.TPQN)


def _tempo_event(point: TempoPoint) -> midi.TimedEvent:
    micros = int(60_000_000 / point.bpm)
    if not 1 <= micros <= 0xFFFFFF:
        raise ValueError(f"tempo BPM cannot be encoded in MIDI: {point.bpm}")
    return midi.TimedEvent(
        _tick(point.position),
        1,
        midi.meta(0x51, micros.to_bytes(3, "big")),
    )


def _meter_event(point: MeterPoint) -> midi.TimedEvent:
    denominator_power = point.denominator.bit_length() - 1
    return midi.TimedEvent(
        _tick(point.position),
        2,
        midi.meta(
            0x58,
            bytes([point.numerator, denominator_power, 24, 8]),
        ),
    )


def _conductor(song: Song) -> bytes:
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(0, 0, midi.meta(0x03, b"Conductor")),
    ]
    events.extend(_tempo_event(point) for point in song.tempo_map)
    events.extend(_meter_event(point) for point in song.meter_map)
    return midi.track_bytes(events)


def _channel_for(track: SongTrack, fallback_index: int) -> int:
    if track.is_percussion or track.classification.role is TrackRole.DRUMS:
        return midi.DRUM_CHANNEL
    if track.midi_channel is not None:
        return track.midi_channel - 1
    melodic_channels = tuple(channel for channel in range(16) if channel != midi.DRUM_CHANNEL)
    return melodic_channels[fallback_index % len(melodic_channels)]


def _track_bytes(track: SongTrack, fallback_index: int) -> bytes:
    channel = _channel_for(track, fallback_index)
    events: list[midi.TimedEvent] = [
        midi.TimedEvent(0, 0, midi.meta(0x03, track.name.encode("utf-8"))),
    ]
    if channel != midi.DRUM_CHANNEL and track.midi_program is not None:
        events.append(midi.TimedEvent(0, 5, bytes([0xC0 | channel, track.midi_program])))
    for note in track.notes:
        events.extend(
            midi.note_events(
                channel=channel,
                note=note.midi_note,
                velocity=note.velocity,
                start=_tick(note.position),
                duration=max(1, _tick(note.duration)),
            )
        )
    return midi.track_bytes(events)


def render_song_midi(song: Song, tracks: Sequence[SongTrack]) -> bytes:
    """Render selected imported-song tracks to deterministic Type-1 MIDI bytes."""

    song_ids = {track.id for track in song.tracks}
    selected_ids = [track.id for track in tracks]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected tracks must have unique ids")
    unknown = set(selected_ids) - song_ids
    if unknown:
        raise ValueError(f"selected track id(s) are not part of song: {sorted(unknown)}")

    chunks = [_conductor(song)]
    chunks.extend(_track_bytes(track, index) for index, track in enumerate(tracks))
    header = midi.midi_chunk(
        b"MThd",
        struct.pack(">HHH", 1, len(chunks), midi.TPQN),
    )
    return header + b"".join(chunks)
