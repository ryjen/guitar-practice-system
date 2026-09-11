from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class NativeGenerationCliTests(unittest.TestCase):
    def test_all_musical_generation_commands_are_native(self) -> None:
        for tokens in (
            ["backing", "generate"],
            ["progression", "generate", "request.json"],
            ["midi", "generate-exercises"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)

    def test_backing_generate_runs_without_repository_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest_dir = workspace / "backing-tracks" / "slide-slow-blues"
            catalog_dir = workspace / "catalogs" / "grooves"
            manifest_dir.mkdir(parents=True)
            catalog_dir.mkdir(parents=True)
            shutil.copyfile(
                ROOT / "backing-tracks" / "slide-slow-blues" / "manifest.json",
                manifest_dir / "manifest.json",
            )
            shutil.copyfile(
                ROOT / "catalogs" / "grooves" / "catalog.json",
                catalog_dir / "catalog.json",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--workspace", str(workspace), "backing", "generate"])

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(1, len(payload))
            output = workspace / payload[0]["output"]
            self.assertTrue(output.is_file())
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_progression_generate_runs_without_repository_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "catalogs" / "grooves").mkdir(parents=True)
            (workspace / "catalogs" / "progressions").mkdir(parents=True)
            shutil.copyfile(
                ROOT / "catalogs" / "grooves" / "catalog.json",
                workspace / "catalogs" / "grooves" / "catalog.json",
            )
            shutil.copyfile(
                ROOT / "catalogs" / "progressions" / "catalog.json",
                workspace / "catalogs" / "progressions" / "catalog.json",
            )
            shutil.copyfile(
                ROOT / "examples" / "backing-tracks" / "funk-wah-request.json",
                workspace / "request.json",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "progression",
                        "generate",
                        "request.json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual([75, 82, 96], [stage["tempo_bpm"] for stage in payload["stages"]])
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_midi_generate_exercises_runs_without_repository_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "midi").mkdir()
            shutil.copyfile(
                ROOT / "midi" / "exercises.json",
                workspace / "midi" / "exercises.json",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    ["--workspace", str(workspace), "midi", "generate-exercises"]
                )

            self.assertEqual(0, result)
            lines = [line for line in stdout.getvalue().splitlines() if line]
            self.assertGreaterEqual(len(lines), 5)
            for line in lines:
                self.assertTrue(line.startswith("wrote generated/midi/"))
                output = workspace / line.removeprefix("wrote ")
                self.assertTrue(output.is_file())
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
