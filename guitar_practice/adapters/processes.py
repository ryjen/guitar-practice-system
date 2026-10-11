"""Process adapters for repository validation."""

from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Sequence
from pathlib import Path

from guitar_practice.application.ports import CommandResult


class SubprocessCommandRunner:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def run(self, command: Sequence[str]) -> CommandResult:
        completed = subprocess.run(
            list(command),
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class PythonModuleProbe:
    def available(self, module: str) -> bool:
        return importlib.util.find_spec(module) is not None
