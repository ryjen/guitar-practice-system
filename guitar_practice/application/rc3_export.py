"""Application orchestration for BOSS RC-3 drum-loop exports."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from guitar_practice.application.ports import (
    AudioRenderer,
    AudioRenderProfile,
    BinaryArtifactStore,
    JsonDocumentStore,
)
from guitar_practice.domain import score
from guitar_practice.domain.audio_profiles import (
    boss_rc3_filename,
    normalize_boss_rc3_wav,
    score_duration_seconds,
)
from guitar_practice.domain.score_midi import render_score_midi
from guitar_practice.domain.score_realization import (
    resolve_section,
    scale_tempo,
    select_drum_parts,
    slice_bars,
)

_SAFE_FILENAME_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")


def _filename_token(value: str) -> str:
    token = _SAFE_FILENAME_TOKEN.sub("-", value.strip()).strip("._-")
    return token[:64] or "section"


@dataclass(frozen=True)
class ExportBossRc3Drums:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    renderer: AudioRenderer

    def execute(
        self,
        score_path: str,
        output_path: str | None,
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
        selected = select_drum_parts(
            realized,
            include_part_ids=include_part_ids,
            exclude_part_ids=exclude_part_ids,
        )
        if not selected["parts"]:
            raise ValueError("no drum parts selected for RC-3 export")

        if output_path is None:
            filename = PurePosixPath(
                boss_rc3_filename(str(source["id"]), tempo_factor=tempo_factor)
            )
            if section is not None:
                filename = filename.with_name(
                    f"{filename.stem}-section-{_filename_token(str(section['label']))}-bars{int(section['start_bar'])}-{int(section['end_bar'])}{filename.suffix}"
                )
            elif bar_range is not None:
                start_bar, end_bar = bar_range
                filename = filename.with_name(
                    f"{filename.stem}-bars{start_bar}-{end_bar}{filename.suffix}"
                )
            resolved_output = str(PurePosixPath("generated/rc3") / filename)
        else:
            resolved_output = output_path

        if PurePosixPath(resolved_output).suffix.casefold() != ".wav":
            raise ValueError("RC-3 output must use a .wav filename")

        midi_output = str(PurePosixPath(resolved_output).with_suffix(".mid"))
        midi_bytes = render_score_midi(selected)
        self.artifacts.write_bytes(midi_output, midi_bytes)

        profile = AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16")
        rendered = self.renderer.render(midi_bytes, profile)
        duration_seconds = score_duration_seconds(selected)
        wav = normalize_boss_rc3_wav(
            rendered.wav,
            duration_seconds=duration_seconds,
        )
        self.artifacts.write_bytes(resolved_output, wav)

        metadata: dict[str, Any] = {
            "schema_version": 1,
            "target": "boss-rc3",
            "score": score_path,
            "source_score_id": source["id"],
            "realization_id": selected["id"],
            "artifact": resolved_output,
            "source_midi": midi_output,
            "tempo_factor": float(tempo_factor),
            "duration_seconds": duration_seconds,
            "bar_range": list(selected_range) if selected_range is not None else None,
            "section": section["label"] if section is not None else None,
            "selected_part_ids": [part["id"] for part in selected["parts"]],
            "explicit_include_part_ids": list(include_part_ids),
            "explicit_exclude_part_ids": list(exclude_part_ids),
            "renderer": rendered.renderer,
            "renderer_version": rendered.renderer_version,
            "soundfont": rendered.soundfont,
            "profile": {
                "sample_rate": profile.sample_rate,
                "channels": profile.channels,
                "sample_format": profile.sample_format,
            },
        }
        self.documents.write(f"{resolved_output}.json", metadata)
        return metadata
