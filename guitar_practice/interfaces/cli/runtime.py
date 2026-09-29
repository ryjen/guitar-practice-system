"""Process-level runtime context for CLI command handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import TextIO


@dataclass(frozen=True)
class CliContext:
    workspace: Path
    stdout: TextIO
    stderr: TextIO
    stdin: TextIO = field(default_factory=lambda: sys.stdin)
