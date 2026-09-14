"""Application orchestration for symbolic MIDI to WAV rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import (
    AudioRenderer,
    AudioRenderProfile,
    BinaryArtifactStore,
    JsonDocumentStore,
)


@dataclass(frozen=True)
class RenderAudioArtifact:
    artifacts: BinaryArtifactStore
    documents: JsonDocumentStore
    renderer: AudioRenderer

    def execute(
        self,
        midi_path: str,
        output_path: str,
        *,
        profile: AudioRenderProfile,
    ) -> Mapping[str, Any]:
        midi = self.artifacts.read_bytes(midi_path)
        rendered = self.renderer.render(midi, profile)

        metadata: dict[str, Any] = {
            "schema_version": 1,
            "source_midi": midi_path,
            "artifact": output_path,
            "renderer": rendered.renderer,
            "renderer_version": rendered.renderer_version,
            "soundfont": rendered.soundfont,
            "profile": {
                "sample_rate": profile.sample_rate,
                "channels": profile.channels,
                "sample_format": profile.sample_format,
            },
        }
        self.artifacts.write_bytes(output_path, rendered.wav)
        self.documents.write(f"{output_path}.json", metadata)
        return metadata
