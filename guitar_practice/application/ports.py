"""Dependency-inversion ports for deterministic application side effects."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from guitar_practice.application.imported_score import ImportedScore


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
class ConvertedScore:
    """MusicXML plus explicit provenance returned by a score-conversion adapter."""

    musicxml: bytes
    converter: str
    converter_version: str | None = None


class ScoreConverter(Protocol):
    """Convert a supported score source into MusicXML without exposing process details."""

    def convert(self, source_path: str) -> ConvertedScore:
        ...


class ScoreParser(Protocol):
    """Parse normalized MusicXML bytes into the transient import contract."""

    def parse(self, data: bytes, *, source_id: str) -> ImportedScore:
        ...


@dataclass(frozen=True)
class ScoreExportDiagnostic:
    """Portable diagnostic emitted while adapting canonical score data."""

    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True)
class ExportedScore:
    """Bytes produced by a score exporter plus explicit mapping diagnostics."""

    data: bytes
    diagnostics: tuple[ScoreExportDiagnostic, ...] = ()


class ScoreExporter(Protocol):
    """Export canonical Score IR without exposing adapter implementation details."""

    def export(self, document: Mapping[str, Any]) -> ExportedScore:
        ...


@dataclass(frozen=True)
class AudioRenderProfile:
    """Explicit PCM render contract for local audio adapters."""

    sample_rate: int
    channels: int
    sample_format: str


@dataclass(frozen=True)
class RenderedAudio:
    """Rendered WAV bytes plus renderer provenance."""

    wav: bytes
    renderer: str
    renderer_version: str | None
    soundfont: str | None


class AudioRenderer(Protocol):
    """Render symbolic MIDI bytes to WAV audio for one explicit profile."""

    def render(self, midi: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        ...



@dataclass(frozen=True)
class PlayedMidi:
    """Successful MIDI playback plus explicit player provenance."""

    player: str
    player_version: str | None
    soundfont: str | None = None


class MidiPlayer(Protocol):
    """Play deterministic MIDI bytes through one bounded local adapter."""

    def play(self, midi: bytes) -> PlayedMidi:
        ...
