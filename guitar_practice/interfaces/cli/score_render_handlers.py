"""CLI handlers for Score IR-derived symbolic MIDI practice artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.binary_files import BinaryArtifactError, BinaryFileStore
from guitar_practice.adapters.score_files import ScoreDocumentError, ScoreFileStore
from guitar_practice.application.score_rendering import RenderScoreMidi
from guitar_practice.domain.score_midi import ScoreMidiError
from guitar_practice.domain.score_realization import ScoreRealizationError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    bar_range,
    tempo_factor,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _render(argv: Sequence[str], context: CliContext, *, kind: str) -> int:
    parser = argparse.ArgumentParser(prog=f"guitarctl {kind} render")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument(
        "--tempo",
        default="100%",
        help="Practice tempo percentage, for example 75% (default: 100%)",
    )
    parser.add_argument("--output", required=True, help="Workspace-relative MIDI output path")
    parser.add_argument(
        "--bars",
        help="1-based inclusive structural bar range, for example 42:58",
    )
    parser.add_argument("--section", help="Named rehearsal section")
    parser.add_argument(
        "--include-part",
        "--include-track",
        dest="include_part",
        action="append",
        default=[],
        help="Explicitly include a part id; repeatable",
    )
    parser.add_argument(
        "--exclude-part",
        "--exclude-track",
        dest="exclude_part",
        action="append",
        default=[],
        help="Explicitly exclude a part id; repeatable",
    )
    args = parser.parse_args(list(argv))

    try:
        score_path = workspace_relative(args.score, label="score document")
        output_path = workspace_relative(args.output, label=f"{kind} output")
        factor = tempo_factor(args.tempo)
        if args.bars is not None and args.section is not None:
            raise ValueError("choose either --bars or --section, not both")
        selected_bars = bar_range(args.bars) if args.bars is not None else None

        document = ScoreFileStore(context.workspace).read(score_path)
        result = RenderScoreMidi(
            artifacts=BinaryFileStore(context.workspace),
        ).execute(
            document,
            output_path,
            kind=kind,
            tempo_factor=factor,
            include_part_ids=tuple(args.include_part),
            exclude_part_ids=tuple(args.exclude_part),
            bar_range=selected_bars,
            section_name=args.section,
        )
    except (
        BinaryArtifactError,
        PracticePathError,
        ScoreDocumentError,
        ScoreMidiError,
        ScoreRealizationError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(
        {
            "output": result.output_path,
            "realization_id": result.realization_id,
            "parts": list(result.part_ids),
            "bytes": result.byte_count,
            "kind": kind,
            "tempo": args.tempo,
        },
        context.stdout,
        indent=2,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


def backing_render(argv: Sequence[str], context: CliContext) -> int:
    return _render(argv, context, kind="backing")


def drums_render(argv: Sequence[str], context: CliContext) -> int:
    return _render(argv, context, kind="drums")


SCORE_RENDER_HANDLERS: dict[str, NativeHandler] = {
    "backing-render": backing_render,
    "drums-render": drums_render,
}
