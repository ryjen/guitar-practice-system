"""Filesystem adapter for structured JSON documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class JsonDocumentError(ValueError):
    """A JSON document could not be decoded as an object."""


class JsonFileStore:
    """Resolve relative document paths against one explicit workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        return candidate.resolve() if candidate.is_absolute() else (self.workspace / candidate).resolve()

    def read(self, path: str | Path) -> Mapping[str, Any]:
        resolved = self.resolve(path)
        try:
            value = json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise JsonDocumentError(f"invalid JSON in {resolved}: {exc}") from exc
        if not isinstance(value, dict):
            raise JsonDocumentError(f"JSON document must be an object: {resolved}")
        return value

    def write(self, path: str | Path, document: Mapping[str, Any]) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
