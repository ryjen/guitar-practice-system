"""Filesystem adapter for bounded binary artifacts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class BinaryArtifactError(ValueError):
    """A binary artifact path or write violated the workspace boundary."""


class BinaryFileStore:
    """Resolve binary artifact paths against one explicit workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.workspace / candidate).resolve()
        )
        if not resolved.is_relative_to(self.workspace):
            raise BinaryArtifactError("artifact path must remain inside workspace")
        return resolved

    def read_bytes(self, path: str) -> bytes:
        try:
            return self.resolve(path).read_bytes()
        except OSError as exc:
            raise BinaryArtifactError(f"cannot read binary artifact: {exc}") from exc

    def write_bytes(self, path: str, data: bytes) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=resolved.parent,
                prefix=f".{resolved.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, resolved)
        except OSError as exc:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise BinaryArtifactError(f"cannot write binary artifact: {exc}") from exc
