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
SECTION_FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "sections.musicxml"


class NativeStemCliTests(unittest.TestCase):
    def _import_fixture(self, workspace: Path) -> None:
        (workspace / "fixture.musicxml").write_bytes(FIXTURE.read_bytes())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = main([
                "--workspace", str(workspace), "score", "import", "fixture.musicxml",
                "--output", "songs/fixture.json",
            ])
        self.assertEqual(0, result)

    def test_backing_render_is_native(self) -> None:
        command, consumed = find_command(["backing", "render"])
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(2, consumed)
        self.assertEqual(MigrationState.NATIVE, command.migration)
        self.assertEqual("backing-render", command.native_handler)
        self.assertIsNone(command.legacy)

    def test_renders_75_percent_backing_with_quiet_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/fixture.json", "--tempo", "75%",
                    "--output", "practice/backing.mid",
                ])

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            self.assertTrue((workspace / "practice" / "backing.mid").is_file())
            metadata = json.loads(
                (workspace / "practice" / "backing.mid.json").read_text(encoding="utf-8")
            )
            self.assertEqual(0.75, metadata["tempo_factor"])
            self.assertEqual(["P2", "P3", "P4"], metadata["selected_track_ids"])
            self.assertEqual(["P1"], metadata["excluded_track_ids"])

    def test_renders_inclusive_bar_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/fixture.json", "--tempo", "75%", "--bars", "2:2",
                    "--output", "practice/focused.mid",
                ])
            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            metadata = json.loads(
                (workspace / "practice" / "focused.mid.json").read_text(encoding="utf-8")
            )
            self.assertEqual([2, 2], metadata["bar_range"])

    def test_renders_named_section_from_rehearsal_mark(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "sections.musicxml").write_bytes(SECTION_FIXTURE.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, main([
                    "--workspace", str(workspace), "score", "import", "sections.musicxml",
                    "--output", "songs/sections.json",
                ]))
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/sections.json", "--tempo", "75%", "--section", "chorus a/b",
                    "--output", "practice/chorus.mid",
                ])
            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            metadata = json.loads((workspace / "practice/chorus.mid.json").read_text())
            self.assertEqual("Chorus A/B", metadata["section"])
            self.assertEqual([2, 2], metadata["bar_range"])

    def test_rejects_bars_and_section_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/fixture.json", "--tempo", "75%", "--bars", "1:1",
                    "--section", "Verse", "--output", "practice/focused.mid",
                ])
            self.assertEqual(65, result)
            self.assertIn("either", stderr.getvalue().lower())

    def test_include_and_exclude_track_flags_are_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/fixture.json", "--tempo", "100%",
                    "--include-track", "P1", "--exclude-track", "P4",
                    "--output", "practice/backing.mid",
                ])

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            metadata = json.loads(
                (workspace / "practice" / "backing.mid.json").read_text(encoding="utf-8")
            )
            self.assertEqual(["P1"], metadata["explicit_include_track_ids"])
            self.assertEqual(["P4"], metadata["explicit_exclude_track_ids"])
            self.assertEqual(["P1", "P2", "P3"], metadata["selected_track_ids"])

    def test_rejects_score_and_output_path_escape(self) -> None:
        for score_path, output_path in (
            ("../outside.json", "practice/backing.mid"),
            ("songs/fixture.json", "../outside.mid"),
        ):
            with self.subTest(score=score_path, output=output_path):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = Path(directory)
                    self._import_fixture(workspace)
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        result = main([
                            "--workspace", str(workspace), "backing", "render",
                            score_path, "--tempo", "75%", "--output", output_path,
                        ])
                    self.assertNotEqual(0, result)
                    self.assertIn("workspace-relative", stderr.getvalue())
    def test_rejects_invalid_tempo_specification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._import_fixture(workspace)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main([
                    "--workspace", str(workspace), "backing", "render",
                    "songs/fixture.json", "--tempo", "0%",
                    "--output", "practice/backing.mid",
                ])
            self.assertNotEqual(0, result)
            self.assertIn("tempo", stderr.getvalue().lower())
            self.assertFalse((workspace / "practice" / "backing.mid").exists())


if __name__ == "__main__":
    unittest.main()
