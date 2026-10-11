"""Filesystem adapter for arbitrary JSON values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonValueError(ValueError):
    """A JSON value could not be read safely."""


class JsonValueFileReader:
    """Resolve JSON value paths against one explicit workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.workspace / candidate).resolve()
        )

    def read(self, path: str | Path) -> Any:
        resolved = self.resolve(path)
        try:
            return json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise JsonValueError(f"invalid JSON in {resolved}: {exc}") from exc
        except OSError as exc:
            raise JsonValueError(f"cannot read JSON value: {exc}") from exc
