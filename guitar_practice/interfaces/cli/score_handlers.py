"""CLI handlers for canonical score import and inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import PurePosixPath

from guitar_practice.adapters.musicxml_import import MusicXmlError, MusicXmlParser
from guitar_practice.adapters.score_conversion import (
    DirectMusicXmlConverter,
    MuseScoreConverter,
    ScoreConversionError,
)
from guitar_practice.adapters.score_files import ScoreDocumentError, ScoreFileStore
from guitar_practice.application.score_authoring import ScoreAuthoring
from guitar_practice.application.score_documents import ScoreDocuments
from guitar_practice.application.score_import import (
    ImportScore,
    ScoreImportError,
    UnsupportedScoreFormat,
)
from guitar_practice.domain import score
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


class ScorePathError(ValueError):
    """A user-selected score document path crossed the workspace boundary."""


def _workspace_relative(path: str, *, label: str) -> str:
    value = PurePosixPath(path.replace("\\", "/"))
    if value.is_absolute() or not value.parts or ".." in value.parts:
        raise ScorePathError(f"{label} must be a workspace-relative path")
    return value.as_posix()


def _documents(context: CliContext) -> ScoreDocuments:
    return ScoreDocuments(ScoreFileStore(context.workspace))


def _write_json(value: object, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def score_init(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score init")
    parser.add_argument("--title", required=True, help="Score title")
    parser.add_argument("--id", dest="score_id", help="Optional canonical score id")
    parser.add_argument("--output", help="Optional canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        output = (
            _workspace_relative(args.output, label="score output")
            if args.output is not None
            else None
        )
        document = _documents(context).create(
            title=args.title,
            score_id=args.score_id,
            output=output,
        )
    except (ScorePathError, ScoreDocumentError, score.ScoreError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    if output is None:
        context.stdout.write(score.dumps(document))
    else:
        _write_json(
            {
                "output": output,
                "id": document["id"],
                "title": document["metadata"]["title"],
            },
            context,
        )
    return exit_codes.OK


def score_show(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score show")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    args = parser.parse_args(list(argv))

    try:
        score_path = _workspace_relative(args.score, label="score document")
        document = _documents(context).load(score_path)
    except (ScorePathError, ScoreDocumentError, score.ScoreError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    context.stdout.write(score.dumps(document))
    return exit_codes.OK


def score_validate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score validate")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    args = parser.parse_args(list(argv))

    try:
        score_path = _workspace_relative(args.score, label="score document")
        report = _documents(context).validation_report(score_path)
    except (ScorePathError, ScoreDocumentError, score.ScoreError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(report, context)
    return exit_codes.OK


def _authoring(context: CliContext) -> ScoreAuthoring:
    return ScoreAuthoring(ScoreFileStore(context.workspace))


def score_form(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score form")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("form", help="Section specification such as 'intro:4 verse:12'")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).replace_form(source, args.form, output)
    except (ScorePathError, ScoreDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {
            "output": output,
            "id": document["id"],
            "bars": len(document["bars"]),
            "sections": len(document.get("sections", [])),
        },
        context,
    )
    return exit_codes.OK


def score_chords(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score chords")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("grid", help="Bar-separated chord grid, for example 'C | Dm7 G7'")
    parser.add_argument("--section", help="Optional section label to replace")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).replace_chords(
            source,
            args.grid,
            output,
            section=args.section,
        )
    except (ScorePathError, ScoreDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {
            "output": output,
            "id": document["id"],
            "harmony_events": len(document.get("harmony", [])),
        },
        context,
    )
    return exit_codes.OK


def score_import(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score import")
    parser.add_argument("source", help="Guitar Pro or MusicXML score inside the workspace")
    parser.add_argument("--output", required=True, help="Canonical Score IR JSON output")
    parser.add_argument(
        "--musescore",
        default="mscore",
        help="MuseScore executable used for Guitar Pro conversion",
    )
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.source, label="score source")
        output = _workspace_relative(args.output, label="score output")
        suffix = PurePosixPath(source).suffix.casefold()
        converter = (
            DirectMusicXmlConverter(context.workspace)
            if suffix in {".xml", ".musicxml"}
            else MuseScoreConverter(context.workspace, executable=args.musescore)
        )
        document = ImportScore(
            converter=converter,
            parser=MusicXmlParser(),
            documents=ScoreFileStore(context.workspace),
        ).execute(source, output)
    except (
        MusicXmlError,
        ScoreConversionError,
        ScoreDocumentError,
        ScoreImportError,
        ScorePathError,
        UnsupportedScoreFormat,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(
        {
            "output": output,
            "id": document["id"],
            "title": document["metadata"]["title"],
            "parts": len(document["parts"]),
        },
        context.stdout,
        indent=2,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


def score_tracks(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score tracks")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    args = parser.parse_args(list(argv))

    try:
        score_path = _workspace_relative(args.score, label="score document")
        document = ScoreFileStore(context.workspace).read(score_path)
    except (ScorePathError, ScoreDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    payload = {
        "id": document["id"],
        "title": document["metadata"]["title"],
        "tracks": [
            {
                "id": part["id"],
                "name": part["name"],
                "role": part["role"],
                "instrument_name": part["instrument"]["name"],
                "instrument_family": part["instrument"]["family"],
                "midi": part["instrument"].get("midi"),
                "provenance": part.get("provenance"),
            }
            for part in document["parts"]
        ],
    }
    json.dump(payload, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")
    return exit_codes.OK


SCORE_HANDLERS: dict[str, NativeHandler] = {
    "score-init": score_init,
    "score-import": score_import,
    "score-form": score_form,
    "score-chords": score_chords,
    "score-show": score_show,
    "score-tracks": score_tracks,
    "score-validate": score_validate,
}
