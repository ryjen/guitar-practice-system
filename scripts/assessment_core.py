#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic assessment."""

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
from guitar_practice.application.assessment import EvaluateAssessment  # noqa: E402
from guitar_practice.domain import assessment as _domain  # noqa: E402
from guitar_practice.domain.progression_state import (  # noqa: E402
    ACTIVE_RANK,
    STATES,
    TRANSITIONS,
)

OUTCOMES = _domain.OUTCOMES
AssessmentError = _domain.AssessmentError
nonempty = _domain.nonempty
parse_date = _domain.parse_date
stable_hash = _domain.stable_hash
transition_kind = _domain.transition_kind
validate_gate_set = _domain.validate_gate_set
validate_request = _domain.validate_request
observation_values = _domain.observation_values
evaluate_gate = _domain.evaluate_gate
assess = _domain.assess


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("gate_set")
    args = parser.parse_args(argv)

    try:
        result = EvaluateAssessment(JsonFileStore(Path.cwd())).execute(
            args.request,
            args.gate_set,
        )
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (AssessmentError, JsonDocumentError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
