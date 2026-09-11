from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class NativeProgressionCliTests(unittest.TestCase):
    def test_catalog_commands_are_native_but_generation_remains_legacy(self) -> None:
        for tokens in (
            ["progression", "validate"],
            ["progression", "list"],
            ["progression", "show"],
            ["progression", "resolve"],
            ["progression", "fourths"],
        ):
            command, consumed = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(len(tokens), consumed)
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

        generation, _ = find_command(["progression", "generate"])
        self.assertIsNotNone(generation)
        assert generation is not None
        self.assertEqual(MigrationState.LEGACY, generation.migration)

    def test_progression_cli_runs_without_repository_scripts(self) -> None:
        catalog = json.loads(
            (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            catalog_path = workspace / "catalogs" / "progressions" / "catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "progression",
                        "resolve",
                        "jazz-blues-12",
                        "C",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(
                ["C7", "C7", "F7", "F7"],
                payload["chords"][:4],
            )
            self.assertEqual(
                ["A7", "D7", "G7", "C7"],
                payload["chords"][-4:],
            )
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_fourths_cli_preserves_deterministic_shape(self) -> None:
        catalog = json.loads(
            (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            catalog_path = workspace / "catalogs" / "progressions" / "catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "progression",
                        "fourths",
                        "progression-jazz-major-ii-v-i",
                        "--start-key",
                        "A",
                        "--count",
                        "4",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(
                ["A", "D", "G", "C"],
                [item["key_signature"] for item in payload["positions"]],
            )


if __name__ == "__main__":
    unittest.main()
