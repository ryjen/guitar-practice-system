"""AI-facing application contracts.

AI is advisory. Outputs are proposals, never canonical state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class InferenceProvenance:
    provider: str
    model: str
    request_id: str
    input_digest: str
    output_digest: str


@dataclass(frozen=True)
class ApprovalDecision:
    status: ProposalStatus
    actor: str
    reason: str | None = None
    metadata: Mapping[str, str] | None = None


def may_mutate_canonical_state(status: ProposalStatus) -> bool:
    """Only explicitly approved proposals may cross into mutation workflows."""

    return status is ProposalStatus.APPROVED
