"""CLI handlers for canonical score import and inspection."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.adapters.musicxml_export import MusicXmlExportError, MusicXmlExporter
from guitar_practice.adapters.musicxml_import import MusicXmlError, MusicXmlParser
from guitar_practice.adapters.midi_playback import FluidSynthMidiPlayer, MidiPlaybackError
from guitar_practice.adapters.score_conversion import (
    DirectMusicXmlConverter,
    MuseScoreConverter,
    ScoreConversionError,
)
from guitar_practice.adapters.score_files import ScoreDocumentError, ScoreFileStore
from guitar_practice.application.score_authoring import ScoreAuthoring
from guitar_practice.application.score_documents import ScoreDocuments
from guitar_practice.application.score_export import ExportScore
from guitar_practice.application.score_playback import PlayScoreMidi, RenderScoreMidi
from guitar_practice.application.score_import import (
    ImportScore,
    ScoreImportError,
    UnsupportedScoreFormat,
)
from guitar_practice.domain import score
from guitar_practice.domain.score_midi import ScoreMidiError
from guitar_practice.domain.score_realization import ScoreRealizationError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import bar_range
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
    return ScoreAuthoring(
        ScoreFileStore(context.workspace),
        inputs=JsonFileStore(context.workspace),
    )


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


def score_part_add(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score part add")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("--input", required=True, help="JSON input document containing one part")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        input_path = _workspace_relative(args.input, label="part input")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).add_part(
            source,
            input_path=input_path,
            output=output,
        )
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    added = document["parts"][-1]
    _write_json(
        {
            "output": output,
            "id": document["id"],
            "part": added["id"],
            "parts": len(document["parts"]),
        },
        context,
    )
    return exit_codes.OK


def score_notes(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score notes")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("part", help="Explicit part id whose note events will be replaced")
    parser.add_argument("--input", required=True, help="JSON input document containing a notes array")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        input_path = _workspace_relative(args.input, label="note input")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).replace_notes(
            source,
            part_id=args.part,
            input_path=input_path,
            output=output,
        )
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {
            "output": output,
            "id": document["id"],
            "part": args.part,
            "note_events": sum(
                1
                for part in document["parts"]
                if part["id"] == args.part
                for event in part["events"]
                if event["kind"] == "note"
            ),
        },
        context,
    )
    return exit_codes.OK


def score_voicing(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score voicing")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("part", help="Explicit part id whose note positions will be updated")
    parser.add_argument("--input", required=True, help="JSON input document containing positions")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        input_path = _workspace_relative(args.input, label="voicing input")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).apply_voicing(
            source,
            part_id=args.part,
            input_path=input_path,
            output=output,
        )
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    positioned = sum(
        1
        for part in document["parts"]
        if part["id"] == args.part
        for event in part["events"]
        if event["kind"] == "note" and "position" in event
    )
    _write_json(
        {
            "output": output,
            "id": document["id"],
            "part": args.part,
            "positioned_notes": positioned,
        },
        context,
    )
    return exit_codes.OK


def score_rhythm(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score rhythm")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("part", help="Explicit part id whose selected note timing will be updated")
    parser.add_argument("--input", required=True, help="JSON input document containing rhythm patches")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        input_path = _workspace_relative(args.input, label="rhythm input")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).apply_rhythm(
            source,
            part_id=args.part,
            input_path=input_path,
            output=output,
        )
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {
            "output": output,
            "id": document["id"],
            "part": args.part,
            "note_events": sum(
                1
                for part in document["parts"]
                if part["id"] == args.part
                for event in part["events"]
                if event["kind"] == "note"
            ),
        },
        context,
    )
    return exit_codes.OK


def score_technique(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score technique")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("part", help="Explicit part id whose selected note expression will be updated")
    parser.add_argument("--input", required=True, help="JSON input document containing technique patches")
    parser.add_argument("--output", required=True, help="New canonical Score IR JSON output")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        input_path = _workspace_relative(args.input, label="technique input")
        output = _workspace_relative(args.output, label="score output")
        document = _authoring(context).apply_technique(
            source,
            part_id=args.part,
            input_path=input_path,
            output=output,
        )
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    expressive = sum(
        1
        for part in document["parts"]
        if part["id"] == args.part
        for event in part["events"]
        if event["kind"] == "note"
        and ({"articulations", "techniques", "dynamics"} & set(event))
    )
    _write_json(
        {
            "output": output,
            "id": document["id"],
            "part": args.part,
            "expressive_notes": expressive,
        },
        context,
    )
    return exit_codes.OK


def _midi_renderer(context: CliContext) -> RenderScoreMidi:
    return RenderScoreMidi(
        documents=ScoreFileStore(context.workspace),
        artifacts=BinaryFileStore(context.workspace),
        metadata=JsonFileStore(context.workspace),
    )


def score_render(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score render")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("--format", required=True, choices=["musicxml", "midi"])
    parser.add_argument("--output", help="Explicit artifact output path")
    parser.add_argument("--bars", help="1-based inclusive structural bar range, for example 17:24")
    parser.add_argument("--section", help="Named score section")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        output = (
            _workspace_relative(args.output, label="score output")
            if args.output is not None
            else None
        )
        if args.bars is not None and args.section is not None:
            raise ValueError("choose either --bars or --section, not both")

        if args.format == "musicxml":
            if args.bars is not None or args.section is not None:
                raise ValueError("MusicXML render does not yet support --bars or --section")
            service = ExportScore(
                documents=ScoreFileStore(context.workspace),
                artifacts=BinaryFileStore(context.workspace),
                exporter=MusicXmlExporter(),
            )
            result = service.render(source) if output is None else service.render_to(source, output)
            if output is None:
                context.stdout.write(result.data.decode("utf-8"))
                for diagnostic in result.diagnostics:
                    print(
                        f"guitarctl: {diagnostic.severity}: {diagnostic.code}: "
                        f"{diagnostic.path}: {diagnostic.message}",
                        file=context.stderr,
                    )
            else:
                _write_json(
                    {
                        "output": output,
                        "format": args.format,
                        "diagnostics": [item.as_dict() for item in result.diagnostics],
                    },
                    context,
                )
            return exit_codes.OK

        if output is None:
            raise ValueError("MIDI render requires --output")
        selected_bars = bar_range(args.bars) if args.bars is not None else None
        payload = _midi_renderer(context).execute(
            source,
            output,
            bar_range=selected_bars,
            section_name=args.section,
        )
        _write_json(payload, context)
        return exit_codes.OK
    except (
        ScorePathError,
        ScoreDocumentError,
        MusicXmlExportError,
        JsonDocumentError,
        ScoreMidiError,
        ScoreRealizationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR


def _playback_soundfont(value: str | None, context: CliContext) -> Path | None:
    selected = value or os.environ.get("GUITAR_SOUNDFONT")
    if selected is None:
        return None
    path = Path(selected)
    return path if path.is_absolute() else context.workspace / path


def score_play(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl score play")
    parser.add_argument("score", help="Canonical Score IR JSON inside the workspace")
    parser.add_argument("--output", help="Optional workspace-relative MIDI artifact path")
    parser.add_argument("--bars", help="1-based inclusive structural bar range, for example 17:24")
    parser.add_argument("--section", help="Named score section")
    parser.add_argument("--soundfont", help="SoundFont path; defaults to GUITAR_SOUNDFONT")
    args = parser.parse_args(list(argv))

    try:
        source = _workspace_relative(args.score, label="score document")
        output = (
            _workspace_relative(args.output, label="score output")
            if args.output is not None
            else None
        )
        if args.bars is not None and args.section is not None:
            raise ValueError("choose either --bars or --section, not both")
        selected_bars = bar_range(args.bars) if args.bars is not None else None
        artifacts = BinaryFileStore(context.workspace)
        metadata = JsonFileStore(context.workspace)
        payload = PlayScoreMidi(
            renderer=RenderScoreMidi(
                documents=ScoreFileStore(context.workspace),
                artifacts=artifacts,
                metadata=metadata,
            ),
            artifacts=artifacts,
            metadata=metadata,
            player=FluidSynthMidiPlayer(
                context.workspace,
                soundfont=_playback_soundfont(args.soundfont, context),
            ),
        ).execute(
            source,
            output,
            bar_range=selected_bars,
            section_name=args.section,
        )
        _write_json(payload, context)
        return exit_codes.OK
    except MidiPlaybackError as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.UNAVAILABLE
    except (
        ScorePathError,
        ScoreDocumentError,
        JsonDocumentError,
        ScoreMidiError,
        ScoreRealizationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR


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
    "score-part-add": score_part_add,
    "score-notes": score_notes,
    "score-voicing": score_voicing,
    "score-rhythm": score_rhythm,
    "score-technique": score_technique,
    "score-render": score_render,
    "score-play": score_play,
    "score-show": score_show,
    "score-tracks": score_tracks,
    "score-validate": score_validate,
}
