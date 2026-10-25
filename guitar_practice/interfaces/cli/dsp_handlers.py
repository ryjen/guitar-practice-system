"""Native CLI handlers for versioned guitar-to-DSP preset documents."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.adapters.dsp_render import DspAudioRenderError, SubprocessDspAudioRenderer
from guitar_practice.application.dsp_render import RenderDspRecording
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
    except (
        PracticePathError,
        dsp_preset.DspPresetError,
        OSError,
        UnicodeError,
    ) as exc:
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



def dsp_audio_render(argv: Sequence[str], context: CliContext) -> int:
    """Select a recording and invoke the portable DSP executable (no DSP in Python)."""
    parser = argparse.ArgumentParser(prog="guitarctl render")
    parser.add_argument("source")
    parser.add_argument("--output", required=True)
    parser.add_argument("--preset")
    parser.add_argument(
        "--effects",
        default="delay",
        choices=("none", "delay", "tremolo", "tremolo,delay", "delay,tremolo"),
    )
    parser.add_argument("--engine", default="dsp")
    for key in (
        "delay-ms", "feedback", "mix", "tempo", "subdivision",
        "tremolo-rate", "tremolo-depth", "tremolo-shape",
    ):
        parser.add_argument(f"--{key}")
    args = parser.parse_args(list(argv))
    options: list[str] = []
    for key in (
        "delay-ms", "feedback", "mix", "tempo", "subdivision",
        "tremolo-rate", "tremolo-depth", "tremolo-shape",
    ):
        value = getattr(args, key.replace("-", "_"))
        if value is not None:
            options.extend((f"--{key}", value))

    try:
        source = workspace_relative(args.source, label="recording")
        output = workspace_relative(args.output, label="render output")
        preset = (
            workspace_relative(args.preset, label="DSP preset document")
            if args.preset is not None
            else None
        )
        # The shared lexical guard rejects traversal. Also check resolved
        # symlinks before reading an optional preset through the workspace tree.
        root = context.workspace.resolve()
        for label, value in (("recording", source), ("output", output), ("preset", preset)):
            if value is not None and not (root / value).resolve().is_relative_to(root):
                raise PracticePathError(f"{label} escapes workspace")
        rendered = RenderDspRecording(
            WorkspaceFileTree(context.workspace),
            SubprocessDspAudioRenderer(context.workspace, executable=args.engine),
        ).execute(
            source, output, effects=args.effects, options=options, preset=preset,
        )
    except (PracticePathError, dsp_preset.DspPresetError, OSError, UnicodeError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    except DspAudioRenderError as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return (
            exit_codes.UNAVAILABLE
            if str(exc).startswith("DSP engine unavailable:")
            else exit_codes.DATA_ERROR
        )

    json.dump(
        {"status": "rendered", "output": rendered, "effects": args.effects},
        context.stdout,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


DSP_HANDLERS: dict[str, NativeHandler] = {
    "dsp-preset-validate": dsp_preset_validate,
    "dsp-audio-render": dsp_audio_render,
    "dsp-preset-canonicalize": dsp_preset_canonicalize,
}
