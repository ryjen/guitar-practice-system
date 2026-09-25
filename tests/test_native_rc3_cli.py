from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"
SECTION_FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "sections.musicxml"


class NativeRc3CliTests(unittest.TestCase):
    def _import_fixture(self, workspace: Path) -> None:
        (workspace / "fixture.musicxml").write_bytes(FIXTURE.read_bytes())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = main([
                "--workspace", str(workspace), "score", "import", "fixture.musicxml",
                "--output", "songs/fixture.json",
            ])
        self.assertEqual(0, result)

    def _fake_fluidsynth(self, workspace: Path) -> tuple[Path, Path]:
        executable = workspace / "bin" / "fluidsynth"
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, wave\n"
            "if '--version' in sys.argv:\n"
            "    print('FluidSynth fake 1.0')\n"
            "    raise SystemExit(0)\n"
            "out = sys.argv[sys.argv.index('-F') + 1]\n"
            "with wave.open(out, 'wb') as audio:\n"
            "    audio.setnchannels(2)\n"
            "    audio.setsampwidth(2)\n"
            "    audio.setframerate(44100)\n"
            "    audio.writeframes(b'\\x01' * 400000 * 4)\n"
        )
        executable.chmod(0o755)
        soundfont = workspace / "fixture.sf2"
        soundfont.write_bytes(b"fixture")
        return executable, soundfont

    def test_drums_export_is_native(self) -> None:
        command, consumed = find_command(["drums", "export"])
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(2, consumed)
        self.assertEqual(MigrationState.NATIVE, command.migration)
        self.assertEqual("drums-export", command.native_handler)

    def test_exports_default_full_song_rc3_wav_with_quiet_stdout(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            executable, soundfont = self._fake_fluidsynth(workspace)
            env = {
                "PATH": f"{executable.parent}:{os.environ.get('PATH', '')}",
                "GUITAR_SOUNDFONT": str(soundfont),
            }
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "drums", "export",
                    "songs/fixture.json", "--tempo", "75%", "--target", "boss-rc3",
                ])

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            wav_path = workspace / "generated/rc3/fixture-drums-75pct.wav"
            self.assertTrue(wav_path.is_file())
            self.assertTrue(wav_path.with_suffix(".mid").is_file())
            with wave.open(str(wav_path), "rb") as audio:
                self.assertEqual((2, 2, 44_100), (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()))
                frames = audio.getnframes()
            metadata = json.loads(Path(f"{wav_path}.json").read_text())
            self.assertEqual(round(metadata["duration_seconds"] * 44_100), frames)
            self.assertEqual("boss-rc3", metadata["target"])
            self.assertEqual(["P3"], metadata["selected_track_ids"])

    def test_exports_inclusive_bar_range(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            executable, soundfont = self._fake_fluidsynth(workspace)
            env = {
                "PATH": f"{executable.parent}:{os.environ.get('PATH', '')}",
                "GUITAR_SOUNDFONT": str(soundfont),
            }
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "drums", "export",
                    "songs/fixture.json", "--tempo", "75%", "--target", "boss-rc3",
                    "--bars", "2:2",
                ])

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            wav_path = workspace / "generated/rc3/fixture-drums-75pct-bars2-2.wav"
            metadata = json.loads(Path(f"{wav_path}.json").read_text())
            self.assertEqual([2, 2], metadata["bar_range"])
            with wave.open(str(wav_path), "rb") as audio:
                self.assertEqual(round(metadata["duration_seconds"] * 44_100), audio.getnframes())

    def test_rejects_invalid_bar_ranges(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            executable, soundfont = self._fake_fluidsynth(workspace)
            env = {
                "PATH": f"{executable.parent}:{os.environ.get('PATH', '')}",
                "GUITAR_SOUNDFONT": str(soundfont),
            }
            for value in ("2", "0:1", "2:1", "1:3"):
                with self.subTest(value=value):
                    stderr = io.StringIO()
                    with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                        result = main([
                            "--workspace", str(workspace), "drums", "export",
                            "songs/fixture.json", "--tempo", "100%", "--target", "boss-rc3",
                            "--bars", value,
                        ])
                    self.assertEqual(65, result)
                    self.assertIn("bar", stderr.getvalue().lower())

    def test_exports_named_section_from_rehearsal_mark(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            (workspace / "sections.musicxml").write_bytes(SECTION_FIXTURE.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, main([
                    "--workspace", str(workspace), "score", "import", "sections.musicxml",
                    "--output", "songs/sections.json",
                ]))
            executable, soundfont = self._fake_fluidsynth(workspace)
            env = {
                "PATH": f"{executable.parent}:{os.environ.get('PATH', '')}",
                "GUITAR_SOUNDFONT": str(soundfont),
            }
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "drums", "export",
                    "songs/sections.json", "--tempo", "75%", "--target", "boss-rc3",
                    "--section", "chorus a/b",
                ])
            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            wav_path = workspace / "generated/rc3/sections-drums-75pct-section-Chorus-A-B.wav"
            metadata = json.loads(Path(f"{wav_path}.json").read_text())
            self.assertEqual("Chorus A/B", metadata["section"])
            self.assertEqual([2, 2], metadata["bar_range"])

    def test_explicit_output_and_path_boundary(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            executable, soundfont = self._fake_fluidsynth(workspace)
            env = {"PATH": f"{executable.parent}:{os.environ.get('PATH', '')}", "GUITAR_SOUNDFONT": str(soundfont)}
            with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = main([
                    "--workspace", str(workspace), "drums", "export", "songs/fixture.json",
                    "--tempo", "100%", "--target", "boss-rc3", "--output", "practice/drums.wav",
                ])
            self.assertEqual(0, result)
            self.assertTrue((workspace / "practice/drums.wav").is_file())

            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "drums", "export", "songs/fixture.json",
                    "--tempo", "100%", "--target", "boss-rc3", "--output", "../outside.wav",
                ])
            self.assertNotEqual(0, result)
            self.assertIn("workspace-relative", stderr.getvalue())

            stderr = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "drums", "export", "songs/fixture.json",
                    "--tempo", "100%", "--target", "boss-rc3", "--output", "practice/drums.mp3",
                ])
            self.assertNotEqual(0, result)
            self.assertIn(".wav", stderr.getvalue())

    def test_missing_soundfont_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            with mock.patch.dict(os.environ, {"GUITAR_SOUNDFONT": ""}, clear=False), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = main([
                    "--workspace", str(workspace), "drums", "export", "songs/fixture.json",
                    "--tempo", "100%", "--target", "boss-rc3",
                ])
            self.assertEqual(69, result)


if __name__ == "__main__":
    unittest.main()
