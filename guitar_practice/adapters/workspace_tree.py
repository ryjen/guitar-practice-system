"""Filesystem adapter for repository/workspace tree operations."""

from __future__ import annotations

import shutil
from pathlib import Path


class WorkspaceFileTree:
    """Resolve tree operations against one explicit root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        return candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()

    def exists(self, path: str) -> bool:
        return self.resolve(path).exists()

    def read_text(self, path: str) -> str:
        return self.resolve(path).read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

    def read_bytes(self, path: str) -> bytes:
        return self.resolve(path).read_bytes()

    def list_files(self, path: str = ".") -> tuple[str, ...]:
        root = self.resolve(path)
        if not root.exists():
            return ()
        if root.is_file():
            return (root.relative_to(self.root).as_posix(),)
        return tuple(
            item.relative_to(self.root).as_posix()
            for item in sorted(root.rglob("*"))
            if item.is_file()
        )

    def copy_tree(self, source: str, destination: str) -> None:
        shutil.copytree(self.resolve(source), self.resolve(destination))

    def remove_tree(self, path: str) -> None:
        resolved = self.resolve(path)
        if resolved.exists():
            shutil.rmtree(resolved)

    def make_directory(self, path: str) -> None:
        self.resolve(path).mkdir(parents=True, exist_ok=True)
