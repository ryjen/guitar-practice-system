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
from guitar_practice.application.score_import import (
    ImportScore,
    ScoreImportError,
    UnsupportedScoreFormat,
)
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
    "score-import": score_import,
    "score-tracks": score_tracks,
}
