from __future__ import annotations

import unittest

from guitar_practice.domain import midi
from guitar_practice.domain.song import (
    ClassificationSource,
    MeterPoint,
    NoteEvent,
    Song,
    SongTrack,
    TempoPoint,
    TrackClassification,
    TrackRole,
)
from guitar_practice.domain.song_midi import render_song_midi
from guitar_practice.domain.song_stems import scale_tempo, select_backing_tracks


def _track(
    track_id: str,
    role: TrackRole,
    *,
    channel: int,
    program: int | None,
    note: int,
    velocity: int,
) -> SongTrack:
    source = ClassificationSource.PERCUSSION if role is TrackRole.DRUMS else ClassificationSource.MIDI
    return SongTrack(
        id=track_id,
        name=track_id.title(),
        classification=TrackClassification(role, source),
        midi_program=program,
        midi_channel=channel,
        is_percussion=role is TrackRole.DRUMS,
        notes=(NoteEvent(position=0.0, duration=1.0, midi_note=note, velocity=velocity),),
    )


class SongMidiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guitar = _track(
            "guitar", TrackRole.GUITAR, channel=1, program=29, note=64, velocity=100
        )
        self.bass = _track(
            "bass", TrackRole.BASS, channel=2, program=33, note=40, velocity=70
        )
        self.drums = _track(
            "drums", TrackRole.DRUMS, channel=10, program=None, note=36, velocity=100
        )
        self.song = Song(
            source_id="fixture",
            title="Fixture",
            tracks=(self.guitar, self.bass, self.drums),
            tempo_map=(
                TempoPoint(position=0.0, bpm=120.0),
                TempoPoint(position=4.0, bpm=90.0),
            ),
            meter_map=(
                MeterPoint(position=0.0, numerator=4, denominator=4),
                MeterPoint(position=8.0, numerator=3, denominator=4),
            ),
        )

    def test_renders_type_one_conductor_and_selected_tracks(self) -> None:
        realized = scale_tempo(self.song, 0.75)
        selected = select_backing_tracks(realized)
        data = render_song_midi(realized, selected)
        report = midi.inspect(data)

        self.assertEqual(1, report["format"])
        self.assertEqual(midi.TPQN, report["division"])
        self.assertEqual(3, report["tracks"])
        self.assertEqual(["Conductor", "Bass", "Drums"], report["track_names"])
        self.assertEqual(2, report["tempo_events"])
        self.assertEqual(2, report["meter_events"])

    def test_preserves_program_channels_and_uses_drum_channel(self) -> None:
        realized = scale_tempo(self.song, 0.75)
        data = render_song_midi(realized, select_backing_tracks(realized))

        self.assertIn(bytes([0xC1, 33]), data)
        self.assertIn(bytes([0x91, 40, 70]), data)
        self.assertIn(bytes([0x99, 36, 100]), data)
        self.assertNotIn(bytes([0x90, 64, 100]), data)

    def test_tempo_and_meter_metadata_use_quarter_note_positions(self) -> None:
        realized = scale_tempo(self.song, 0.75)
        data = render_song_midi(realized, select_backing_tracks(realized))

        conductor_start = 14
        length = int.from_bytes(data[conductor_start + 4 : conductor_start + 8], "big")
        conductor = data[conductor_start + 8 : conductor_start + 8 + length]
        self.assertIn(b"\xff\x51\x03" + int(60_000_000 / 90.0).to_bytes(3, "big"), conductor)
        self.assertIn(b"\xff\x51\x03" + int(60_000_000 / 67.5).to_bytes(3, "big"), conductor)
        self.assertIn(b"\xff\x58\x04\x04\x02\x18\x08", conductor)
        self.assertIn(b"\xff\x58\x04\x03\x02\x18\x08", conductor)

    def test_rendering_is_deterministic(self) -> None:
        realized = scale_tempo(self.song, 0.75)
        selected = select_backing_tracks(realized)
        self.assertEqual(
            render_song_midi(realized, selected),
            render_song_midi(realized, selected),
        )


if __name__ == "__main__":
    unittest.main()
