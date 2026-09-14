from __future__ import annotations

import unittest

from guitar_practice.domain.song import (
    ClassificationSource,
    Song,
    SongTrack,
    TempoPoint,
    TrackClassification,
    TrackRole,
)
from guitar_practice.domain.song_stems import (
    scale_tempo,
    select_backing_tracks,
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

    def test_backing_excludes_guitar_but_keeps_unknown_by_default(self) -> None:
        selected = select_backing_tracks(self.song)
        self.assertEqual(
            ["bass", "drums", "mystery"],
            [track.id for track in selected],
        )

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
