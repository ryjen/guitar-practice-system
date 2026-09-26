from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain import score
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "musicxml" / "multitrack.musicxml"


class NativeScoreCliTests(unittest.TestCase):
    def test_score_commands_are_native(self) -> None:
        for tokens in (
            ["score", "import", "song.musicxml"],
            ["score", "tracks", "song.score.json"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)

    def test_import_writes_canonical_score_ir_and_tracks_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            shutil.copyfile(FIXTURE, workspace / "song.musicxml")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "song.musicxml",
                        "--output",
                        "generated/song.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            summary = json.loads(stdout.getvalue())
            self.assertEqual("song", summary["id"])
            self.assertEqual(4, summary["parts"])

            output = workspace / "generated" / "song.score.json"
            document = score.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("guitar-practice.score", document["schema"])
            self.assertNotIn("song", document)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "tracks",
                        "generated/song.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            tracks = json.loads(stdout.getvalue())
            self.assertEqual("song", tracks["id"])
            self.assertEqual(
                ["guitar", "bass", "drums", "keys"],
                [track["role"] for track in tracks["tracks"]],
            )
            self.assertFalse((workspace / "scripts").exists())

    def test_import_rejects_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "../song.musicxml",
                        "--output",
                        "song.score.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertIn("workspace-relative", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
