"""Process-level runtime context for CLI command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class CliContext:
    workspace: Path
    stdout: TextIO
    stderr: TextIO
