"""Application orchestration for imported-song symbolic practice stems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import BinaryArtifactStore, JsonDocumentStore
from guitar_practice.domain.song import song_from_dict
from guitar_practice.domain.song_midi import render_song_midi
from guitar_practice.domain.song_stems import (
    resolve_section,
    scale_tempo,
    select_backing_tracks,
    slice_bars,
)


@dataclass(frozen=True)
class RenderBackingStem:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore

    def execute(
        self,
        score_path: str,
        output_path: str,
        *,
        tempo_factor: float,
        include_track_ids: tuple[str, ...] = (),
        exclude_track_ids: tuple[str, ...] = (),
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> Mapping[str, Any]:
        document = self.documents.read(score_path)
        raw_song = document.get("song")
        if not isinstance(raw_song, Mapping):
            raise ValueError("score document must contain a song object")

        song = song_from_dict(raw_song)
        if bar_range is not None and section_name is not None:
            raise ValueError("choose either a bar range or a section, not both")
        section = resolve_section(song, section_name) if section_name is not None else None
        selected_range = (section.start_bar, section.end_bar) if section is not None else bar_range
        focused = slice_bars(song, *selected_range) if selected_range is not None else song
        realized = scale_tempo(focused, tempo_factor)
        selected = select_backing_tracks(
            realized,
            include_track_ids=include_track_ids,
            exclude_track_ids=exclude_track_ids,
        )
        selected_ids = [track.id for track in selected]
        selected_set = set(selected_ids)
        excluded_ids = [track.id for track in realized.tracks if track.id not in selected_set]

        self.artifacts.write_bytes(output_path, render_song_midi(realized, selected))
        metadata: dict[str, Any] = {
            "schema_version": 1,
            "source_id": song.source_id,
            "score": score_path,
            "artifact": output_path,
            "tempo_factor": float(tempo_factor),
            "bar_range": list(selected_range) if selected_range is not None else None,
            "section": section.name if section is not None else None,
            "selected_track_ids": selected_ids,
            "excluded_track_ids": excluded_ids,
            "explicit_include_track_ids": list(include_track_ids),
            "explicit_exclude_track_ids": list(exclude_track_ids),
        }
        self.documents.write(f"{output_path}.json", metadata)
        return metadata
