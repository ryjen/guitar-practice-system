"""Native CLI handlers for deterministic versioned releases."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.release import ReleasePackager
from guitar_practice.domain.release import ReleaseError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _write_json(value: object, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def release_prepare(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl release prepare")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--previous-tag")
    parser.add_argument("--changed-paths")
    parser.add_argument(
        "--output-dir",
        default="generated/release",
    )
    args = parser.parse_args(list(argv))

    try:
        output = workspace_relative(args.output_dir, label="release output")
        changed_paths = (
            workspace_relative(
                args.changed_paths,
                label="release changed-paths input",
            )
            if args.changed_paths is not None
            else None
        )
        result = ReleasePackager(
            WorkspaceFileTree(context.workspace)
        ).prepare(
            output,
            tag=args.tag,
            source_sha=args.source_sha,
            previous_tag=args.previous_tag,
            changed_paths_path=changed_paths,
        )
    except (
        PracticePathError,
        ReleaseError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def release_verify(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl release verify")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument(
        "--output-dir",
        default="generated/release",
    )
    args = parser.parse_args(list(argv))

    try:
        output = workspace_relative(args.output_dir, label="release output")
        result = ReleasePackager(
            WorkspaceFileTree(context.workspace)
        ).verify(
            output,
            tag=args.tag,
            source_sha=args.source_sha,
        )
    except (
        PracticePathError,
        ReleaseError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


RELEASE_HANDLERS: dict[str, NativeHandler] = {
    "release-prepare": release_prepare,
    "release-verify": release_verify,
}
