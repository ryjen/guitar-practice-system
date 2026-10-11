"""Application orchestration for advisory evidence feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonValueReader
from guitar_practice.domain import evidence_feedback


@dataclass(frozen=True)
class EvidenceFeedback:
    documents: JsonValueReader

    def execute(self, path: str, *, as_of: str) -> dict[str, Any]:
        payload = self.documents.read(path)
        records = (
            payload.get("records")
            if isinstance(payload, dict)
            else payload
        )
        return evidence_feedback.summarize(
            records,
            evidence_feedback.parse_date(as_of, "as_of"),
        )
