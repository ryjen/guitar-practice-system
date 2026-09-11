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


class NativeBackingCliTests(unittest.TestCase):
    def _workspace(self, directory: str) -> Path:
        workspace = Path(directory)
        groove_target = workspace / "catalogs" / "grooves" / "catalog.json"
        progression_target = workspace / "catalogs" / "progressions" / "catalog.json"
        request_target = workspace / "request.json"
        groove_target.parent.mkdir(parents=True)
        progression_target.parent.mkdir(parents=True)
        groove_target.write_text(
            (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        progression_target.write_text(
            (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        request_target.write_text(
            (ROOT / "examples" / "backing-tracks" / "funk-wah-request.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return workspace

    def test_backing_resolve_is_native_but_bulk_generate_remains_legacy(self) -> None:
        resolve, _ = find_command(["backing", "resolve", "request.json"])
        generate, _ = find_command(["backing", "generate"])
        self.assertIsNotNone(resolve)
        self.assertIsNotNone(generate)
        assert resolve is not None and generate is not None
        self.assertEqual(MigrationState.NATIVE, resolve.migration)
        self.assertEqual(MigrationState.LEGACY, generate.migration)

    def test_backing_resolve_runs_without_repository_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "resolve",
                        "request.json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("funk-wah-pocket-em-96", payload["id"])
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_backing_resolve_output_preserves_quiet_stdout_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "resolve",
                        "request.json",
                        "--output",
                        "resolved/spec.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            payload = json.loads((workspace / "resolved" / "spec.json").read_text())
            self.assertEqual("funk-wah-pocket-em-96", payload["id"])


if __name__ == "__main__":
    unittest.main()
