"""Application orchestration for Score IR-derived symbolic MIDI artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import BinaryArtifactStore
from guitar_practice.domain.score_midi import render_score_midi
from guitar_practice.domain.score_realization import (
    scale_tempo,
    select_backing_parts,
    select_drum_parts,
    slice_bars,
    slice_section,
)


@dataclass(frozen=True)
class RenderedScoreMidi:
    output_path: str
    realization_id: str
    part_ids: tuple[str, ...]
    byte_count: int


@dataclass(frozen=True)
class RenderScoreMidi:
    artifacts: BinaryArtifactStore

    def execute(
        self,
        document: Mapping[str, Any],
        output_path: str,
        *,
        kind: str,
        tempo_factor: float = 1.0,
        include_part_ids: tuple[str, ...] = (),
        exclude_part_ids: tuple[str, ...] = (),
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> RenderedScoreMidi:
        if bar_range is not None and section_name is not None:
            raise ValueError("choose either a bar range or section, not both")
        if kind not in {"backing", "drums"}:
            raise ValueError("render kind must be backing or drums")

        realized: Mapping[str, Any] = document
        if bar_range is not None:
            realized = slice_bars(realized, bar_range[0], bar_range[1])
        elif section_name is not None:
            realized = slice_section(realized, section_name)

        if tempo_factor != 1.0:
            realized = scale_tempo(realized, tempo_factor)

        if kind == "backing":
            realized = select_backing_parts(
                realized,
                include_part_ids=include_part_ids,
                exclude_part_ids=exclude_part_ids,
            )
        else:
            realized = select_drum_parts(
                realized,
                include_part_ids=include_part_ids,
                exclude_part_ids=exclude_part_ids,
            )

        parts = tuple(str(part["id"]) for part in realized["parts"])
        if not parts:
            raise ValueError(f"{kind} realization selected no parts")

        payload = render_score_midi(realized)
        self.artifacts.write_bytes(output_path, payload)
        return RenderedScoreMidi(
            output_path=output_path,
            realization_id=str(realized["id"]),
            part_ids=parts,
            byte_count=len(payload),
        )
