"""Native CLI handlers for the bounded guitar-dsp preset contract."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from guitar_practice.domain import dsp_preset
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]
MAX_SOURCE_BYTES = 4096


class DspPresetPathError(ValueError):
    """A user-selected preset path crossed the workspace boundary."""


def _workspace_relative(path: str) -> str:
    value = PurePosixPath(path.replace("\\", "/"))
    if value.is_absolute() or not value.parts or ".." in value.parts:
        raise DspPresetPathError("DSP preset must be a workspace-relative path")
    return value.as_posix()


def _read_document(path: str, context: CliContext) -> dict[str, object]:
    relative = _workspace_relative(path)
    resolved = (context.workspace / relative).resolve()
    root = context.workspace.resolve()
    if resolved != root and root not in resolved.parents:
        raise DspPresetPathError("DSP preset resolves outside the workspace")
    if resolved.stat().st_size > MAX_SOURCE_BYTES:
        raise dsp_preset.DspPresetError(
            f"DSP preset source must be at most {MAX_SOURCE_BYTES} bytes"
        )
    return dsp_preset.loads(resolved.read_text(encoding="utf-8"))


def _parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("document", help="Workspace-relative guitar-dsp preset JSON")
    return parser


def dsp_preset_validate(argv: Sequence[str], context: CliContext) -> int:
    args = _parser("guitarctl dsp preset validate").parse_args(list(argv))
    try:
        document = _read_document(args.document, context)
    except (
        DspPresetPathError,
        dsp_preset.DspPresetError,
        OSError,
        UnicodeError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(
        {
            "preset": document["preset"],
            "schema": dsp_preset.SCHEMA_ID,
            "valid": True,
            "version": dsp_preset.SCHEMA_VERSION,
        },
        context.stdout,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


def dsp_preset_canonicalize(argv: Sequence[str], context: CliContext) -> int:
    args = _parser("guitarctl dsp preset canonicalize").parse_args(list(argv))
    try:
        document = _read_document(args.document, context)
        encoded = dsp_preset.dumps(document)
    except (
        DspPresetPathError,
        dsp_preset.DspPresetError,
        OSError,
        UnicodeError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    context.stdout.write(encoded)
    context.stdout.write("\n")
    return exit_codes.OK


DSP_HANDLERS: dict[str, NativeHandler] = {
    "dsp-preset-validate": dsp_preset_validate,
    "dsp-preset-canonicalize": dsp_preset_canonicalize,
}
