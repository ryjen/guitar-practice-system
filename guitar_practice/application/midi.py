"""Application use cases for deterministic MIDI artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.generation import DEFAULT_GROOVE_CATALOG
from guitar_practice.application.ports import BinaryArtifactStore, JsonDocumentStore
from guitar_practice.domain import backing, midi


def render_canonical(
    manifest: dict[str, Any],
    documents: JsonDocumentStore,
    groove_catalog_path: str,
) -> bytes:
    """Route authored backing data without weakening legacy MIDI behavior."""
    if backing.needs_backing_renderer(manifest):
        return backing.render(
            manifest, dict(documents.read(groove_catalog_path))
        )
    return midi.render(manifest)


@dataclass(frozen=True)
class GenerateMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    groove_catalog_path: str = DEFAULT_GROOVE_CATALOG

    def execute(self, manifest_path: str, output_path: str) -> dict[str, Any]:
        manifest = dict(self.documents.read(manifest_path))
        data = render_canonical(manifest, self.documents, self.groove_catalog_path)
        report = midi.validate_rendered(manifest, data)
        self.artifacts.write_bytes(output_path, data)
        return report


@dataclass(frozen=True)
class ValidateMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    groove_catalog_path: str = DEFAULT_GROOVE_CATALOG

    def execute(self, manifest_path: str, midi_path: str) -> dict[str, Any]:
        manifest = dict(self.documents.read(manifest_path))
        data = self.artifacts.read_bytes(midi_path)
        report = midi.validate_rendered(manifest, data)
        if backing.needs_backing_renderer(manifest):
            expected = render_canonical(
                manifest, self.documents, self.groove_catalog_path
            )
            if data != expected:
                raise midi.ManifestError(
                    "MIDI note content differs from canonical backing render; "
                    "regenerate with guitarctl midi generate or backing generate"
                )
        return report
