"""Application use case for the public repository-boundary scan."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_practice.application.ports import WorkspaceTree
from guitar_practice.domain import public_boundary


@dataclass(frozen=True)
class PublicBoundaryValidation:
    tree: WorkspaceTree

    def findings(self) -> list[str]:
        files: list[tuple[str, str]] = []
        for path in self.tree.list_files("."):
            if not public_boundary.should_scan(path):
                continue
            try:
                content = self.tree.read_text(path)
            except UnicodeDecodeError:
                continue
            files.append((path, content))
        return public_boundary.scan_texts(files)

    def validate(self) -> list[str]:
        return self.findings()
