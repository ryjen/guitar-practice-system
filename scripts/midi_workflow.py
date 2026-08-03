#!/usr/bin/env python3
"""Generate and validate portable Type 1 MIDI backing tracks from JSON manifests.

The implementation intentionally uses only the Python standard library so the
manifest remains the source of truth and generated MIDI can be reproduced in
minimal environments.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

TPQN = 480
DRUM_CHANNEL = 9


class ManifestError(ValueError):
    """Raised when a backing-track manifest is incomplete or inconsistent."""


def vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ values must be non-negative")
    buffer = value & 0x7F
    result = bytearray([buffer])
    value >>= 7
    while value:
        buffer = (value & 0x7F) | 0x80
        result.insert(0, buffer)
        value >>= 7
    return bytes(result)


def meta(kind: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([kind]) + vlq(len(payload)) + payload


def midi_chunk(kind: bytes, payload: bytes) -> bytes:
    return kind + struct.pack(">I", len(payload)) + payload


@dataclass(frozen=True)
class TimedEvent:
    tick: int
    priority: int
    data: bytes


def track_bytes(events: Iterable[TimedEvent]) -> bytes:
    ordered = sorted(events, key=lambda event: (event.tick, event.priority))
    previous = 0
    body = bytearray()
    for event in ordered:
        if event.tick < previous:
            raise ValueError("events are not monotonic")
        body.extend(vlq(event.tick - previous))
        body.extend(event.data)
        previous = event.tick
    body.extend(vlq(0))
    body.extend(meta(0x2F, b""))
    return midi_chunk(b"MTrk", bytes(body))


def note_events(
    *, channel: int, note: int, velocity: int, start: int, duration: int
) -> list[TimedEvent]:
    if not 0 <= channel <= 15:
        raise ManifestError(f"invalid MIDI channel: {channel}")
    if not 0 <= note <= 127:
        raise ManifestError(f"invalid MIDI note: {note}")
    if not 1 <= velocity <= 127:
        raise ManifestError(f"invalid velocity: {velocity}")
    if duration <= 0:
        raise ManifestError("note duration must be positive")
    return [
        TimedEvent(start, 20, bytes([0x90 | channel, note, velocity])),
        TimedEvent(start + duration, 10, bytes([0x80 | channel, note, 0])),
    ]


def require(manifest: dict[str, Any], key: str, expected: type) -> Any:
    value = manifest.get(key)
    if not isinstance(value, expected):
        raise ManifestError(f"{key!r} must be {expected.__name__}")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest, "id", str)
    require(manifest, "title", str)
    tempo = require(manifest, "tempo_bpm", int)
    if not 20 <= tempo <= 300:
        raise ManifestError("tempo_bpm must be between 20 and 300")

    meter = require(manifest, "meter", list)
    if len(meter) != 2 or not all(isinstance(value, int) for value in meter):
        raise ManifestError("meter must be [numerator, denominator]")
    numerator, denominator = meter
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
        raise ManifestError("unsupported meter")

    require(manifest, "key_signature", str)
    count_in = require(manifest, "count_in_bars", int)
    if count_in < 0:
        raise ManifestError("count_in_bars cannot be negative")

    sections = require(manifest, "sections", list)
    if not sections:
        raise ManifestError("sections cannot be empty")
    for section in sections:
        if not isinstance(section, dict):
            raise ManifestError("each section must be an object")
        require(section, "name", str)
        bars = require(section, "bars", int)
        chords = require(section, "chords", list)
        if bars <= 0 or len(chords) != bars:
            raise ManifestError("each section needs exactly one chord per bar")
        if not all(isinstance(chord, str) for chord in chords):
            raise ManifestError("chords must be strings")

    tracks = require(manifest, "tracks", list)
    names: set[str] = set()
    channels: set[int] = set()
    for track in tracks:
        if not isinstance(track, dict):
            raise ManifestError("each track must be an object")
        name = require(track, "name", str)
        role = require(track, "role", str)
        channel = require(track, "channel", int)
        if name in names:
            raise ManifestError(f"duplicate track name: {name}")
        names.add(name)
        if role != "drums" and channel == DRUM_CHANNEL:
            raise ManifestError("channel 10 is reserved for drums")
        if role != "drums" and channel in channels:
            raise ManifestError(f"duplicate melodic channel: {channel + 1}")
        channels.add(channel)


NOTE_NAMES = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}


def chord_notes(symbol: str, octave: int = 3) -> list[int]:
    normalized = symbol.strip().upper().replace("♭", "B").replace("♯", "#")
    root_name = normalized[:2] if len(normalized) > 1 and normalized[1] in {"#", "B"} else normalized[:1]
    if root_name not in NOTE_NAMES:
        raise ManifestError(f"unsupported chord root: {symbol}")
    suffix = normalized[len(root_name) :]
    root = 12 * (octave + 1) + NOTE_NAMES[root_name]
    if suffix in {"", "MAJ"}:
        intervals = [0, 4, 7]
    elif suffix in {"M", "MIN"}:
        intervals = [0, 3, 7]
    elif suffix in {"7", "DOM7"}:
        intervals = [0, 4, 7, 10]
    elif suffix in {"M7", "MIN7"}:
        intervals = [0, 3, 7, 10]
    elif suffix in {"MAJ7"}:
        intervals = [0, 4, 7, 11]
    elif suffix in {"5"}:
        intervals = [0, 7]
    else:
        raise ManifestError(f"unsupported chord quality: {symbol}")
    return [root + interval for interval in intervals]


def key_signature_payload(name: str) -> bytes:
    signatures = {
        "CB": (-7, 0), "GB": (-6, 0), "DB": (-5, 0), "AB": (-4, 0),
        "EB": (-3, 0), "BB": (-2, 0), "F": (-1, 0), "C": (0, 0),
        "G": (1, 0), "D": (2, 0), "A": (3, 0), "E": (4, 0),
        "B": (5, 0), "F#": (6, 0), "C#": (7, 0),
        "ABM": (-7, 1), "EBM": (-6, 1), "BBM": (-5, 1), "FM": (-4, 1),
        "CM": (-3, 1), "GM": (-2, 1), "DM": (-1, 1), "AM": (0, 1),
        "EM": (1, 1), "BM": (2, 1), "F#M": (3, 1), "C#M": (4, 1),
    }
    normalized = name.upper().replace("MIN", "M")
    if normalized not in signatures:
        raise ManifestError(f"unsupported key signature: {name}")
    sharps, minor = signatures[normalized]
    return struct.pack("bb", sharps, minor)


def conductor_track(manifest: dict[str, Any], bar_ticks: int) -> bytes:
    tempo = manifest["tempo_bpm"]
    numerator, denominator = manifest["meter"]
    denominator_power = int(math.log2(denominator))
    events = [
        TimedEvent(0, 0, meta(0x03, b"Conductor")),
        TimedEvent(0, 1, meta(0x51, int(60_000_000 / tempo).to_bytes(3, "big"))),
        TimedEvent(0, 2, meta(0x58, bytes([numerator, denominator_power, 24, 8]))),
        TimedEvent(0, 3, meta(0x59, key_signature_payload(manifest["key_signature"]))),
        TimedEvent(0, 4, meta(0x06, b"COUNT-IN")),
    ]
    bar = manifest["count_in_bars"]
    for section in manifest["sections"]:
        events.append(TimedEvent(bar * bar_ticks, 4, meta(0x06, section["name"].encode())))
        bar += section["bars"]
    events.append(TimedEvent(bar * bar_ticks, 4, meta(0x06, b"END")))
    return track_bytes(events)


def arrangement_chords(manifest: dict[str, Any]) -> list[str]:
    result = ["N.C."] * manifest["count_in_bars"]
    for section in manifest["sections"]:
        result.extend(section["chords"])
    return result


def generate_track(track: dict[str, Any], chords: list[str], bar_ticks: int, beat_ticks: int) -> bytes:
    name = track["name"]
    role = track["role"]
    channel = track["channel"]
    velocity = int(track.get("velocity", 78))
    events: list[TimedEvent] = [TimedEvent(0, 0, meta(0x03, name.encode()))]
    if role != "drums":
        program = int(track.get("program", 0))
        events.append(TimedEvent(0, 5, bytes([0xC0 | channel, program])))

    for bar_index, chord in enumerate(chords):
        start = bar_index * bar_ticks
        if role == "drums":
            for beat in range(bar_ticks // beat_ticks):
                tick = start + beat * beat_ticks
                events.extend(note_events(channel=DRUM_CHANNEL, note=42, velocity=56, start=tick, duration=60))
                if beat in {0, 2}:
                    events.extend(note_events(channel=DRUM_CHANNEL, note=36, velocity=88, start=tick, duration=90))
                if beat in {1, 3}:
                    events.extend(note_events(channel=DRUM_CHANNEL, note=38, velocity=82, start=tick, duration=90))
        elif chord != "N.C.":
            notes = chord_notes(chord)
            if role == "bass":
                root = notes[0] - 12
                fifth = root + 7
                for beat, note in enumerate([root, fifth, root, fifth]):
                    events.extend(note_events(channel=channel, note=note, velocity=velocity, start=start + beat * beat_ticks, duration=int(beat_ticks * 0.82)))
            elif role in {"keys", "pad"}:
                duration = bar_ticks - 30
                for note in notes:
                    events.extend(note_events(channel=channel, note=note + 12, velocity=velocity, start=start, duration=duration))
            else:
                root = notes[0]
                events.extend(note_events(channel=channel, note=root, velocity=velocity, start=start, duration=bar_ticks - 30))
    return track_bytes(events)


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    numerator, denominator = manifest["meter"]
    beat_ticks = TPQN * 4 // denominator
    bar_ticks = numerator * beat_ticks
    chords = arrangement_chords(manifest)
    tracks = [conductor_track(manifest, bar_ticks)]
    tracks.extend(generate_track(track, chords, bar_ticks, beat_ticks) for track in manifest["tracks"])
    header = midi_chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), TPQN))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + b"".join(tracks))


def read_vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        if offset >= len(data):
            raise ManifestError("truncated variable-length quantity")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80 == 0:
            return value, offset


def inspect_midi(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 14 or data[:4] != b"MThd":
        raise ManifestError("missing MIDI header")
    header_length = struct.unpack(">I", data[4:8])[0]
    if header_length != 6:
        raise ManifestError("unsupported MIDI header length")
    format_type, track_count, division = struct.unpack(">HHH", data[8:14])
    if format_type != 1:
        raise ManifestError("expected Type 1 MIDI")
    offset = 14
    names: list[str] = []
    markers: list[str] = []
    tempo_events = 0
    meter_events = 0
    key_events = 0
    parsed_tracks = 0
    while offset < len(data):
        if data[offset : offset + 4] != b"MTrk":
            raise ManifestError("missing track chunk")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        track = data[offset + 8 : offset + 8 + length]
        if len(track) != length:
            raise ManifestError("truncated track chunk")
        parsed_tracks += 1
        cursor = 0
        running_status: int | None = None
        while cursor < len(track):
            _, cursor = read_vlq(track, cursor)
            status = track[cursor]
            if status < 0x80:
                if running_status is None:
                    raise ManifestError("invalid running status")
                status = running_status
            else:
                cursor += 1
                if status < 0xF0:
                    running_status = status
            if status == 0xFF:
                kind = track[cursor]
                cursor += 1
                size, cursor = read_vlq(track, cursor)
                payload = track[cursor : cursor + size]
                cursor += size
                if kind == 0x03:
                    names.append(payload.decode(errors="replace"))
                elif kind == 0x06:
                    markers.append(payload.decode(errors="replace"))
                elif kind == 0x51:
                    tempo_events += 1
                elif kind == 0x58:
                    meter_events += 1
                elif kind == 0x59:
                    key_events += 1
            elif status in {0xF0, 0xF7}:
                size, cursor = read_vlq(track, cursor)
                cursor += size
            else:
                message = status & 0xF0
                data_size = 1 if message in {0xC0, 0xD0} else 2
                if track[cursor - 1] < 0x80:
                    cursor += data_size - 1
                else:
                    cursor += data_size
        offset += 8 + length
    if parsed_tracks != track_count:
        raise ManifestError("header track count does not match chunks")
    return {
        "format": format_type,
        "tracks": track_count,
        "division": division,
        "track_names": names,
        "markers": markers,
        "tempo_events": tempo_events,
        "meter_events": meter_events,
        "key_events": key_events,
    }


def validate_output(manifest_path: Path, midi_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    report = inspect_midi(midi_path)
    expected_names = ["Conductor"] + [track["name"] for track in manifest["tracks"]]
    if report["track_names"] != expected_names:
        raise ManifestError(f"track names differ: {report['track_names']} != {expected_names}")
    expected_markers = ["COUNT-IN"] + [section["name"] for section in manifest["sections"]] + ["END"]
    if report["markers"] != expected_markers:
        raise ManifestError(f"markers differ: {report['markers']} != {expected_markers}")
    if not all(report[key] == 1 for key in ("tempo_events", "meter_events", "key_events")):
        raise ManifestError("conductor metadata must contain one tempo, meter, and key event")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("manifest", type=Path)
    generate_parser.add_argument("output", type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("manifest", type=Path)
    validate_parser.add_argument("midi", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate(args.manifest, args.output)
            report = validate_output(args.manifest, args.output)
        else:
            report = validate_output(args.manifest, args.midi)
    except (OSError, json.JSONDecodeError, ManifestError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
