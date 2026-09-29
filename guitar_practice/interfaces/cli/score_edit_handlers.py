"""Interactive canonical Score IR editing shell."""

from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Callable, Sequence

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.adapters.score_files import ScoreDocumentError, ScoreFileStore
from guitar_practice.application.score_editor import ScoreEditError, ScoreEditSession
from guitar_practice.domain import score
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import PracticePathError, workspace_relative
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]

_HELP = """Commands:
  context
  show
  validate
  form <name:bars ...>
  chords [--section <label>] <bar-separated chord grid>
  notes <part-id> <input.json>
  voicing <part-id> <input.json>
  rhythm <part-id> <input.json>
  technique <part-id> <input.json>
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
            ScoreEditError,
            score.ScoreError,
            OSError,
            ValueError,
        ) as exc:
            print(f"score-edit: {exc}", file=context.stderr)


SCORE_EDIT_HANDLERS: dict[str, NativeHandler] = {
    "score-edit": score_edit,
}
