"""Application use cases for explicit canonical Score IR documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import score


def _default_score_id(title: str) -> str:
    if not isinstance(title, str):
        raise score.ScoreError("metadata.title must be a non-empty string")
    safe = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    return safe[:64] or "score"


def new_score(*, title: str, score_id: str | None = None) -> dict[str, Any]:
    """Build the smallest valid deterministic Score IR document."""

    document: dict[str, Any] = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": score_id if score_id is not None else _default_score_id(title),
        "metadata": {"title": title},
        "bars": [{"number": 1}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [],
        "parts": [],
    }
    score.validate(document)
    return document


@dataclass(frozen=True)
class ScoreDocuments:
    """Coordinate explicit canonical score creation, loading, and validation."""

    documents: JsonDocumentStore

    def create(
        self,
        *,
        title: str,
        score_id: str | None = None,
        output: str | None = None,
    ) -> dict[str, Any]:
        document = new_score(title=title, score_id=score_id)
        if output is not None:
            self.documents.write(output, document)
        return document

    def load(self, path: str) -> dict[str, Any]:
        document = dict(self.documents.read(path))
        score.validate(document)
        return document

    def validation_report(self, path: str) -> dict[str, Any]:
        document = self.load(path)
        return {
            "valid": True,
            "schema": document["schema"],
            "version": document["version"],
            "id": document["id"],
        }
