"""Native CLI handler for BOSS RC-3 drum exports."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from guitar_practice.adapters.audio_rendering import AudioRenderError, FluidSynthAudioRenderer
from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.rc3_export import ExportBossRc3Drums
from guitar_practice.domain.audio_profiles import BossRc3ProfileError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    tempo_factor,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _soundfont_path(value: str | None, workspace: Path) -> Path:
    selected = value or os.environ.get("GUITAR_SOUNDFONT")
    if not selected:
        raise AudioRenderError("SoundFont is required; use --soundfont or GUITAR_SOUNDFONT")
    path = Path(selected)
    return path if path.is_absolute() else workspace / path


def drums_export(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl drums export")
    parser.add_argument("score", help="Canonical imported-score JSON inside the workspace")
    parser.add_argument("--tempo", required=True, help="Practice tempo percentage, for example 75%")
    parser.add_argument("--target", choices=("boss-rc3",), required=True)
    parser.add_argument("--output", help="Optional workspace-relative WAV output path")
    parser.add_argument("--soundfont", help="SoundFont path; defaults to GUITAR_SOUNDFONT")
    parser.add_argument("--include-track", action="append", default=[])
    parser.add_argument("--exclude-track", action="append", default=[])
    args = parser.parse_args(list(argv))

    try:
        score = workspace_relative(args.score, label="score document")
        output = (
            workspace_relative(args.output, label="drum output")
            if args.output is not None
            else None
        )
        factor = tempo_factor(args.tempo)
        renderer = FluidSynthAudioRenderer(
            context.workspace,
            soundfont=_soundfont_path(args.soundfont, context.workspace),
        )
        ExportBossRc3Drums(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
            renderer=renderer,
        ).execute(
            score,
            output,
            tempo_factor=factor,
            include_track_ids=tuple(args.include_track),
            exclude_track_ids=tuple(args.exclude_track),
        )
    except AudioRenderError as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.UNAVAILABLE
    except (
        BossRc3ProfileError,
        PracticePathError,
        JsonDocumentError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    return exit_codes.OK


RC3_HANDLERS: dict[str, NativeHandler] = {"drums-export": drums_export}
