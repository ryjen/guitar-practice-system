"""Application orchestration for deterministic score MIDI realization and playback."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import (
    BinaryArtifactStore,
    JsonDocumentStore,
    MidiPlayer,
    PlaybackResult,
)
from guitar_practice.domain import score
from guitar_practice.domain.score_midi import render_score_midi
from guitar_practice.domain.score_realization import (
    resolve_section,
    scale_tempo,
    slice_bars,
)

_RENDER_PATH = "score-midi-v1"


def _source_hash(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(score.dumps(document).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RenderScoreMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore

    def execute(
        self,
        score_path: str,
        output_path: str,
        *,
        tempo_factor: float = 1.0,
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> Mapping[str, Any]:
        source = dict(self.documents.read(score_path))
        score.validate(source)
        if bar_range is not None and section_name is not None:
            raise ValueError("choose either a bar range or a section, not both")

        section = resolve_section(source, section_name) if section_name is not None else None
        selected_range = (
            (int(section["start_bar"]), int(section["end_bar"]))
            if section is not None
            else bar_range
        )
        realized = (
            slice_bars(source, *selected_range)
            if selected_range is not None
            else copy.deepcopy(source)
        )
        if float(tempo_factor) != 1.0:
            realized = scale_tempo(realized, tempo_factor)
        elif not isinstance(tempo_factor, (int, float)) or isinstance(tempo_factor, bool):
            raise ValueError("tempo factor must be numeric")

        midi_bytes = render_score_midi(realized)
        self.artifacts.write_bytes(output_path, midi_bytes)

        metadata: dict[str, Any] = {
            "schema_version": 1,
            "render_path": _RENDER_PATH,
            "score": score_path,
            "source_score_id": source["id"],
            "source_score_schema_version": source["version"],
            "source_score_sha256": _source_hash(source),
            "realization_id": realized["id"],
            "artifact": output_path,
            "tempo_factor": float(tempo_factor),
            "bar_range": list(selected_range) if selected_range is not None else None,
            "section": section["label"] if section is not None else None,
            "selected_part_ids": [part["id"] for part in realized["parts"]],
        }
        self.documents.write(f"{output_path}.json", metadata)
        return metadata


@dataclass(frozen=True)
class PlayScoreMidi:
    renderer: RenderScoreMidi
    artifacts: BinaryArtifactStore
    player: MidiPlayer

    def execute(
        self,
        score_path: str,
        output_path: str,
        *,
        tempo_factor: float = 1.0,
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> tuple[Mapping[str, Any], PlaybackResult]:
        metadata = self.renderer.execute(
            score_path,
            output_path,
            tempo_factor=tempo_factor,
            bar_range=bar_range,
            section_name=section_name,
        )
        playback = self.player.play(self.artifacts.read_bytes(output_path))
        return metadata, playback
