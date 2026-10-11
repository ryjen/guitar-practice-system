"""Native CLI handlers for advisory evidence/session workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import date

from guitar_practice.adapters.json_values import JsonValueError, JsonValueFileReader
from guitar_practice.application.adaptive_session import AdaptiveSession
from guitar_practice.application.evidence_feedback import EvidenceFeedback
from guitar_practice.domain.adaptive_session import SessionError
from guitar_practice.domain.evidence_feedback import EvidenceError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _write_json(value: object, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def session_adapt(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl session adapt")
    parser.add_argument("request", help="Adaptive-session request JSON")
    args = parser.parse_args(list(argv))

    try:
        request = workspace_relative(args.request, label="session request")
        result = AdaptiveSession(JsonValueFileReader(context.workspace)).execute(
            request
        )
    except (
        PracticePathError,
        JsonValueError,
        SessionError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


def evidence_feedback(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl evidence feedback")
    parser.add_argument("records", help="Evidence JSON object or raw records array")
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args(list(argv))

    try:
        records = workspace_relative(args.records, label="evidence input")
        result = EvidenceFeedback(
            JsonValueFileReader(context.workspace)
        ).execute(
            records,
            as_of=args.as_of,
        )
    except (
        PracticePathError,
        JsonValueError,
        EvidenceError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(result, context)
    return exit_codes.OK


ADVISORY_HANDLERS: dict[str, NativeHandler] = {
    "session-adapt": session_adapt,
    "evidence-feedback": evidence_feedback,
}
