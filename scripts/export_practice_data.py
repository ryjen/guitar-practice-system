#!/usr/bin/env python3
"""Compatibility shim for package-native practice-data export."""

from __future__ import annotations

import argparse
from pathlib import Path

from guitar_practice.adapters.json_values import JsonValueFileReader
from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_data_export import (
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    PracticeDataExport,
)
from guitar_practice.domain.practice_data import (
    CatalogError,
    render_catalog,
    validate_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / DEFAULT_SOURCE


def _service() -> PracticeDataExport:
    return PracticeDataExport(
        values=JsonValueFileReader(ROOT),
        tree=WorkspaceFileTree(ROOT),
    )


def load_catalog() -> dict:
    return _service()._catalog()


def export(output: Path) -> None:
    _service().export(str(output))


def check(output: Path) -> None:
    _service().check(str(output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        check(output) if args.check else export(output)
    except (CatalogError, ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
