"""Compatibility adapter for legacy script entrypoints.

This is intentionally isolated. It exists only to preserve behavior while script
internals are extracted into application/domain modules. Do not add new product
logic here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


class LegacyCommandError(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_script(script: str, argv: Sequence[str]) -> int:
    path = repository_root() / script
    if not path.is_file():
        raise LegacyCommandError(f"legacy command target not found: {script}")
    completed = subprocess.run(
        [sys.executable, str(path), *argv],
        cwd=repository_root(),
        check=False,
    )
    return completed.returncode
