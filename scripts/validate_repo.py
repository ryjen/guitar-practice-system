#!/usr/bin/env python3
"""Run the repository's canonical fast validation checks."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Sequence


def run(label: str, command: Sequence[str]) -> None:
    print(f"\n==> {label}")
    subprocess.run(command, check=True)


def main() -> int:
    if importlib.util.find_spec("ruff") is None:
        print(
            "Ruff is required for repository validation. "
            "Install pinned development dependencies with: "
            "python -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return 2

    source_dirs = ["scripts", "tests", "tools"]
    checks = (
        (
            "Compile Python sources",
            [sys.executable, "-m", "compileall", "-q", *source_dirs],
        ),
        (
            "Run Ruff static analysis",
            [sys.executable, "-m", "ruff", "check", *source_dirs],
        ),
        (
            "Enforce public repository boundary",
            [sys.executable, "scripts/check_public_boundary.py"],
        ),
        (
            "Run unit tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
    )

    try:
        for label, command in checks:
            run(label, command)
    except subprocess.CalledProcessError as exc:
        return exc.returncode or 1

    print("\nRepository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
