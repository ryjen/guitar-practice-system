"""Application use cases for deterministic scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain.scheduling import approval_status, propose


@dataclass(frozen=True)
class ProposeSchedule:
    documents: JsonDocumentStore

    def execute(self, snapshot_path: str) -> dict[str, Any]:
        snapshot = dict(self.documents.read(snapshot_path))
        return propose(snapshot)


@dataclass(frozen=True)
class CheckScheduleApproval:
    documents: JsonDocumentStore

    def execute(self, proposal_path: str, snapshot_path: str) -> dict[str, Any]:
        proposal = dict(self.documents.read(proposal_path))
        snapshot = dict(self.documents.read(snapshot_path))
        return approval_status(proposal, snapshot)
