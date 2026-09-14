"""Bounded local audio-rendering adapters."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from guitar_practice.application.ports import AudioRenderProfile, RenderedAudio


class AudioRenderError(RuntimeError):
    """Raised when a local audio renderer cannot produce the requested artifact."""


class FluidSynthAudioRenderer:
    """Render MIDI bytes to WAV with one explicit SoundFont."""

    def __init__(
        self,
        workspace: Path,
        *,
        soundfont: Path,
        executable: str = "fluidsynth",
    ) -> None:
        self.workspace = workspace.resolve()
        self.soundfont = soundfont.resolve()
        self.executable = executable

    def render(self, midi: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        self._validate(profile)
        version = self._version()

        self.workspace.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=self.workspace,
            prefix=".guitar-audio-",
        ) as directory:
            temp = Path(directory)
            midi_path = temp / "source.mid"
            wav_path = temp / "render.wav"
            midi_path.write_bytes(midi)

            argv = [
                self.executable,
                "-ni",
                "-F",
                str(wav_path),
                "-T",
                "wav",
                "-O",
                profile.sample_format,
                "-r",
                str(profile.sample_rate),
                "-L",
                "1",
                str(self.soundfont),
                str(midi_path),
            ]
            result = self._run(argv, timeout=60)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "unknown renderer failure"
                raise AudioRenderError(f"FluidSynth render failed: {detail}")
            if not wav_path.is_file():
                raise AudioRenderError("FluidSynth render did not produce a WAV file")
            wav = wav_path.read_bytes()

        return RenderedAudio(
            wav=wav,
            renderer="fluidsynth",
            renderer_version=version,
            soundfont=str(self.soundfont),
        )

    def _validate(self, profile: AudioRenderProfile) -> None:
        if not self.soundfont.is_file():
            raise AudioRenderError(f"SoundFont not found: {self.soundfont}")
        if profile.channels != 2:
            raise AudioRenderError("FluidSynth adapter currently requires stereo output")
        if profile.sample_format != "s16":
            raise AudioRenderError("FluidSynth adapter currently requires s16 PCM output")

    def _version(self) -> str:
        result = self._run([self.executable, "--version"], timeout=10)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "version query failed"
            raise AudioRenderError(f"FluidSynth version query failed: {detail}")
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
            raise AudioRenderError(f"FluidSynth invocation failed: {exc}") from exc
