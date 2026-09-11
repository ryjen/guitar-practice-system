"""Filesystem adapter for binary artifacts."""

from __future__ import annotations

from pathlib import Path


class BinaryFileStore:
    """Resolve relative artifact paths against one explicit workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.workspace / candidate).resolve()
        )

    def read_bytes(self, path: str) -> bytes:
        return self.resolve(path).read_bytes()

    def write_bytes(self, path: str, data: bytes) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(data)
