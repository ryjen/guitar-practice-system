"""CLI handlers for imported-song symbolic practice stems."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import PurePosixPath

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.song_stems import RenderBackingStem
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


class StemPathError(ValueError):
    """A symbolic-stem path crossed the explicit workspace boundary."""


def _workspace_relative(path: str, *, label: str) -> str:
    value = PurePosixPath(path.replace("\\", "/"))
    if value.is_absolute() or not value.parts or ".." in value.parts:
        raise StemPathError(f"{label} must be a workspace-relative path")
    return value.as_posix()


def _tempo_factor(value: str) -> float:
    normalized = value.strip()
    if not normalized.endswith("%"):
        raise ValueError("tempo must be a percentage such as 75%")
    try:
        percent = float(normalized[:-1])
    except ValueError as exc:
        raise ValueError("tempo percentage must be numeric") from exc
    factor = percent / 100.0
    if factor <= 0:
        raise ValueError("tempo percentage must be positive")
    return factor


def backing_render(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing render")
    parser.add_argument("score", help="Canonical imported-score JSON inside the workspace")
    parser.add_argument("--tempo", required=True, help="Practice tempo percentage, for example 75%")
    parser.add_argument("--output", required=True, help="Workspace-relative MIDI output path")
    parser.add_argument("--include-track", action="append", default=[])
    parser.add_argument("--exclude-track", action="append", default=[])
    args = parser.parse_args(list(argv))

    try:
        score = _workspace_relative(args.score, label="score document")
        output = _workspace_relative(args.output, label="backing output")
        factor = _tempo_factor(args.tempo)
        RenderBackingStem(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
        ).execute(
            score,
            output,
            tempo_factor=factor,
            include_track_ids=tuple(args.include_track),
            exclude_track_ids=tuple(args.exclude_track),
        )
    except (StemPathError, JsonDocumentError, OSError, ValueError, KeyError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    return exit_codes.OK


STEM_HANDLERS: dict[str, NativeHandler] = {
    "backing-render": backing_render,
}
