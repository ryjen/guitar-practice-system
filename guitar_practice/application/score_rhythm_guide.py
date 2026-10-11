"""Application boundary for Groove Engine rhythm guidance over Score IR."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.groove import GrooveCatalog
from guitar_practice.domain import score_groove


@dataclass(frozen=True)
class ScoreRhythmGuide:
    grooves: GrooveCatalog

    def build(
        self,
        document: Mapping[str, Any],
        preset_id: str,
        *,
        bar: int = 1,
    ) -> dict[str, Any]:
        preset = self.grooves.show(preset_id)
        return score_groove.rhythm_guide(document, preset, bar=bar)
