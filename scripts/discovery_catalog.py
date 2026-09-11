#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic repository catalog discovery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script execution predates the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import discovery as _discovery  # noqa: E402

# Intentional compatibility exports for existing script-import consumers/tests.
CANONICAL_GENRES = _discovery.CANONICAL_GENRES
LIST_FIELDS = _discovery.LIST_FIELDS
SCALAR_FIELDS = _discovery.SCALAR_FIELDS
TARGET_TYPES = _discovery.TARGET_TYPES
DiscoveryError = _discovery.DiscoveryError
fingerprint = _discovery.fingerprint
local_candidate = _discovery.local_candidate
make_candidate_id = _discovery.make_candidate_id
normalize_evidence = _discovery.normalize_evidence
optional_strings = _discovery.optional_strings
score_item = _discovery.score_item
search_catalog = _discovery.search_catalog
strings = _discovery.strings
text = _discovery.text
token = _discovery.token
validate_catalog = _discovery.validate_catalog
validate_request = _discovery.validate_request


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: Iterable[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if args_list[:1] == ["search"]:
        args_list = args_list[1:]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("catalog")
    try:
        args = parser.parse_args(args_list)
        request = read_json(Path(args.request))
        catalog_path = Path(args.catalog)
        catalog = read_json(catalog_path) if catalog_path.exists() else None
        write(search_catalog(request, catalog))
        return 0
    except (DiscoveryError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
