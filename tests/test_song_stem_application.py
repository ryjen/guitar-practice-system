from __future__ import annotations

import copy
import unittest
from typing import Any, Mapping

from guitar_practice.application.song_stems import RenderBackingStem
from guitar_practice.domain import midi
from guitar_practice.domain.song import (
    ClassificationSource,
    NoteEvent,
    Song,
    SongTrack,
    TempoPoint,
    TrackClassification,
    TrackRole,
    song_to_dict,
)


class MemoryDocuments:
    def __init__(self, values: Mapping[str, Mapping[str, Any]]) -> None:
        self.values = dict(values)
        self.writes: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.writes[path] = document


class MemoryArtifacts:
    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.writes[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.writes[path] = data


def _track(track_id: str, role: TrackRole, note: int, channel: int) -> SongTrack:
    source = ClassificationSource.PERCUSSION if role is TrackRole.DRUMS else ClassificationSource.MIDI
    return SongTrack(
        id=track_id,
        name=track_id.title(),
        classification=TrackClassification(role, source),
        midi_channel=channel,
        is_percussion=role is TrackRole.DRUMS,
        notes=(NoteEvent(position=0.0, duration=1.0, midi_note=note),),
    )


class SongStemApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.song = Song(
            source_id="fixture",
            title="Fixture",
            tracks=(
                _track("guitar", TrackRole.GUITAR, 64, 1),
                _track("bass", TrackRole.BASS, 40, 2),
                _track("drums", TrackRole.DRUMS, 36, 10),
                _track("mystery", TrackRole.UNKNOWN, 72, 3),
            ),
            tempo_map=(
                TempoPoint(position=0.0, bpm=120.0),
                TempoPoint(position=4.0, bpm=90.0),
            ),
        )
        self.wrapper = {
            "schema_version": 1,
            "song": song_to_dict(self.song),
            "import": {"source": "fixture.gp5", "converter": "fake", "converter_version": "1"},
        }

    def test_writes_backing_midi_and_sidecar_without_mutating_score(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": self.wrapper})
        artifacts = MemoryArtifacts()
        before = copy.deepcopy(self.wrapper)
        service = RenderBackingStem(documents=documents, artifacts=artifacts)
        metadata = service.execute(
            "songs/fixture.json",
            "practice/backing.mid",
            tempo_factor=0.75,
        )

        self.assertEqual(before, self.wrapper)
        self.assertIn("practice/backing.mid", artifacts.writes)
        report = midi.inspect(artifacts.writes["practice/backing.mid"])
        self.assertEqual(4, report["tracks"])
        self.assertEqual(
            ["bass", "drums", "mystery"],
            metadata["selected_track_ids"],
        )
        self.assertEqual(["guitar"], metadata["excluded_track_ids"])
        self.assertEqual(0.75, metadata["tempo_factor"])
        self.assertEqual("fixture", metadata["source_id"])
        self.assertEqual(metadata, documents.writes["practice/backing.mid.json"])

    def test_explicit_track_overrides_are_recorded(self) -> None:
        documents = MemoryDocuments({"song.json": self.wrapper})
        artifacts = MemoryArtifacts()
        service = RenderBackingStem(documents=documents, artifacts=artifacts)
        metadata = service.execute(
            "song.json",
            "out/backing.mid",
            tempo_factor=1.0,
            include_track_ids=("guitar",),
            exclude_track_ids=("mystery",),
        )

        self.assertEqual(
            ["guitar", "bass", "drums"],
            metadata["selected_track_ids"],
        )
        self.assertEqual(["mystery"], metadata["explicit_exclude_track_ids"])
        self.assertEqual(["guitar"], metadata["explicit_include_track_ids"])
        self.assertEqual(
            ["Guitar", "Bass", "Drums"],
            midi.inspect(artifacts.writes["out/backing.mid"])["track_names"][1:],
        )


if __name__ == "__main__":
    unittest.main()
