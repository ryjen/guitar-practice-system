from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain import midi
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class NativeMidiCliTests(unittest.TestCase):
    def test_midi_render_commands_are_native_but_exercise_generator_remains_legacy(self) -> None:
        for tokens in (["midi", "generate"], ["midi", "validate"]):
            command, consumed = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(len(tokens), consumed)
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

        exercises, _ = find_command(["midi", "generate-exercises"])
        self.assertIsNotNone(exercises)
        assert exercises is not None
        self.assertEqual(MigrationState.LEGACY, exercises.migration)

    def test_generate_and_validate_run_without_repository_scripts(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "backing-tracks"
                / "slide-slow-blues"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        expected_bytes = midi.render(manifest)
        expected_report = midi.validate_rendered(manifest, expected_bytes)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            generate_stdout = io.StringIO()
            generate_stderr = io.StringIO()
            with contextlib.redirect_stdout(generate_stdout), contextlib.redirect_stderr(
                generate_stderr
            ):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "midi",
                        "generate",
                        "manifest.json",
                        "output.mid",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(expected_report, json.loads(generate_stdout.getvalue()))
            self.assertEqual("", generate_stderr.getvalue())
            self.assertEqual(expected_bytes, (workspace / "output.mid").read_bytes())
            self.assertFalse((workspace / "scripts").exists())

            validate_stdout = io.StringIO()
            validate_stderr = io.StringIO()
            with contextlib.redirect_stdout(validate_stdout), contextlib.redirect_stderr(
                validate_stderr
            ):
                validate_result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "midi",
                        "validate",
                        "manifest.json",
                        "output.mid",
                    ]
                )

            self.assertEqual(0, validate_result)
            self.assertEqual(expected_report, json.loads(validate_stdout.getvalue()))
            self.assertEqual("", validate_stderr.getvalue())
            self.assertEqual(
                hashlib.sha256(expected_bytes).hexdigest(),
                hashlib.sha256((workspace / "output.mid").read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
