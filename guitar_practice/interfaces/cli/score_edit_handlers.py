"""Interactive canonical Score IR editing shell."""

from __future__ import annotations

import argparse
import json
import os
import shlex
from collections.abc import Callable, Sequence
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.adapters.midi_playback import FluidSynthMidiPlayer, MidiPlaybackError
from guitar_practice.adapters.musicxml_export import MusicXmlExportError, MusicXmlExporter
from guitar_practice.adapters.score_files import ScoreDocumentError, ScoreFileStore
from guitar_practice.application.score_editor import ScoreEditError, ScoreEditSession
from guitar_practice.domain import score
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    bar_range,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]

_HELP = """Commands:
  context
  show
  validate
  form <name:bars ...>
  chords [--section <label>] <bar-separated chord grid>
  part add <input.json>
  notes <part-id> <input.json>
  voicing <part-id> <input.json>
  rhythm <part-id> <input.json>
  technique <part-id> <input.json>
  play [--section <label> | --bars START:END] [--output <midi>] [--soundfont <sf2>]
  export <output.musicxml>
  save
  cancel
  help
"""


def _write_json(value: object, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def _chord_args(tokens: list[str]) -> tuple[str | None, str]:
    section: str | None = None
    rest = tokens[1:]
    if rest[:1] == ["--section"]:
        if len(rest) < 3:
            raise ValueError("chords --section requires a label and chord grid")
        section = rest[1]
        rest = rest[2:]
    grid = " ".join(rest).strip()
    if not grid:
        raise ValueError("chords requires a chord grid")
    return section, grid


def _play_args(
    tokens: list[str],
) -> tuple[str | None, tuple[int, int] | None, str | None, str | None]:
    section: str | None = None
    bars: tuple[int, int] | None = None
    output: str | None = None
    soundfont: str | None = None
    index = 1
    while index < len(tokens):
        option = tokens[index]
        if option not in {"--section", "--bars", "--output", "--soundfont"}:
            raise ValueError(f"unknown play option: {option}")
        if index + 1 >= len(tokens):
            raise ValueError(f"{option} requires a value")
        value = tokens[index + 1]
        if option == "--section":
            section = value
        elif option == "--bars":
            bars = bar_range(value)
        elif option == "--output":
            output = value
        else:
            soundfont = value
        index += 2
    if section is not None and bars is not None:
        raise ValueError("choose either --section or --bars, not both")
    return section, bars, output, soundfont


def _soundfont_path(value: str | None, context: CliContext) -> Path | None:
    selected = value or os.environ.get("GUITAR_SOUNDFONT")
    if selected is None:
        return None
    path = Path(selected)
    return path if path.is_absolute() else context.workspace / path


def score_edit(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score edit")
    parser.add_argument("score", help="Explicit canonical Score IR document to edit")
    args = parser.parse_args(list(argv))

    try:
        source = workspace_relative(args.score, label="score document")
        session = ScoreEditSession(source, ScoreFileStore(context.workspace))
    except (PracticePathError, ScoreDocumentError, ScoreEditError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    inputs = JsonFileStore(context.workspace)
    initial = session.context()
    print(
        f"Editing {initial['id']} ({initial['bars']} bars). "
        "Changes remain in memory until 'save'.",
        file=context.stdout,
    )
    print(_HELP, file=context.stdout, end="")

    while True:
        context.stdout.write("score-edit> ")
        context.stdout.flush()
        line = context.stdin.readline()
        if line == "":
            print("cancelled", file=context.stdout)
            return exit_codes.OK
        raw = line.strip()
        if not raw:
            continue

        try:
            tokens = shlex.split(raw)
            command = tokens[0].casefold()

            if command in {"cancel", "quit"}:
                if len(tokens) != 1:
                    raise ValueError("cancel takes no arguments")
                print("cancelled", file=context.stdout)
                return exit_codes.OK

            if command == "save":
                if len(tokens) != 1:
                    raise ValueError("save takes no arguments")
                saved = session.save()
                _write_json(
                    {
                        "saved": source,
                        "id": saved["id"],
                        "bars": len(saved["bars"]),
                    },
                    context,
                )
                return exit_codes.OK

            if command == "help":
                print(_HELP, file=context.stdout, end="")
                continue

            if command == "context":
                if len(tokens) != 1:
                    raise ValueError("context takes no arguments")
                _write_json(session.context(), context)
                continue

            if command == "show":
                if len(tokens) != 1:
                    raise ValueError("show takes no arguments")
                context.stdout.write(score.dumps(session.snapshot()))
                continue

            if command == "validate":
                if len(tokens) != 1:
                    raise ValueError("validate takes no arguments")
                _write_json(session.validate(), context)
                continue

            if command == "form":
                spec = " ".join(tokens[1:]).strip()
                if not spec:
                    raise ValueError("form requires a section specification")
                session.replace_form(spec)
                _write_json(session.context(), context)
                continue

            if command == "chords":
                section, grid = _chord_args(tokens)
                session.replace_chords(grid, section=section)
                _write_json(session.context(), context)
                continue

            if command == "play":
                (
                    section,
                    selected_bars,
                    output_value,
                    soundfont_value,
                ) = _play_args(tokens)
                output = (
                    workspace_relative(output_value, label="playback output")
                    if output_value is not None
                    else None
                )
                artifacts = BinaryFileStore(context.workspace)
                metadata = JsonFileStore(context.workspace)
                payload = session.play(
                    artifacts=artifacts,
                    metadata=metadata,
                    player=FluidSynthMidiPlayer(
                        context.workspace,
                        soundfont=_soundfont_path(soundfont_value, context),
                    ),
                    output=output,
                    bar_range=selected_bars,
                    section_name=section,
                )
                _write_json(payload, context)
                continue

            if command == "export":
                if len(tokens) != 2:
                    raise ValueError("export requires <output.musicxml>")
                output = workspace_relative(tokens[1], label="export output")
                result = session.export_musicxml(
                    artifacts=BinaryFileStore(context.workspace),
                    exporter=MusicXmlExporter(),
                    output=output,
                )
                _write_json(
                    {
                        "output": output,
                        "format": "musicxml",
                        "diagnostics": [
                            item.as_dict() for item in result.diagnostics
                        ],
                    },
                    context,
                )
                continue

            if command == "part":
                if len(tokens) != 3 or tokens[1].casefold() != "add":
                    raise ValueError("part requires: part add <input.json>")
                input_path = workspace_relative(
                    tokens[2],
                    label="part input",
                )
                session.add_part(inputs.read(input_path))
                _write_json(session.context(), context)
                continue

            if command in {"notes", "voicing", "rhythm", "technique"}:
                if len(tokens) != 3:
                    raise ValueError(
                        f"{command} requires <part-id> <input.json>"
                    )
                part_id = tokens[1]
                input_path = workspace_relative(
                    tokens[2],
                    label=f"{command} input",
                )
                input_document = inputs.read(input_path)
                session.apply_structured(
                    command,
                    part_id=part_id,
                    input_document=input_document,
                )
                _write_json(session.context(), context)
                continue

            raise ValueError(f"unknown edit command: {command}")
        except (
            PracticePathError,
            ScoreDocumentError,
            JsonDocumentError,
            MidiPlaybackError,
            MusicXmlExportError,
            ScoreEditError,
            score.ScoreError,
            OSError,
            ValueError,
        ) as exc:
            print(f"score-edit: {exc}", file=context.stderr)


SCORE_EDIT_HANDLERS: dict[str, NativeHandler] = {
    "score-edit": score_edit,
}
