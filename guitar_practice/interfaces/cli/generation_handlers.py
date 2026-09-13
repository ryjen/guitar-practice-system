"""CLI handlers for deterministic generated practice artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.generation import (
    GenerateBackingCatalog,
    GenerateMidiExercises,
    GeneratePracticeProgression,
)
from guitar_practice.domain import midi, practice_progression
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def backing_generate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing generate")
    try:
        parser.parse_args(list(argv))
        documents = JsonFileStore(context.workspace)
        service = GenerateBackingCatalog(
            documents=documents,
            locator=documents,
            artifacts=BinaryFileStore(context.workspace),
        )
        results = service.execute()
    except (midi.ManifestError, JsonDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(results, context.stdout, indent=2)
    context.stdout.write("\n")
    return exit_codes.OK


def progression_generate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression generate")
    parser.add_argument("request")
    parser.add_argument(
        "--profile",
        default=practice_progression.PROFILE,
        choices=[practice_progression.PROFILE],
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--render-midi", action="store_true")
    args = parser.parse_args(list(argv))
    if args.render_midi and args.output_dir is None:
        parser.error("--render-midi requires --output-dir")

    try:
        service = GeneratePracticeProgression(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
        )
        result = service.execute(args.request, profile=args.profile)
        if args.output_dir is None:
            json.dump(result, context.stdout, indent=2, sort_keys=True)
            context.stdout.write("\n")
        else:
            service.write(result, args.output_dir, render_midi=args.render_midi)
            context.stdout.write(f"{args.output_dir}\n")
    except (midi.ManifestError, JsonDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    return exit_codes.OK


def midi_generate_exercises(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl midi generate-exercises")
    try:
        parser.parse_args(list(argv))
        outputs = GenerateMidiExercises(
            documents=JsonFileStore(context.workspace),
            artifacts=BinaryFileStore(context.workspace),
        ).execute()
    except (JsonDocumentError, OSError, ValueError, KeyError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    for output in outputs:
        context.stdout.write(f"wrote {output}\n")
    return exit_codes.OK


GENERATION_HANDLERS: dict[str, NativeHandler] = {
    "backing-generate": backing_generate,
    "progression-generate": progression_generate,
    "midi-generate-exercises": midi_generate_exercises,
}
