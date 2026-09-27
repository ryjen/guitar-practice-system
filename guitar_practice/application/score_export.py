"""Application orchestration for deterministic Score IR export."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_practice.application.ports import (
    BinaryArtifactStore,
    ExportedScore,
    JsonDocumentStore,
    ScoreExporter,
)
from guitar_practice.domain import score


@dataclass(frozen=True)
class ExportScore:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    exporter: ScoreExporter

    def render(self, source: str) -> ExportedScore:
        document = dict(self.documents.read(source))
        score.validate(document)
        return self.exporter.export(document)

    def render_to(self, source: str, output: str) -> ExportedScore:
        result = self.render(source)
        self.artifacts.write_bytes(output, result.data)
        return result
