"""Dependency-inversion ports for side effects and optional intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class Proposal:
    """Non-canonical candidate produced outside deterministic core logic."""

    kind: str
    content: Mapping[str, Any]
    provenance: Mapping[str, str] = field(default_factory=dict)
    warnings: Sequence[str] = ()


class ProposalProvider(Protocol):
    """Optional provider for advisory/generated candidates.

    Implementations may use local models, a supervisor gateway, or another
    inference system. Callers must treat the result as a proposal requiring
    deterministic validation and explicit approval before canonical mutation.
    """

    def propose(self, *, task: str, context: Mapping[str, Any]) -> Proposal:
        ...


class Clock(Protocol):
    def now_iso8601(self) -> str:
        ...


class JsonDocumentStore(Protocol):
    def read(self, path: str) -> Mapping[str, Any]:
        ...

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        ...
