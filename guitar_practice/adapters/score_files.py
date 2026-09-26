"""Canonical Score IR filesystem adapter."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from guitar_practice.domain import score


class ScoreDocumentError(ValueError):
    """A canonical Score IR document could not be read or written safely."""


class ScoreFileStore:
    """Persist canonical Score IR inside one explicit workspace."""

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
            raise ScoreDocumentError("score path must remain inside workspace")
        return resolved

    def read(self, path: str | Path) -> Mapping[str, Any]:
        resolved = self.resolve(path)
        try:
            return score.loads(resolved.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ScoreDocumentError(f"cannot read score document: {exc}") from exc
        except score.ScoreError as exc:
            raise ScoreDocumentError(str(exc)) from exc

    def write(self, path: str | Path, document: Mapping[str, Any]) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = score.dumps(dict(document))
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=resolved.parent,
                prefix=f".{resolved.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, resolved)
        except (OSError, score.ScoreError) as exc:
            if "temporary" in locals():
                temporary.unlink(missing_ok=True)
            raise ScoreDocumentError(f"cannot write score document: {exc}") from exc
