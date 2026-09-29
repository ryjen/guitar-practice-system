"""Bounded local MIDI playback adapters."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from guitar_practice.application.ports import PlaybackResult


class MidiPlaybackError(RuntimeError):
    """Raised when a local MIDI player cannot complete playback safely."""


class FluidSynthMidiPlayer:
    """Play MIDI through FluidSynth using one explicit SoundFont."""

    def __init__(
        self,
        workspace: Path,
        *,
        soundfont: Path | None,
        executable: str = "fluidsynth",
        playback_timeout_seconds: int = 600,
    ) -> None:
        self.workspace = workspace.resolve()
        self.soundfont = soundfont.resolve() if soundfont is not None else None
        self.executable = executable
        self.playback_timeout_seconds = playback_timeout_seconds

    def play(self, data: bytes) -> PlaybackResult:
        if self.soundfont is None:
            raise MidiPlaybackError(
                "SoundFont is required; use --soundfont or GUITAR_SOUNDFONT"
            )
        if not self.soundfont.is_file():
            raise MidiPlaybackError(f"SoundFont not found: {self.soundfont}")
        version = self._version()

        self.workspace.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(
                dir=self.workspace,
                prefix=".guitar-playback-",
            ) as directory:
                midi_path = Path(directory) / "playback.mid"
                midi_path.write_bytes(data)
                result = subprocess.run(
                    [
                        self.executable,
                        "-ni",
                        str(self.soundfont),
                        str(midi_path),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    shell=False,
                    timeout=self.playback_timeout_seconds,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MidiPlaybackError(f"FluidSynth playback failed: {exc}") from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown playback failure"
            raise MidiPlaybackError(f"FluidSynth playback failed: {detail}")

        return PlaybackResult(
            player="fluidsynth",
            player_version=version,
            soundfont=str(self.soundfont),
        )

    def _version(self) -> str | None:
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        value = result.stdout.strip() or result.stderr.strip()
        return value or None
