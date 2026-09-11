#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic v2 scheduling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script execution predates the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore  # noqa: E402
from guitar_practice.application.scheduling import (  # noqa: E402
    CheckScheduleApproval,
    ProposeSchedule,
)
from guitar_practice.domain import scheduling as _domain  # noqa: E402

CONTRACT_VERSION = _domain.CONTRACT_VERSION
PROGRESSION_STATES = _domain.PROGRESSION_STATES
DEVELOPMENT_STATES = _domain.DEVELOPMENT_STATES
SchedulingError = _domain.SchedulingError
Candidate = _domain.Candidate
require_id = _domain.require_id
require_int = _domain.require_int
require_string_list = _domain.require_string_list
parse_date = _domain.parse_date
parse_datetime = _domain.parse_datetime
validate_constraints = _domain.validate_constraints
validate_snapshot = _domain.validate_snapshot
canonical_hash = _domain.canonical_hash
dependencies_satisfied = _domain.dependencies_satisfied
in_recovery = _domain.in_recovery
maintenance_due = _domain.maintenance_due
classify = _domain.classify
propose = _domain.propose
approval_status = _domain.approval_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose_parser = subparsers.add_parser("propose")
    propose_parser.add_argument("snapshot")
    approval_parser = subparsers.add_parser("check-approval")
    approval_parser.add_argument("proposal")
    approval_parser.add_argument("current_snapshot")
    args = parser.parse_args(argv)

    documents = JsonFileStore(Path.cwd())
    try:
        if args.command == "propose":
            result = ProposeSchedule(documents).execute(args.snapshot)
        else:
            result = CheckScheduleApproval(documents).execute(
                args.proposal,
                args.current_snapshot,
            )
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (SchedulingError, JsonDocumentError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
