#!/usr/bin/env python3
"""Compatibility shim for package-native repository validation."""

from __future__ import annotations

import sys
from pathlib import Path

from guitar_practice.adapters.processes import PythonModuleProbe, SubprocessCommandRunner
from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.public_boundary import PublicBoundaryValidation
from guitar_practice.application.repository_validation import (
    RepositoryValidation,
    ValidationFailed,
    ValidationUnavailable,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    service = RepositoryValidation(
        runner=SubprocessCommandRunner(ROOT),
        modules=PythonModuleProbe(),
        public_boundary=PublicBoundaryValidation(WorkspaceFileTree(ROOT)),
        python_executable=sys.executable,
    )
    try:
        service.execute()
    except ValidationUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValidationFailed as exc:
        print(f"{exc.label} failed", file=sys.stderr)
        for detail in exc.details:
            print(detail, file=sys.stderr)
        return exc.returncode or 1
    print("\nRepository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
