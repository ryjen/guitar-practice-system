"""CLI handlers for imported-song symbolic practice stems."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.song_stems import RenderBackingStem
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    bar_range,
    tempo_factor,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def backing_render(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing render")
    parser.add_argument("score", help="Canonical imported-score JSON inside the workspace")
    parser.add_argument("--tempo", required=True, help="Practice tempo percentage, for example 75%")
    parser.add_argument("--output", required=True, help="Workspace-relative MIDI output path")
    parser.add_argument("--bars", help="1-based inclusive structural bar range, for example 42:58")
    parser.add_argument("--include-track", action="append", default=[])
    parser.add_argument("--exclude-track", action="append", default=[])
    args = parser.parse_args(list(argv))

    try:
        score = workspace_relative(args.score, label="score document")
        output = workspace_relative(args.output, label="backing output")
        factor = tempo_factor(args.tempo)
        selected_bars = bar_range(args.bars) if args.bars is not None else None
        RenderBackingStem(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
        ).execute(
            score,
            output,
            tempo_factor=factor,
            include_track_ids=tuple(args.include_track),
            exclude_track_ids=tuple(args.exclude_track),
            bar_range=selected_bars,
        )
    except (PracticePathError, JsonDocumentError, OSError, ValueError, KeyError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    return exit_codes.OK


STEM_HANDLERS: dict[str, NativeHandler] = {
    "backing-render": backing_render,
}
