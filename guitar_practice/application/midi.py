"""Application use cases for deterministic MIDI artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import BinaryArtifactStore, JsonDocumentStore
from guitar_practice.domain import midi


@dataclass(frozen=True)
class GenerateMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore

    def execute(self, manifest_path: str, output_path: str) -> dict[str, Any]:
        manifest = dict(self.documents.read(manifest_path))
        data = midi.render(manifest)
        report = midi.validate_rendered(manifest, data)
        self.artifacts.write_bytes(output_path, data)
        return report


@dataclass(frozen=True)
class ValidateMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore

    def execute(self, manifest_path: str, midi_path: str) -> dict[str, Any]:
        manifest = dict(self.documents.read(manifest_path))
        data = self.artifacts.read_bytes(midi_path)
        return midi.validate_rendered(manifest, data)
