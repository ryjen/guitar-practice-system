from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guitar_practice.adapters.midi_playback import FluidSynthMidiPlayer, MidiPlaybackError


class MidiPlaybackAdapterTests(unittest.TestCase):
    def test_fluidsynth_player_uses_bounded_argv_and_returns_provenance(self) -> None:
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
                self.assertTrue(midi_path.is_file())
                self.assertTrue(midi_path.is_relative_to(workspace))
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            player = FluidSynthMidiPlayer(
                workspace,
                executable="fluidsynth-test",
                soundfont=soundfont,
            )
            with mock.patch(
                "guitar_practice.adapters.midi_playback.subprocess.run",
                side_effect=fake_run,
            ):
                result = player.play(b"MThd-midi")

        self.assertEqual(["fluidsynth-test", "--version"], calls[0][0])
        self.assertEqual("fluidsynth-test", calls[1][0][0])
        self.assertEqual(["-ni"], calls[1][0][1:2])
        self.assertEqual(str(soundfont.resolve()), calls[1][0][-2])
        self.assertFalse(calls[1][1]["shell"])
        self.assertEqual(600, calls[1][1]["timeout"])
        self.assertEqual("fluidsynth", result.player)
        self.assertIn("2.5.6", result.player_version or "")
        self.assertEqual(str(soundfont.resolve()), result.soundfont)

    def test_player_failure_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            soundfont = workspace / "FluidR3.sf2"
            soundfont.write_bytes(b"soundfont")
            player = FluidSynthMidiPlayer(workspace, soundfont=soundfont)

            responses = [
                subprocess.CompletedProcess(["fluidsynth", "--version"], 0, stdout="FluidSynth 2\n", stderr=""),
                subprocess.CompletedProcess(["fluidsynth"], 1, stdout="", stderr="no audio device"),
            ]
            with mock.patch(
                "guitar_practice.adapters.midi_playback.subprocess.run",
                side_effect=responses,
            ):
                with self.assertRaisesRegex(MidiPlaybackError, "no audio device"):
                    player.play(b"MThd-midi")

    def test_missing_soundfont_fails_before_process_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            player = FluidSynthMidiPlayer(workspace, soundfont=workspace / "missing.sf2")
            with mock.patch("guitar_practice.adapters.midi_playback.subprocess.run") as run:
                with self.assertRaisesRegex(MidiPlaybackError, "SoundFont not found"):
                    player.play(b"MThd-midi")
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
