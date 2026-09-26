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
            ["score", "init", "--title", "Blue Thing"],
            ["score", "import", "song.musicxml"],
            ["score", "show", "song.score.json"],
            ["score", "tracks", "song.score.json"],
            ["score", "validate", "song.score.json"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)


    def test_init_emits_canonical_score_without_ambient_state(self) -> None:
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
                        "init",
                        "--title",
                        "Blue Thing",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            document = score.loads(stdout.getvalue())
            self.assertEqual("blue-thing", document["id"])
            self.assertEqual("Blue Thing", document["metadata"]["title"])
            self.assertEqual([{"number": 1}], document["bars"])
            self.assertEqual(
                [{"bar": 1, "beats": 4, "beat_unit": 4}],
                document["meter_map"],
            )
            self.assertEqual([], document["tempo_map"])
            self.assertEqual([], document["parts"])
            self.assertEqual([], list(workspace.iterdir()))

    def test_init_explicit_output_show_and_validate(self) -> None:
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
                        "init",
                        "--title",
                        "Blue Thing",
                        "--output",
                        "scores/blue.score.json",
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"id": "blue-thing", "output": "scores/blue.score.json", "title": "Blue Thing"},
                json.loads(stdout.getvalue()),
            )

            path = workspace / "scores" / "blue.score.json"
            expected = score.loads(path.read_text(encoding="utf-8"))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--workspace", str(workspace), "score", "show", "scores/blue.score.json"])
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(expected, score.loads(stdout.getvalue()))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--workspace", str(workspace), "score", "validate", "scores/blue.score.json"])
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"id": "blue-thing", "schema": score.SCHEMA_ID, "valid": True, "version": score.SCHEMA_VERSION},
                json.loads(stdout.getvalue()),
            )

    def test_validate_rejects_invalid_score_and_never_infers_current_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "current.score.json").write_text("{}\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                missing_target = main(["--workspace", str(workspace), "score", "validate"])
            self.assertEqual(2, missing_target)
            self.assertEqual("", stdout.getvalue())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                invalid = main(
                    ["--workspace", str(workspace), "score", "validate", "current.score.json"]
                )
            self.assertEqual(65, invalid)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("missing required fields", stderr.getvalue())

    def test_song_namespace_is_not_registered(self) -> None:
        command, consumed = find_command(["song", "show", "song.score.json"])
        self.assertIsNone(command)
        self.assertEqual(0, consumed)

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
            self.assertEqual(
                {"program": 29, "channel": 1},
                tracks["tracks"][0]["midi"],
            )
            self.assertEqual(
                {"channel": 10, "percussion": True},
                tracks["tracks"][2]["midi"],
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
