"""Dependency-inversion ports for deterministic application side effects."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True)
class AudioRenderProfile:
    """Explicit audio characteristics requested from a renderer."""

    sample_rate: int = 44_100
    channels: int = 2
    sample_format: str = "s16"

    def __post_init__(self) -> None:
        if isinstance(self.sample_rate, bool) or self.sample_rate <= 0:
            raise ValueError("audio sample rate must be a positive integer")
        if isinstance(self.channels, bool) or self.channels <= 0:
            raise ValueError("audio channels must be a positive integer")
        if not self.sample_format:
            raise ValueError("audio sample format must not be empty")


@dataclass(frozen=True)
class RenderedAudio:
    """Rendered WAV bytes plus renderer and instrument-set provenance."""

    wav: bytes
    renderer: str
    renderer_version: str | None
    soundfont: str | None


class AudioRenderer(Protocol):
    """Render symbolic MIDI bytes to WAV audio for one explicit profile."""

    def render(self, midi: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        ...


@dataclass(frozen=True)
class ConvertedScore:
    """MusicXML plus explicit provenance returned by a score-conversion adapter."""

    musicxml: bytes
    converter: str
    converter_version: str | None = None


class ScoreConverter(Protocol):
    """Convert a supported score source into MusicXML without exposing process details."""

    def convert(self, source_path: str) -> ConvertedScore:
        ...
