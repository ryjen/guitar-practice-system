from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"


class NativeScoreCliTests(unittest.TestCase):
    def test_score_commands_are_native(self) -> None:
        for tokens in (["score", "import"], ["score", "tracks"]):
            command, consumed = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(len(tokens), consumed)
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

    def test_musicxml_import_and_track_inspection_run_without_musescore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "fixture.musicxml").write_bytes(FIXTURE.read_bytes())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "fixture.musicxml",
                        "--output",
                        "songs/fixture.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            summary = json.loads(stdout.getvalue())
            self.assertEqual("Fixture Song", summary["title"])
            self.assertEqual("songs/fixture.json", summary["output"])
            self.assertEqual(4, summary["tracks"])
            self.assertTrue((workspace / "songs" / "fixture.json").is_file())

            tracks_stdout = io.StringIO()
            tracks_stderr = io.StringIO()
            with contextlib.redirect_stdout(tracks_stdout), contextlib.redirect_stderr(tracks_stderr):
                tracks_result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "tracks",
                        "songs/fixture.json",
                    ]
                )

            self.assertEqual(0, tracks_result)
            self.assertEqual("", tracks_stderr.getvalue())
            inspection = json.loads(tracks_stdout.getvalue())
            self.assertEqual("Fixture Song", inspection["title"])
            self.assertEqual(
                ["guitar", "bass", "drums", "keys"],
                [track["role"] for track in inspection["tracks"]],
            )
            self.assertEqual("instrument", inspection["tracks"][0]["classification_source"])
            self.assertTrue(inspection["tracks"][2]["is_percussion"])

    def test_score_import_rejects_output_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "fixture.musicxml").write_bytes(FIXTURE.read_bytes())
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "fixture.musicxml",
                        "--output",
                        "../escape.json",
                    ]
                )
            self.assertNotEqual(0, result)
            self.assertIn("workspace-relative", stderr.getvalue())
            self.assertFalse((workspace.parent / "escape.json").exists())

    def test_score_tracks_rejects_document_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            external = Path(outside) / "song.json"
            external.write_text("{}", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "tracks",
                        str(external),
                    ]
                )
            self.assertNotEqual(0, result)
            self.assertIn("workspace-relative", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
