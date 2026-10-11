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
FIXTURE = ROOT / "contracts" / "dsp" / "fixtures" / "jazz-blues-preset-v1.json"


class NativeDspPresetCliTests(unittest.TestCase):
    def test_dsp_preset_commands_are_native(self) -> None:
        for tokens in (
            ["dsp", "preset", "validate"],
            ["dsp", "preset", "canonicalize"],
        ):
            with self.subTest(tokens=tokens):
                command, consumed = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(len(tokens), consumed)
                self.assertEqual(MigrationState.NATIVE, command.migration)
                self.assertIsNotNone(command.native_handler)
                self.assertIsNone(command.legacy)

    def test_validate_runs_in_isolated_workspace_without_dsp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            shutil.copyfile(FIXTURE, workspace / "preset.json")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "validate",
                        "preset.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {
                    "preset": "jazz-blues",
                    "schema": "guitar-dsp.preset",
                    "status": "valid",
                    "version": 1,
                },
                json.loads(stdout.getvalue()),
            )
            self.assertFalse((workspace / "dsp").exists())
            self.assertFalse((workspace / "scripts").exists())

    def test_canonicalize_emits_fixture_bytes_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            document = json.loads(FIXTURE.read_text(encoding="utf-8"))
            (workspace / "preset.json").write_text(
                json.dumps(document, indent=2),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "canonicalize",
                        "preset.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                FIXTURE.read_text(encoding="utf-8"),
                stdout.getvalue(),
            )

    def test_invalid_preset_is_data_error_with_no_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            document = json.loads(FIXTURE.read_text(encoding="utf-8"))
            document["parameters"]["delay.feedback_milli"] = 951
            (workspace / "preset.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "validate",
                        "preset.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("delay.feedback_milli", stderr.getvalue())

    def test_invalid_utf8_is_data_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "preset.json").write_bytes(b"\\xff\\xfe")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "validate",
                        "preset.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertTrue(stderr.getvalue().startswith("guitarctl: "))

    def test_document_path_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        directory,
                        "dsp",
                        "preset",
                        "validate",
                        "../preset.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("workspace-relative", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
