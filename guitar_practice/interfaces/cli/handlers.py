"""Package-native CLI command handlers."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.assessment import EvaluateAssessment
from guitar_practice.application.discovery import SearchCatalog
from guitar_practice.application.midi import GenerateMidi, ValidateMidi
from guitar_practice.application.progression import ProgressionCatalog
from guitar_practice.application.scheduling import CheckScheduleApproval, ProposeSchedule
from guitar_practice.domain.assessment import AssessmentError
from guitar_practice.domain.discovery import DiscoveryError
from guitar_practice.domain.midi import ManifestError as MidiManifestError
from guitar_practice.domain.progression import ProgressionError
from guitar_practice.domain.scheduling import SchedulingError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _write_json(value: Any, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def _progression_service(context: CliContext) -> ProgressionCatalog:
    return ProgressionCatalog(JsonFileStore(context.workspace))


def discover_search(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl discover search")
    parser.add_argument("request", help="Discovery request JSON")
    parser.add_argument("catalog", help="Repository catalog JSON")
    try:
        args = parser.parse_args(list(argv))
        service = SearchCatalog(JsonFileStore(context.workspace))
        result = service.execute(args.request, args.catalog)
    except (DiscoveryError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def schedule_propose(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl schedule propose")
    parser.add_argument("snapshot", help="Scheduling snapshot JSON")
    try:
        args = parser.parse_args(list(argv))
        service = ProposeSchedule(JsonFileStore(context.workspace))
        result = service.execute(args.snapshot)
    except (SchedulingError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def schedule_check_approval(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl schedule check-approval")
    parser.add_argument("proposal", help="Schedule proposal JSON")
    parser.add_argument("current_snapshot", help="Current scheduling snapshot JSON")
    try:
        args = parser.parse_args(list(argv))
        service = CheckScheduleApproval(JsonFileStore(context.workspace))
        result = service.execute(args.proposal, args.current_snapshot)
    except (SchedulingError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def assess_evaluate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl assess evaluate")
    parser.add_argument("request", help="Assessment request JSON")
    parser.add_argument("gate_set", help="Assessment gate-set JSON")
    try:
        args = parser.parse_args(list(argv))
        service = EvaluateAssessment(JsonFileStore(context.workspace))
        result = service.execute(args.request, args.gate_set)
    except (AssessmentError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def progression_validate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression validate")
    parser.parse_args(list(argv))
    try:
        count = _progression_service(context).validate()
    except (ProgressionError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    context.stdout.write(f"validated {count} progression presets\n")
    return exit_codes.OK


def progression_list(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression list")
    parser.parse_args(list(argv))
    try:
        preset_ids = _progression_service(context).list_ids()
    except (ProgressionError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    for preset_id in preset_ids:
        context.stdout.write(f"{preset_id}\n")
    return exit_codes.OK


def progression_show(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression show")
    parser.add_argument("preset_id")
    try:
        args = parser.parse_args(list(argv))
        result = _progression_service(context).show(args.preset_id)
    except (ProgressionError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


def progression_resolve(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression resolve")
    parser.add_argument("preset_id")
    parser.add_argument("key_signature")
    parser.add_argument("--tonal-center")
    try:
        args = parser.parse_args(list(argv))
        chords = _progression_service(context).resolve(
            args.preset_id,
            args.key_signature,
            tonal_center=args.tonal_center,
        )
    except (ProgressionError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    payload: dict[str, Any] = {
        "preset": args.preset_id,
        "key_signature": args.key_signature,
        "chords": chords,
    }
    if args.tonal_center is not None:
        payload["tonal_center"] = args.tonal_center
    _write_json(payload, context)
    return exit_codes.OK


def progression_fourths(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl progression fourths")
    parser.add_argument("preset_id")
    parser.add_argument("--start-key", default="C")
    parser.add_argument("--count", type=int, default=12)
    try:
        args = parser.parse_args(list(argv))
        positions = _progression_service(context).fourths(
            args.preset_id,
            start_key=args.start_key,
            count=args.count,
        )
    except (ProgressionError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(
        {
            "preset": args.preset_id,
            "traversal": "circle-of-fourths",
            "start_key": positions[0]["key_signature"],
            "count": len(positions),
            "positions": positions,
        },
        context,
    )
    return exit_codes.OK


def midi_generate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl midi generate")
    parser.add_argument("manifest")
    parser.add_argument("output")
    try:
        args = parser.parse_args(list(argv))
        service = GenerateMidi(
            JsonFileStore(context.workspace),
            BinaryFileStore(context.workspace),
        )
        result = service.execute(args.manifest, args.output)
    except (MidiManifestError, JsonDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


def midi_validate(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl midi validate")
    parser.add_argument("manifest")
    parser.add_argument("midi")
    try:
        args = parser.parse_args(list(argv))
        service = ValidateMidi(
            JsonFileStore(context.workspace),
            BinaryFileStore(context.workspace),
        )
        result = service.execute(args.manifest, args.midi)
    except (MidiManifestError, JsonDocumentError, OSError, ValueError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


NATIVE_HANDLERS: dict[str, NativeHandler] = {
    "discover-search": discover_search,
    "schedule-propose": schedule_propose,
    "schedule-check-approval": schedule_check_approval,
    "assess-evaluate": assess_evaluate,
    "progression-validate": progression_validate,
    "progression-list": progression_list,
    "progression-show": progression_show,
    "progression-resolve": progression_resolve,
    "progression-fourths": progression_fourths,
    "midi-generate": midi_generate,
    "midi-validate": midi_validate,
}
