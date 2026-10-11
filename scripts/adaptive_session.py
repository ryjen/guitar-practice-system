#!/usr/bin/env python3
"""Compatibility shim for package-native adaptive-session recommendations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guitar_practice.adapters.json_values import JsonValueError, JsonValueFileReader
from guitar_practice.application.adaptive_session import AdaptiveSession
from guitar_practice.domain.adaptive_session import (
    SessionError,
    recommend,
    validate_request,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    args = parser.parse_args()

    try:
        result = AdaptiveSession(
            JsonValueFileReader(Path.cwd())
        ).execute(args.request)
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (SessionError, JsonValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


__all__ = [
    "SessionError",
    "recommend",
    "validate_request",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
