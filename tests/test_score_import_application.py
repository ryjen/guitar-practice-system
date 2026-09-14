from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Mapping

from guitar_practice.application.ports import ConvertedScore
from guitar_practice.application.score_import import ImportScore, UnsupportedScoreFormat

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"


class MemoryDocuments:
    def __init__(self) -> None:
        self.writes: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.writes[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.writes[path] = document


class FakeConverter:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def convert(self, source_path: str) -> ConvertedScore:
        self.seen.append(source_path)
        return ConvertedScore(
            musicxml=FIXTURE.read_bytes(),
            converter="fake-converter",
            converter_version="1.2.3",
        )


class ScoreImportApplicationTests(unittest.TestCase):
    def test_imports_supported_source_and_writes_provenance_wrapper(self) -> None:
        documents = MemoryDocuments()
        converter = FakeConverter()
        service = ImportScore(converter=converter, documents=documents)

        song = service.execute("incoming/My Song.gp5", "songs/my-song.json")

        self.assertEqual(["incoming/My Song.gp5"], converter.seen)
        self.assertEqual("My-Song", song.source_id)
        self.assertEqual("Fixture Song", song.title)
        written = documents.writes["songs/my-song.json"]
        self.assertEqual("fake-converter", written["import"]["converter"])
        self.assertEqual("1.2.3", written["import"]["converter_version"])
        self.assertEqual("incoming/My Song.gp5", written["import"]["source"])
        self.assertEqual("Fixture Song", written["song"]["title"])

    def test_accepts_supported_guitar_pro_and_musicxml_extensions(self) -> None:
        supported = ("x.gp", "x.gp3", "x.gp4", "x.gp5", "x.gpx", "x.musicxml", "x.xml")
        for source in supported:
            with self.subTest(source=source):
                documents = MemoryDocuments()
                converter = FakeConverter()
                ImportScore(converter=converter, documents=documents).execute(source, "out.json")
                self.assertEqual([source], converter.seen)

    def test_rejects_unsupported_extension_before_converter_runs(self) -> None:
        documents = MemoryDocuments()
        converter = FakeConverter()
        service = ImportScore(converter=converter, documents=documents)

        with self.assertRaises(UnsupportedScoreFormat):
            service.execute("song.pdf", "songs/song.json")

        self.assertEqual([], converter.seen)
        self.assertEqual({}, documents.writes)

    def test_source_id_is_filename_based_and_path_safe(self) -> None:
        documents = MemoryDocuments()
        converter = FakeConverter()
        song = ImportScore(converter=converter, documents=documents).execute(
            "incoming/../../Odd Song (Live).gp",
            "song.json",
        )
        self.assertEqual("Odd-Song-Live", song.source_id)
        self.assertNotIn("/", song.source_id)
        self.assertNotIn("..", song.source_id)


if __name__ == "__main__":
    unittest.main()
