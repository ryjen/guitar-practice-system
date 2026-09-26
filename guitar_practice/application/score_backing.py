"""Application orchestration for score-derived backing MIDI artifacts."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import BinaryArtifactStore, JsonDocumentStore
from guitar_practice.domain import score
from guitar_practice.domain.score_midi import render_score_midi
from guitar_practice.domain.score_realization import (
    resolve_section,
    scale_tempo,
    select_backing_parts,
    slice_bars,
)


@dataclass(frozen=True)
class RenderScoreBacking:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore

    def execute(
        self,
        score_path: str,
        output_path: str,
        *,
        tempo_factor: float,
        include_part_ids: tuple[str, ...] = (),
        exclude_part_ids: tuple[str, ...] = (),
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
        focused = (
            slice_bars(source, *selected_range)
            if selected_range is not None
            else copy.deepcopy(source)
        )
        realized = scale_tempo(focused, tempo_factor)
        selected = select_backing_parts(
            realized,
            include_part_ids=include_part_ids,
            exclude_part_ids=exclude_part_ids,
        )
        if not selected["parts"]:
            raise ValueError("no backing parts selected")

        midi_bytes = render_score_midi(selected)
        self.artifacts.write_bytes(output_path, midi_bytes)

        selected_ids = [part["id"] for part in selected["parts"]]
        selected_set = set(selected_ids)
        metadata: dict[str, Any] = {
            "schema_version": 1,
            "score": score_path,
            "source_score_id": source["id"],
            "realization_id": selected["id"],
            "artifact": output_path,
            "tempo_factor": float(tempo_factor),
            "bar_range": list(selected_range) if selected_range is not None else None,
            "section": section["label"] if section is not None else None,
            "selected_part_ids": selected_ids,
            "excluded_part_ids": [
                part["id"] for part in realized["parts"] if part["id"] not in selected_set
            ],
            "explicit_include_part_ids": list(include_part_ids),
            "explicit_exclude_part_ids": list(exclude_part_ids),
        }
        self.documents.write(f"{output_path}.json", metadata)
        return metadata
