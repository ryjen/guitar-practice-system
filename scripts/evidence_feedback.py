#!/usr/bin/env python3
"""Compatibility shim for package-native evidence feedback."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from guitar_practice.adapters.json_values import JsonValueError, JsonValueFileReader
from guitar_practice.application.evidence_feedback import EvidenceFeedback
from guitar_practice.domain.evidence_feedback import (
    EvidenceError,
    parse_date,
    summarize,
    validate_record,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records")
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args()

    try:
        result = EvidenceFeedback(
            JsonValueFileReader(Path.cwd())
        ).execute(
            args.records,
            as_of=args.as_of,
        )
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (EvidenceError, JsonValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


__all__ = [
    "EvidenceError",
    "parse_date",
    "summarize",
    "validate_record",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
