#!/usr/bin/env python3
"""Compatibility shim for package-native public-boundary validation."""

from __future__ import annotations

import sys
from pathlib import Path

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.public_boundary import PublicBoundaryValidation
from guitar_practice.domain.public_boundary import (
    ALLOWLIST as ALLOWLIST,
    EXCLUDED_DIRS as EXCLUDED_DIRS,
    MARKERS as MARKERS,
    TEXT_SUFFIXES as TEXT_SUFFIXES,
    should_scan,
)

ROOT = Path(__file__).resolve().parents[1]


def candidates() -> list[Path]:
    tree = WorkspaceFileTree(ROOT)
    return [ROOT / path for path in tree.list_files(".") if should_scan(path)]


def violations() -> list[str]:
    return PublicBoundaryValidation(WorkspaceFileTree(ROOT)).findings()


def main() -> int:
    findings = violations()
    if findings:
        print("Public boundary check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Public boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
