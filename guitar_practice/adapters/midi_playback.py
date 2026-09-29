"""Bounded local MIDI playback adapters."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from guitar_practice.application.ports import PlayedMidi


class MidiPlaybackError(RuntimeError):
    """Raised when a local MIDI player cannot audition an artifact."""


class FluidSynthMidiPlayer:
    """Play MIDI through FluidSynth using one explicit SoundFont."""

    def __init__(
        self,
        workspace: Path,
        *,
        soundfont: Path | None,
        executable: str = "fluidsynth",
        timeout_seconds: int = 300,
    ) -> None:
        self.workspace = workspace.resolve()
        self.soundfont = soundfont.resolve() if soundfont is not None else None
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def play(self, midi: bytes) -> PlayedMidi:
        if self.soundfont is None:
            raise MidiPlaybackError(
                "SoundFont is required for playback; use --soundfont or GUITAR_SOUNDFONT"
            )
        if not self.soundfont.is_file():
            raise MidiPlaybackError(f"SoundFont not found: {self.soundfont}")
        version = self._version()

        self.workspace.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=self.workspace,
            prefix=".guitar-midi-play-",
        ) as directory:
            midi_path = Path(directory) / "playback.mid"
            midi_path.write_bytes(midi)
            result = self._run(
                [
                    self.executable,
                    "-ni",
                    str(self.soundfont),
                    str(midi_path),
                ],
                timeout=self.timeout_seconds,
            )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown player failure"
            raise MidiPlaybackError(f"FluidSynth playback failed: {detail}")

        return PlayedMidi(
            player="fluidsynth",
            player_version=version,
            soundfont=str(self.soundfont),
        )

    def _version(self) -> str:
        result = self._run([self.executable, "--version"], timeout=10)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "version query failed"
            raise MidiPlaybackError(f"FluidSynth version query failed: {detail}")
        return result.stdout.strip() or result.stderr.strip()

    def _run(
        self,
        argv: list[str],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MidiPlaybackError(f"FluidSynth invocation failed: {exc}") from exc
