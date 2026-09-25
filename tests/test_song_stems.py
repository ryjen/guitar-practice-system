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
)
from guitar_practice.domain.song_stems import (
    scale_tempo,
    select_backing_tracks,
    slice_bars,
    select_drum_tracks,
)


def _track(track_id: str, role: TrackRole, source: ClassificationSource) -> SongTrack:
    return SongTrack(
        id=track_id,
        name=track_id,
        classification=TrackClassification(role, source),
    )


class SongStemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guitar = _track("guitar", TrackRole.GUITAR, ClassificationSource.INSTRUMENT)
        self.bass = _track("bass", TrackRole.BASS, ClassificationSource.MIDI)
        self.drums = _track("drums", TrackRole.DRUMS, ClassificationSource.PERCUSSION)
        self.unknown = _track("mystery", TrackRole.UNKNOWN, ClassificationSource.UNKNOWN)
        self.song = Song(
            source_id="fixture",
            title="Fixture",
            tracks=(self.guitar, self.bass, self.drums, self.unknown),
            tempo_map=(
                TempoPoint(position=0.0, bpm=120.0),
                TempoPoint(position=8.0, bpm=90.0),
            ),
        )

    def test_scale_tempo_scales_entire_map_without_mutating_source(self) -> None:
        realized = scale_tempo(self.song, 0.75)

        self.assertEqual([90.0, 67.5], [point.bpm for point in realized.tempo_map])
        self.assertEqual([120.0, 90.0], [point.bpm for point in self.song.tempo_map])
        self.assertEqual(self.song.tracks, realized.tracks)

    def test_scale_tempo_rejects_non_positive_or_non_finite_factor(self) -> None:
        for factor in (0.0, -0.5, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                scale_tempo(self.song, factor)

    def test_slice_bars_remaps_structure_maps_and_overlapping_notes(self) -> None:
        track = SongTrack(
            id="drums",
            name="Drums",
            classification=TrackClassification(TrackRole.DRUMS, ClassificationSource.PERCUSSION),
            notes=(
                NoteEvent(position=0.5, duration=1.0, midi_note=36),
                NoteEvent(position=2.0, duration=2.0, midi_note=38),
                NoteEvent(position=7.0, duration=2.0, midi_note=42),
            ),
        )
        song = Song(
            source_id="slice",
            title="Slice",
            tracks=(track,),
            tempo_map=(TempoPoint(0.0, 120.0), TempoPoint(5.0, 90.0)),
            meter_map=(MeterPoint(0.0, 4, 4), MeterPoint(1.0, 3, 4)),
            duration_quarters=8.0,
            bar_boundaries=(0.0, 1.0, 5.0, 8.0),
        )

        sliced = slice_bars(song, 2, 3)

        self.assertEqual(7.0, sliced.duration_quarters)
        self.assertEqual((0.0, 4.0, 7.0), sliced.bar_boundaries)
        self.assertEqual([(0.0, 120.0), (4.0, 90.0)], [(p.position, p.bpm) for p in sliced.tempo_map])
        self.assertEqual([(0.0, 3, 4)], [(p.position, p.numerator, p.denominator) for p in sliced.meter_map])
        self.assertEqual(
            [(0.0, 0.5, 36), (1.0, 2.0, 38), (6.0, 1.0, 42)],
            [(n.position, n.duration, n.midi_note) for n in sliced.tracks[0].notes],
        )

    def test_slice_bars_rejects_missing_boundaries_and_invalid_ranges(self) -> None:
        with self.assertRaises(ValueError):
            slice_bars(self.song, 1, 1)
        bounded = Song(
            source_id="bounded",
            title="Bounded",
            duration_quarters=8.0,
            bar_boundaries=(0.0, 4.0, 8.0),
        )
        for start, end in ((0, 1), (2, 1), (1, 3)):
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    slice_bars(bounded, start, end)

    def test_backing_excludes_guitar_but_keeps_unknown_by_default(self) -> None:
        selected = select_backing_tracks(self.song)
        self.assertEqual(
            ["bass", "drums", "mystery"],
            [track.id for track in selected],
        )

    def test_backing_keeps_heuristic_guitar_by_default(self) -> None:
        heuristic = _track(
            "maybe-guitar",
            TrackRole.GUITAR,
            ClassificationSource.NAME_HEURISTIC,
        )
        song = Song(source_id="heuristic", title="Heuristic", tracks=(heuristic, self.bass))
        selected = select_backing_tracks(song)
        self.assertEqual(["maybe-guitar", "bass"], [track.id for track in selected])

    def test_explicit_include_and_exclude_override_default_selection(self) -> None:
        selected = select_backing_tracks(
            self.song,
            include_track_ids=("guitar",),
            exclude_track_ids=("bass",),
        )
        self.assertEqual(
            ["guitar", "drums", "mystery"],
            [track.id for track in selected],
        )

    def test_drum_selection_is_drums_only_by_default(self) -> None:
        selected = select_drum_tracks(self.song)
        self.assertEqual(["drums"], [track.id for track in selected])

    def test_drum_selection_can_explicitly_include_ambiguous_track(self) -> None:
        selected = select_drum_tracks(self.song, include_track_ids=("mystery",))
        self.assertEqual(["drums", "mystery"], [track.id for track in selected])

    def test_explicit_track_ids_must_exist_and_not_conflict(self) -> None:
        with self.assertRaises(ValueError):
            select_backing_tracks(self.song, include_track_ids=("missing",))
        with self.assertRaises(ValueError):
            select_drum_tracks(self.song, exclude_track_ids=("missing",))
        with self.assertRaises(ValueError):
            select_backing_tracks(
                self.song,
                include_track_ids=("guitar",),
                exclude_track_ids=("guitar",),
            )


if __name__ == "__main__":
    unittest.main()
