"""CLI handlers for deterministic backing-track request resolution."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.backing import ResolveBackingRequest
from guitar_practice.application.score_backing import RenderScoreBacking
from guitar_practice.domain.midi import ManifestError
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


def backing_resolve(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing resolve")
    parser.add_argument("request", help="BackingTrackRequest JSON")
    parser.add_argument("--output", help="Optional BackingTrackSpec output JSON")
    try:
        args = parser.parse_args(list(argv))
        service = ResolveBackingRequest(JsonFileStore(context.workspace))
        if args.output is not None:
            service.execute_to(args.request, args.output)
            return exit_codes.OK
        result = service.execute(args.request)
    except (ManifestError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(result, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")
    return exit_codes.OK


def backing_render(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing render")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("--tempo", required=True, help="Practice tempo percentage, for example 75%")
    parser.add_argument("--output", required=True, help="Workspace-relative MIDI output path")
    parser.add_argument("--bars", help="1-based inclusive structural bar range, for example 42:58")
    parser.add_argument("--section", help="Named score section")
    parser.add_argument("--include-part", action="append", default=[])
    parser.add_argument("--exclude-part", action="append", default=[])
    args = parser.parse_args(list(argv))

    try:
        score_path = workspace_relative(args.score, label="score document")
        output = workspace_relative(args.output, label="backing output")
        factor = tempo_factor(args.tempo)
        if args.bars is not None and args.section is not None:
            raise ValueError("choose either --bars or --section, not both")
        selected_bars = bar_range(args.bars) if args.bars is not None else None
        RenderScoreBacking(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
        ).execute(
            score_path,
            output,
            tempo_factor=factor,
            include_part_ids=tuple(args.include_part),
            exclude_part_ids=tuple(args.exclude_part),
            bar_range=selected_bars,
            section_name=args.section,
        )
    except (
        PracticePathError,
        ScoreRealizationError,
        JsonDocumentError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    return exit_codes.OK


BACKING_HANDLERS: dict[str, NativeHandler] = {
    "backing-resolve": backing_resolve,
    "backing-render": backing_render,
}
