from __future__ import annotations

import unittest
from typing import Any, Mapping

from guitar_practice.application.ports import ExportedScore, ScoreExportDiagnostic
from guitar_practice.application.score_export import ExportScore
from tests.test_score_ir import timeline_score


class MemoryDocuments:
    def __init__(self, values: dict[str, dict[str, Any]]) -> None:
        self.values = values

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = dict(document)


class MemoryArtifacts:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.values[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.values[path] = data


class FakeExporter:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    def export(self, document: Mapping[str, Any]) -> ExportedScore:
        self.documents.append(dict(document))
        return ExportedScore(
            data=b"<score-partwise/>\n",
            diagnostics=(
                ScoreExportDiagnostic(
                    severity="warning",
                    code="generic-technique",
                    path="parts[guitar-1]",
                    message="generic technique",
                ),
            ),
        )


class ScoreExportApplicationTests(unittest.TestCase):
    def test_render_returns_exported_bytes_and_diagnostics_without_writing(self) -> None:
        source = timeline_score()
        documents = MemoryDocuments({"source.score.json": source})
        artifacts = MemoryArtifacts()
        exporter = FakeExporter()
        service = ExportScore(documents, artifacts, exporter)

        result = service.render("source.score.json")

        self.assertEqual(b"<score-partwise/>\n", result.data)
        self.assertEqual("generic-technique", result.diagnostics[0].code)
        self.assertEqual({}, artifacts.values)
        self.assertEqual(source, exporter.documents[0])

    def test_render_to_writes_only_explicit_output(self) -> None:
        source = timeline_score()
        documents = MemoryDocuments({"source.score.json": source})
        artifacts = MemoryArtifacts()
        exporter = FakeExporter()
        service = ExportScore(documents, artifacts, exporter)

        result = service.render_to("source.score.json", "generated/source.musicxml")

        self.assertEqual(result.data, artifacts.values["generated/source.musicxml"])
        self.assertEqual({"source.score.json": source}, documents.values)


if __name__ == "__main__":
    unittest.main()
