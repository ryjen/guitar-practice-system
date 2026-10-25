"""Application orchestration for a separate native DSP execution plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from guitar_practice.application.dsp_preset import DspPresetDocuments
from guitar_practice.application.ports import WorkspaceTree


class DspRenderEngine(Protocol):
    def render(
        self,
        source: str,
        output: str,
        *,
        effects: str,
        options: Sequence[str],
        preset_canonical: str | None,
    ) -> str: ...


@dataclass(frozen=True)
class RenderDspRecording:
    """Canonicalize the preset once, then delegate all audio to the native host."""

    documents: WorkspaceTree
    engine: DspRenderEngine

    def execute(
        self,
        source: str,
        output: str,
        *,
        effects: str,
        options: Sequence[str] = (),
        preset: str | None = None,
    ) -> str:
        canonical = (
            DspPresetDocuments(self.documents).canonicalize(preset)
            if preset is not None
            else None
        )
        return self.engine.render(
            source, output,
            effects=effects,
            options=options,
            preset_canonical=canonical,
        )
