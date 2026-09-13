"""Dependency-inversion ports for deterministic application side effects."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping, Protocol


class Clock(Protocol):
    """Explicit time source for deterministic use cases that require a clock."""

    def now_iso8601(self) -> str:
        ...


class JsonDocumentStore(Protocol):
    """Bounded structured-document storage used by application services."""

    def read(self, path: str) -> Mapping[str, Any]:
        ...

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        ...


class DocumentLocator(Protocol):
    """Discover workspace-relative document paths from a bounded pattern."""

    def glob(self, pattern: str) -> Sequence[str]:
        ...


class BinaryArtifactStore(Protocol):
    """Bounded binary artifact storage used by application services."""

    def read_bytes(self, path: str) -> bytes:
        ...

    def write_bytes(self, path: str, data: bytes) -> None:
        ...
