from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Mapping

from guitar_practice.adapters.musicxml_import import MusicXmlParser
from guitar_practice.application.ports import ConvertedScore
from guitar_practice.application.score_import import (
    ImportScore,
    imported_to_score_ir,
    source_id_for,
)
from guitar_practice.application.imported_score import (
    ClassificationSource,
    ImportedMeterPoint,
    ImportedNoteEvent,
    ImportedScore,
    ImportedTrack,
    TrackClassification,
    TrackRole,
)
from guitar_practice.domain import score

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = document


class FakeConverter:
    def __init__(self, musicxml: bytes) -> None:
        self.musicxml = musicxml

    def convert(self, source_path: str) -> ConvertedScore:
        return ConvertedScore(
            musicxml=self.musicxml,
            converter="test-converter",
            converter_version="1.0",
        )


class ScoreImportApplicationTests(unittest.TestCase):
    def test_import_persists_only_canonical_score_ir(self) -> None:
        store = MemoryStore()
        document = ImportScore(
            converter=FakeConverter(FIXTURE.read_bytes()),
            parser=MusicXmlParser(),
            documents=store,
        ).execute("Fixture Song.musicxml", "generated/fixture.score.json")

        self.assertEqual(score.SCHEMA_ID, document["schema"])
        self.assertEqual(score.SCHEMA_VERSION, document["version"])
        self.assertEqual("fixture-song", document["id"])
        self.assertEqual("Fixture Song", document["metadata"]["title"])
        self.assertNotIn("song", document)
        self.assertNotIn("schema_version", document)
        self.assertEqual(document, store.values["generated/fixture.score.json"])
        score.validate(dict(document))

    def test_import_maps_tracks_tempo_meter_and_notes_to_score_ir(self) -> None:
        document = ImportScore(
            converter=FakeConverter(FIXTURE.read_bytes()),
            parser=MusicXmlParser(),
            documents=MemoryStore(),
        ).execute("fixture.musicxml", "fixture.score.json")

        self.assertEqual([1, 2], [bar["number"] for bar in document["bars"]])
        self.assertEqual(
            [(1, 4, 4)],
            [(item["bar"], item["beats"], item["beat_unit"]) for item in document["meter_map"]],
        )
        self.assertEqual(
            [
                ({"bar": 1, "beat": [1, 1]}, 120.0),
                ({"bar": 2, "beat": [1, 1]}, 90.0),
            ],
            [(item["location"], item["bpm"]) for item in document["tempo_map"]],
        )
        self.assertEqual(
            ["guitar", "bass", "drums", "keys"],
            [part["role"] for part in document["parts"]],
        )
        guitar = document["parts"][0]
        self.assertEqual("p1", guitar["id"])
        self.assertEqual(
            {"program": 29, "channel": 1},
            guitar["instrument"]["midi"],
        )
        drums = document["parts"][2]
        self.assertEqual(
            {"channel": 10, "percussion": True},
            drums["instrument"]["midi"],
        )
        self.assertEqual(
            [
                ({"bar": 1, "beat": [1, 1]}, [1, 1], {"step": "E", "alter": 0, "octave": 4}),
                ({"bar": 2, "beat": [1, 1]}, [1, 1], {"step": "G", "alter": 0, "octave": 4}),
            ],
            [
                (event["location"], event["duration"], event["pitch"])
                for event in guitar["events"]
            ],
        )

    def test_cross_bar_notes_are_split_with_tie_semantics(self) -> None:
        imported = ImportedScore(
            source_id="fixture",
            title="Cross Bar",
            tracks=(
                ImportedTrack(
                    id="P1",
                    name="Guitar",
                    classification=TrackClassification(
                        TrackRole.GUITAR,
                        ClassificationSource.INSTRUMENT,
                    ),
                    instrument_name="Electric Guitar",
                    notes=(
                        ImportedNoteEvent(
                            position=3.0,
                            duration=2.0,
                            midi_note=64,
                        ),
                    ),
                ),
            ),
            meter_map=(ImportedMeterPoint(position=0.0, numerator=4, denominator=4),),
            duration_quarters=8.0,
            bar_boundaries=(0.0, 4.0, 8.0),
        )

        document = imported_to_score_ir(
            imported,
            source_path="cross-bar.musicxml",
            converter="test",
        )

        events = document["parts"][0]["events"]
        self.assertEqual(2, len(events))
        self.assertEqual("start", events[0]["tie"])
        self.assertEqual("stop", events[1]["tie"])
        self.assertEqual({"bar": 1, "beat": [4, 1]}, events[0]["location"])
        self.assertEqual({"bar": 2, "beat": [1, 1]}, events[1]["location"])
        self.assertEqual([1, 4], events[0]["duration"])
        self.assertEqual([1, 4], events[1]["duration"])
        score.validate(document)

    def test_source_id_is_a_score_ir_slug(self) -> None:
        self.assertEqual("my-weird-song-2", source_id_for("Some Folder/My Weird_Song #2.GP5"))


if __name__ == "__main__":
    unittest.main()
