"""Bounded score-conversion adapters for MusicXML and MuseScore."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from guitar_practice.application.ports import ConvertedScore


class ScoreConversionError(ValueError):
    """A score source could not be read or converted safely."""


def _workspace_root(workspace: Path) -> Path:
    root = workspace.resolve()
    if not root.is_dir():
        raise ScoreConversionError(f"score workspace does not exist: {root}")
    return root


def _resolve_source(workspace: Path, source_path: str) -> Path:
    root = _workspace_root(workspace)
    candidate = Path(source_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ScoreConversionError("score source must remain inside workspace")
    if not resolved.is_file():
        raise ScoreConversionError(f"score source is not a file: {source_path}")
    return resolved


@dataclass(frozen=True)
class DirectMusicXmlConverter:
    workspace: Path

    def convert(self, source_path: str) -> ConvertedScore:
        source = _resolve_source(self.workspace, source_path)
        if source.suffix.casefold() not in {".xml", ".musicxml"}:
            raise ScoreConversionError("direct MusicXML conversion requires .xml or .musicxml")
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise ScoreConversionError(f"cannot read MusicXML source: {exc}") from exc
        return ConvertedScore(
            musicxml=data,
            converter="direct-musicxml",
            converter_version=None,
        )


@dataclass(frozen=True)
class MuseScoreConverter:
    workspace: Path
    executable: str = "mscore"

    def _version(self) -> str | None:
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        first_line = result.stdout.strip().splitlines()
        return first_line[0] if first_line else None

    def convert(self, source_path: str) -> ConvertedScore:
        root = _workspace_root(self.workspace)
        source = _resolve_source(root, source_path)
        version = self._version()

        try:
            with tempfile.TemporaryDirectory(prefix=".guitarctl-score-", dir=root) as directory:
                output = Path(directory) / "converted.musicxml"
                result = subprocess.run(
                    [self.executable, "-o", str(output), str(source)],
                    check=False,
                    capture_output=True,
                    text=True,
                    shell=False,
                )
                if result.returncode != 0:
                    detail = result.stderr.strip() or f"exit code {result.returncode}"
                    raise ScoreConversionError(f"MuseScore conversion failed: {detail}")
                if not output.is_file():
                    raise ScoreConversionError("MuseScore conversion produced no MusicXML output")
                data = output.read_bytes()
        except ScoreConversionError:
            raise
        except OSError as exc:
            raise ScoreConversionError(f"MuseScore conversion failed: {exc}") from exc

        return ConvertedScore(
            musicxml=data,
            converter="musescore",
            converter_version=version,
        )
