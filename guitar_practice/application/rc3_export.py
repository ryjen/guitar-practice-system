"""Application orchestration for BOSS RC-3 drum-loop exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from guitar_practice.application.ports import (
    AudioRenderer,
    AudioRenderProfile,
    BinaryArtifactStore,
    JsonDocumentStore,
)
from guitar_practice.domain.audio_profiles import (
    boss_rc3_filename,
    normalize_boss_rc3_wav,
    song_duration_seconds,
)
from guitar_practice.domain.song import song_from_dict
from guitar_practice.domain.song_midi import render_song_midi
from guitar_practice.domain.song_stems import scale_tempo, select_drum_tracks, slice_bars


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
        include_track_ids: tuple[str, ...] = (),
        exclude_track_ids: tuple[str, ...] = (),
        bar_range: tuple[int, int] | None = None,
    ) -> Mapping[str, Any]:
        document = self.documents.read(score_path)
        raw_song = document.get("song")
        if not isinstance(raw_song, Mapping):
            raise ValueError("score document must contain a song object")

        song = song_from_dict(raw_song)
        focused = slice_bars(song, *bar_range) if bar_range is not None else song
        realized = scale_tempo(focused, tempo_factor)
        selected = select_drum_tracks(
            realized,
            include_track_ids=include_track_ids,
            exclude_track_ids=exclude_track_ids,
        )
        if not selected:
            raise ValueError("no drum tracks selected for RC-3 export")

        if output_path is None:
            filename = PurePosixPath(
                boss_rc3_filename(song.source_id, tempo_factor=tempo_factor)
            )
            if bar_range is not None:
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
        midi_bytes = render_song_midi(realized, selected)
        self.artifacts.write_bytes(midi_output, midi_bytes)

        profile = AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16")
        rendered = self.renderer.render(midi_bytes, profile)
        duration_seconds = song_duration_seconds(realized)
        wav = normalize_boss_rc3_wav(
            rendered.wav,
            duration_seconds=duration_seconds,
        )
        self.artifacts.write_bytes(resolved_output, wav)

        metadata: dict[str, Any] = {
            "schema_version": 1,
            "target": "boss-rc3",
            "score": score_path,
            "artifact": resolved_output,
            "source_midi": midi_output,
            "tempo_factor": float(tempo_factor),
            "duration_seconds": duration_seconds,
            "bar_range": list(bar_range) if bar_range is not None else None,
            "selected_track_ids": [track.id for track in selected],
            "explicit_include_track_ids": list(include_track_ids),
            "explicit_exclude_track_ids": list(exclude_track_ids),
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
