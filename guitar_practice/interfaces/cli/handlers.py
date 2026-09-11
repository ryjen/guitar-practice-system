"""Package-native CLI command handlers."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.assessment import EvaluateAssessment
from guitar_practice.application.discovery import SearchCatalog
from guitar_practice.application.scheduling import CheckScheduleApproval, ProposeSchedule
from guitar_practice.domain.assessment import AssessmentError
from guitar_practice.domain.discovery import DiscoveryError
from guitar_practice.domain.scheduling import SchedulingError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _write_json(value: Any, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


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


NATIVE_HANDLERS: dict[str, NativeHandler] = {
    "discover-search": discover_search,
    "schedule-propose": schedule_propose,
    "schedule-check-approval": schedule_check_approval,
    "assess-evaluate": assess_evaluate,
}
