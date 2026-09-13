"""CLI handlers for imported score inspection and conversion."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import PurePosixPath

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.adapters.score_conversion import (
    DirectMusicXmlConverter,
    MuseScoreConverter,
    ScoreConversionError,
)
from guitar_practice.application.score_import import ImportScore, UnsupportedScoreFormat
from guitar_practice.domain.musicxml import MusicXmlError
from guitar_practice.domain.song import song_from_dict
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
    parser.add_argument("--output", required=True, help="Canonical imported-score JSON output")
    parser.add_argument(
        "--musescore",
        default="MuseScore4",
        help="MuseScore executable used for Guitar Pro conversion",
    )
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.source, label="score source")
        output = _workspace_relative(args.output, label="score output")
        suffix = PurePosixPath(source).suffix.casefold()
        if suffix in {".xml", ".musicxml"}:
            converter = DirectMusicXmlConverter(context.workspace)
        else:
            converter = MuseScoreConverter(context.workspace, executable=args.musescore)
        song = ImportScore(
            converter=converter,
            documents=JsonFileStore(context.workspace),
        ).execute(source, output)
    except (
        ScoreConversionError,
        ScorePathError,
        UnsupportedScoreFormat,
        MusicXmlError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(
        {"output": output, "title": song.title, "tracks": len(song.tracks)},
        context.stdout,
        indent=2,
        sort_keys=True,
    )
    context.stdout.write("\n")
    return exit_codes.OK


def score_tracks(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score tracks")
    parser.add_argument("score", help="Canonical imported-score JSON inside the workspace")
    args = parser.parse_args(list(argv))

    try:
        score_path = _workspace_relative(args.score, label="score document")
        document = JsonFileStore(context.workspace).read(score_path)
        raw_song = document.get("song")
        if not isinstance(raw_song, dict):
            raise ValueError("score document must contain a song object")
        song = song_from_dict(raw_song)
    except (ScorePathError, JsonDocumentError, OSError, ValueError, KeyError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    payload = {
        "source_id": song.source_id,
        "title": song.title,
        "tracks": [
            {
                "id": track.id,
                "name": track.name,
                "role": track.classification.role.value,
                "classification_source": track.classification.source.value,
                "instrument_name": track.instrument_name,
                "midi_program": track.midi_program,
                "midi_channel": track.midi_channel,
                "is_percussion": track.is_percussion,
            }
            for track in song.tracks
        ],
    }
    json.dump(payload, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")
    return exit_codes.OK


SCORE_HANDLERS: dict[str, NativeHandler] = {
    "score-import": score_import,
    "score-tracks": score_tracks,
}
