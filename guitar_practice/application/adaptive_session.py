"""Application orchestration for adaptive practice-session recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonValueReader
from guitar_practice.domain import adaptive_session


@dataclass(frozen=True)
class AdaptiveSession:
    documents: JsonValueReader

    def execute(self, path: str) -> dict[str, Any]:
        request = self.documents.read(path)
        return adaptive_session.recommend(request)
