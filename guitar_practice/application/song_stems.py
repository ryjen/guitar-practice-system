"""Application orchestration for imported-song symbolic practice stems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import BinaryArtifactStore, JsonDocumentStore
from guitar_practice.domain.song import song_from_dict
from guitar_practice.domain.song_midi import render_song_midi
from guitar_practice.domain.song_stems import scale_tempo, select_backing_tracks


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
    ) -> Mapping[str, Any]:
        document = self.documents.read(score_path)
        raw_song = document.get("song")
        if not isinstance(raw_song, Mapping):
            raise ValueError("score document must contain a song object")

        song = song_from_dict(raw_song)
        realized = scale_tempo(song, tempo_factor)
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
            "selected_track_ids": selected_ids,
            "excluded_track_ids": excluded_ids,
            "explicit_include_track_ids": list(include_track_ids),
            "explicit_exclude_track_ids": list(exclude_track_ids),
        }
        self.documents.write(f"{output_path}.json", metadata)
        return metadata
