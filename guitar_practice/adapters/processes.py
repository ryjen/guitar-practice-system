"""Process adapters for repository validation."""

from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Sequence
from pathlib import Path


class SubprocessCommandRunner:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def run(self, command: Sequence[str]) -> int:
        return subprocess.run(
            list(command),
            cwd=self.workspace,
            check=False,
        ).returncode


class PythonModuleProbe:
    def available(self, module: str) -> bool:
        return importlib.util.find_spec(module) is not None
