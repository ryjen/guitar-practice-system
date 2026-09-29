"""Application orchestration for Score IR MIDI artifacts and playback."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from guitar_practice.application.ports import (
    BinaryArtifactStore,
    JsonDocumentStore,
    MidiPlayer,
)
from guitar_practice.domain import score
from guitar_practice.domain.score_midi import render_score_midi
from guitar_practice.domain.score_realization import resolve_section, slice_bars


_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")


def _token(value: str) -> str:
    normalized = _SAFE_TOKEN.sub("-", value.strip()).strip("._-")
    return normalized[:64] or "section"


def _realize(
    document: Mapping[str, Any],
    *,
    bar_range: tuple[int, int] | None,
    section_name: str | None,
) -> tuple[dict[str, Any], tuple[int, int] | None, str | None]:
    if bar_range is not None and section_name is not None:
        raise ValueError("choose either a bar range or a section, not both")
    if section_name is not None:
        section = resolve_section(document, section_name)
        selected = (int(section["start_bar"]), int(section["end_bar"]))
        return slice_bars(document, *selected), selected, str(section["label"])
    if bar_range is not None:
        return slice_bars(document, *bar_range), bar_range, None
    return copy.deepcopy(dict(document)), None, None


def _default_playback_path(
    score_id: str,
    *,
    selected_range: tuple[int, int] | None,
    section: str | None,
) -> str:
    stem = score_id
    if section is not None:
        stem = f"{stem}-section-{_token(section)}"
    elif selected_range is not None:
        stem = f"{stem}-bars{selected_range[0]}-{selected_range[1]}"
    return str(PurePosixPath("generated/playback") / f"{stem}.mid")


@dataclass(frozen=True)
class RenderScoreMidi:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    metadata: JsonDocumentStore

    def execute(
        self,
        source: str,
        output: str,
        *,
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> Mapping[str, Any]:
        document = dict(self.documents.read(source))
        score.validate(document)
        realized, selected_range, section = _realize(
            document,
            bar_range=bar_range,
            section_name=section_name,
        )
        midi = render_score_midi(realized)
        self.artifacts.write_bytes(output, midi)

        payload: dict[str, Any] = {
            "schema_version": 1,
            "format": "midi",
            "score": source,
            "source_score_id": document["id"],
            "source_score_schema": document["schema"],
            "source_score_version": document["version"],
            "realization_id": realized["id"],
            "artifact": output,
            "bar_range": list(selected_range) if selected_range is not None else None,
            "section": section,
            "render_path": "score-ir-midi-v1",
            "parts": [part["id"] for part in realized["parts"]],
        }
        if "provenance" in realized:
            payload["realization_provenance"] = copy.deepcopy(realized["provenance"])
        self.metadata.write(f"{output}.json", payload)
        return payload


@dataclass(frozen=True)
class PlayScoreMidi:
    renderer: RenderScoreMidi
    artifacts: BinaryArtifactStore
    metadata: JsonDocumentStore
    player: MidiPlayer

    def execute(
        self,
        source: str,
        output: str | None = None,
        *,
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> Mapping[str, Any]:
        document = dict(self.renderer.documents.read(source))
        score.validate(document)
        _, selected_range, section = _realize(
            document,
            bar_range=bar_range,
            section_name=section_name,
        )
        resolved_output = output or _default_playback_path(
            str(document["id"]),
            selected_range=selected_range,
            section=section,
        )

        payload = dict(
            self.renderer.execute(
                source,
                resolved_output,
                bar_range=bar_range,
                section_name=section_name,
            )
        )
        played = self.player.play(self.artifacts.read_bytes(resolved_output))
        payload["playback"] = {
            "player": played.player,
            "player_version": played.player_version,
            "soundfont": played.soundfont,
        }
        self.metadata.write(f"{resolved_output}.json", payload)
        return payload
