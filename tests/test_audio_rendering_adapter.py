from __future__ import annotations

import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from guitar_practice.adapters.audio_rendering import AudioRenderError, FluidSynthAudioRenderer
from guitar_practice.application.ports import AudioRenderProfile


def _write_stereo_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(44_100)
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
                    return subprocess.CompletedProcess(argv, 0, stdout="FluidSynth 2.5.6\n", stderr="")
                midi_path = Path(argv[-1])
                wav_path = Path(argv[argv.index("-F") + 1])
                self.assertTrue(midi_path.is_relative_to(workspace))
                self.assertTrue(wav_path.is_relative_to(workspace))
                _write_stereo_wav(wav_path)
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            renderer = FluidSynthAudioRenderer(workspace, executable="fluidsynth-test", soundfont=soundfont)
            with mock.patch("guitar_practice.adapters.audio_rendering.subprocess.run", side_effect=fake_run):
                rendered = renderer.render(
                    b"MThd-midi",
                    AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16"),
                )

        self.assertEqual(["fluidsynth-test", "--version"], calls[0][0])
        self.assertFalse(calls[0][1]["shell"])
        self.assertEqual(10, calls[0][1]["timeout"])
        self.assertFalse(calls[1][1]["shell"])
        self.assertEqual(60, calls[1][1]["timeout"])
        self.assertEqual(str(soundfont.resolve()), calls[1][0][-2])
        self.assertEqual("fluidsynth", rendered.renderer)
        self.assertIn("2.5.6", rendered.renderer_version or "")

    def test_missing_soundfont_fails_before_process_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            renderer = FluidSynthAudioRenderer(workspace, soundfont=workspace / "missing.sf2")
            with mock.patch("guitar_practice.adapters.audio_rendering.subprocess.run") as run:
                with self.assertRaises(AudioRenderError):
                    renderer.render(
                        b"MThd-midi",
                        AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16"),
                    )
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
