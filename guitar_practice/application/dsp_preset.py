"""Application boundary for versioned DSP preset documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import WorkspaceTree
from guitar_practice.domain import dsp_preset


@dataclass(frozen=True)
class DspPresetDocuments:
    tree: WorkspaceTree

    def validate(self, path: str) -> dict[str, Any]:
        return dsp_preset.loads(self.tree.read_text(path))

    def canonicalize(self, path: str) -> str:
        return dsp_preset.canonicalize(self.tree.read_text(path))
