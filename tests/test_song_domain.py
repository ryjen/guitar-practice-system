from __future__ import annotations

import unittest

from guitar_practice.domain.song import (
    ClassificationSource,
    MeterPoint,
    NoteEvent,
    Song,
    SongTrack,
    TempoPoint,
    TrackClassification,
    TrackRole,
    classify_track,
    song_from_dict,
    song_to_dict,
)


class SongDomainTests(unittest.TestCase):
    def test_instrument_identity_precedes_name_heuristic(self) -> None:
        classification = classify_track(
            name="Lead Guitar",
            instrument_name="Electric Guitar",
            midi_program=29,
            is_percussion=False,
        )
        self.assertEqual(TrackRole.GUITAR, classification.role)
        self.assertEqual(ClassificationSource.INSTRUMENT, classification.source)

    def test_explicit_override_precedes_inferred_identity(self) -> None:
        classification = classify_track(
            name="Guitar",
            instrument_name="Electric Guitar",
            midi_program=29,
            is_percussion=False,
            override=TrackRole.OTHER,
        )
        self.assertEqual(TrackRole.OTHER, classification.role)
        self.assertEqual(ClassificationSource.EXPLICIT, classification.source)

    def test_percussion_identity_precedes_weak_name_heuristic(self) -> None:
        classification = classify_track(
            name="Guitar Scratch",
            instrument_name=None,
            midi_program=None,
            is_percussion=True,
        )
        self.assertEqual(TrackRole.DRUMS, classification.role)
        self.assertEqual(ClassificationSource.PERCUSSION, classification.source)

    def test_unknown_track_remains_non_destructive(self) -> None:
        classification = classify_track(
            name="Mystery Layer",
            instrument_name=None,
            midi_program=None,
            is_percussion=False,
        )
        self.assertEqual(TrackRole.UNKNOWN, classification.role)
        self.assertEqual(ClassificationSource.UNKNOWN, classification.source)

    def test_midi_program_family_can_classify_bass(self) -> None:
        classification = classify_track(
            name="Part 2",
            instrument_name=None,
            midi_program=33,
            is_percussion=False,
        )
        self.assertEqual(TrackRole.BASS, classification.role)
        self.assertEqual(ClassificationSource.MIDI, classification.source)

    def test_song_rejects_duplicate_track_ids(self) -> None:
        track = SongTrack(
            id="part-1",
            name="One",
            classification=TrackClassification(TrackRole.OTHER, ClassificationSource.EXPLICIT),
        )
        with self.assertRaises(ValueError):
            Song(source_id="fixture", title="Fixture", tracks=(track, track))

    def test_track_id_is_conservative_but_display_name_is_not(self) -> None:
        with self.assertRaises(ValueError):
            SongTrack(
                id="../escape",
                name="../../still display data",
                classification=TrackClassification(TrackRole.UNKNOWN, ClassificationSource.UNKNOWN),
            )

        track = SongTrack(
            id="part-1",
            name="../../still display data",
            classification=TrackClassification(TrackRole.UNKNOWN, ClassificationSource.UNKNOWN),
        )
        self.assertEqual("../../still display data", track.name)

    def test_note_events_validate_musical_position_and_midi_values(self) -> None:
        self.assertEqual(
            NoteEvent(position=1.5, duration=0.5, midi_note=64, velocity=90),
            NoteEvent(position=1.5, duration=0.5, midi_note=64, velocity=90),
        )
        for kwargs in (
            {"position": -1.0, "duration": 1.0, "midi_note": 60},
            {"position": 0.0, "duration": 0.0, "midi_note": 60},
            {"position": 0.0, "duration": 1.0, "midi_note": 128},
            {"position": 0.0, "duration": 1.0, "midi_note": 60, "velocity": 0},
        ):
            with self.assertRaises(ValueError):
                NoteEvent(**kwargs)

    def test_tempo_and_meter_validate_values(self) -> None:
        with self.assertRaises(ValueError):
            TempoPoint(position=0.0, bpm=0)
        with self.assertRaises(ValueError):
            TempoPoint(position=-1.0, bpm=120)
        with self.assertRaises(ValueError):
            MeterPoint(position=0.0, numerator=0, denominator=4)
        with self.assertRaises(ValueError):
            MeterPoint(position=0.0, numerator=4, denominator=3)

    def test_song_dict_round_trip_is_deterministic(self) -> None:
        song = Song(
            source_id="fixture-1",
            title="Fixture Song",
            tracks=(
                SongTrack(
                    id="part-1",
                    name="Lead Guitar",
                    classification=TrackClassification(
                        TrackRole.GUITAR,
                        ClassificationSource.INSTRUMENT,
                    ),
                    instrument_name="Electric Guitar",
                    midi_program=29,
                    is_percussion=False,
                    notes=(
                        NoteEvent(position=0.0, duration=1.0, midi_note=64, velocity=88),
                        NoteEvent(position=1.0, duration=0.5, midi_note=67),
                    ),
                ),
            ),
            tempo_map=(TempoPoint(position=0.0, bpm=120.0),),
            meter_map=(MeterPoint(position=0.0, numerator=4, denominator=4),),
        )
        document = song_to_dict(song)
        self.assertEqual(song, song_from_dict(document))
        self.assertEqual(document, song_to_dict(song_from_dict(document)))


if __name__ == "__main__":
    unittest.main()
