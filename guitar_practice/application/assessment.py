"""Application use case for deterministic assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain.assessment import assess


@dataclass(frozen=True)
class EvaluateAssessment:
    documents: JsonDocumentStore

    def execute(self, request_path: str, gate_set_path: str) -> dict[str, Any]:
        request = dict(self.documents.read(request_path))
        gate_set = dict(self.documents.read(gate_set_path))
        return assess(request, gate_set)
