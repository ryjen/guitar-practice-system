from __future__ import annotations

import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from guitar_practice.adapters.audio_rendering import (
    AudioRenderError,
    FluidSynthAudioRenderer,
)
from guitar_practice.application.ports import AudioRenderProfile


def _write_stereo_wav(path: Path, *, sample_rate: int = 44_100) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00\x00\x00\x00" * 8)


class AudioRenderingAdapterTests(unittest.TestCase):
    def test_fluidsynth_uses_bounded_argv_and_records_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            soundfont = workspace / "FluidR3.sf2"
            soundfont.write_bytes(b"soundfont")
            calls: list[tuple[list[str], dict[str, object]]] = []

            def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append((argv, kwargs))
                if argv[-1] == "--version":
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        stdout="FluidSynth runtime version 2.5.6\n",
                        stderr="",
                    )
                midi_path = Path(argv[-1])
                wav_path = Path(argv[argv.index("-F") + 1])
                self.assertTrue(midi_path.is_relative_to(workspace))
                self.assertTrue(wav_path.is_relative_to(workspace))
                self.assertEqual(b"MThd-midi", midi_path.read_bytes())
                _write_stereo_wav(wav_path)
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            renderer = FluidSynthAudioRenderer(
                workspace,
                executable="fluidsynth-test",
                soundfont=soundfont,
            )
            with mock.patch(
                "guitar_practice.adapters.audio_rendering.subprocess.run",
                side_effect=fake_run,
            ):
                rendered = renderer.render(
                    b"MThd-midi",
                    AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16"),
                )

        version_argv, version_kwargs = calls[0]
        render_argv, render_kwargs = calls[1]
        self.assertEqual(["fluidsynth-test", "--version"], version_argv)
        self.assertEqual("fluidsynth-test", render_argv[0])
        self.assertIn("-ni", render_argv)
        self.assertEqual("wav", render_argv[render_argv.index("-T") + 1])
        self.assertEqual("s16", render_argv[render_argv.index("-O") + 1])
        self.assertEqual("44100", render_argv[render_argv.index("-r") + 1])
        self.assertEqual("1", render_argv[render_argv.index("-L") + 1])
        self.assertEqual(str(soundfont.resolve()), render_argv[-2])
        self.assertFalse(render_kwargs["shell"])
        self.assertTrue(render_kwargs["capture_output"])
        self.assertEqual(60, render_kwargs["timeout"])
        self.assertFalse(version_kwargs["shell"])
        self.assertEqual("fluidsynth", rendered.renderer)
        self.assertIn("2.5.6", rendered.renderer_version or "")
        self.assertEqual(str(soundfont.resolve()), rendered.soundfont)
        self.assertTrue(rendered.wav.startswith(b"RIFF"))

    def test_fluidsynth_failure_is_distinct_and_does_not_return_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            soundfont = workspace / "fixture.sf2"
            soundfont.write_bytes(b"soundfont")

            def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                if argv[-1] == "--version":
                    return subprocess.CompletedProcess(argv, 0, stdout="FluidSynth 2.5.6", stderr="")
                return subprocess.CompletedProcess(argv, 7, stdout="", stderr="render failed")

            renderer = FluidSynthAudioRenderer(workspace, soundfont=soundfont)
            with mock.patch(
                "guitar_practice.adapters.audio_rendering.subprocess.run",
                side_effect=fake_run,
            ):
                with self.assertRaisesRegex(AudioRenderError, "render failed"):
                    renderer.render(b"MThd-midi", AudioRenderProfile())

    def test_rejects_missing_soundfont_and_unsupported_profile_before_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            missing = workspace / "missing.sf2"
            renderer = FluidSynthAudioRenderer(workspace, soundfont=missing)
            with mock.patch("guitar_practice.adapters.audio_rendering.subprocess.run") as run:
                with self.assertRaises(AudioRenderError):
                    renderer.render(b"MThd-midi", AudioRenderProfile())
                run.assert_not_called()

            soundfont = workspace / "fixture.sf2"
            soundfont.write_bytes(b"soundfont")
            renderer = FluidSynthAudioRenderer(workspace, soundfont=soundfont)
            with mock.patch("guitar_practice.adapters.audio_rendering.subprocess.run") as run:
                with self.assertRaises(AudioRenderError):
                    renderer.render(
                        b"MThd-midi",
                        AudioRenderProfile(sample_rate=48_000, channels=1, sample_format="float"),
                    )
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
