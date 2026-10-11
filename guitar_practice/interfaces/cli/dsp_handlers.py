"""Native CLI handlers for versioned guitar-to-DSP preset documents."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.dsp_preset import DspPresetDocuments
from guitar_practice.domain import dsp_preset
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def dsp_preset_validate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(
        prog="guitarctl dsp preset validate"
    )
    parser.add_argument("document")
    args = parser.parse_args(list(argv))

    try:
        path = workspace_relative(args.document, label="DSP preset document")
        document = DspPresetDocuments(
            WorkspaceFileTree(context.workspace)
        ).validate(path)
    except (PracticePathError, dsp_preset.DspPresetError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(
        {
            "status": "valid",
            "schema": document["schema"],
            "version": document["version"],
            "preset": document["preset"],
        },
        context.stdout,
        indent=2,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


def dsp_preset_canonicalize(
    argv: Sequence[str],
    context: CliContext,
) -> int:
    parser = argparse.ArgumentParser(
        prog="guitarctl dsp preset canonicalize"
    )
    parser.add_argument("document")
    args = parser.parse_args(list(argv))

    try:
        path = workspace_relative(args.document, label="DSP preset document")
        canonical = DspPresetDocuments(
            WorkspaceFileTree(context.workspace)
        ).canonicalize(path)
    except (PracticePathError, dsp_preset.DspPresetError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    context.stdout.write(canonical)
    return exit_codes.OK


DSP_HANDLERS: dict[str, NativeHandler] = {
    "dsp-preset-validate": dsp_preset_validate,
    "dsp-preset-canonicalize": dsp_preset_canonicalize,
}
