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


class NativeGrooveCliTests(unittest.TestCase):
    def test_groove_catalog_commands_are_native(self) -> None:
        for tokens in (
            ["groove", "validate"],
            ["groove", "list"],
            ["groove", "show", "blues-shuffle"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)

    def test_groove_cli_runs_without_repository_scripts(self) -> None:
        source = json.loads(
            (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "grooves.json").write_text(
                json.dumps(source),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "groove",
                        "show",
                        "blues-shuffle",
                        "--catalog",
                        "grooves.json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("blues-shuffle", payload["id"])
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
