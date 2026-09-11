from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import (
    COMMANDS,
    COMPATIBILITY_SHIMS,
    INTERNAL_LIBRARY_SCRIPTS,
    MigrationState,
    command_paths,
    find_command,
    registered_legacy_scripts,
)
from guitar_practice.interfaces.cli.main import main


class CommandRegistryTests(unittest.TestCase):
    def test_command_paths_are_unique(self) -> None:
        paths = tuple(command_paths())
        self.assertEqual(len(paths), len(set(paths)))

    def test_expected_capability_roots_exist(self) -> None:
        roots = {path[0] for path in command_paths()}
        self.assertTrue(
            {
                "artifact",
                "assess",
                "backing",
                "discover",
                "evidence",
                "export",
                "groove",
                "midi",
                "progression",
                "schedule",
                "session",
                "validate",
            }
            <= roots
        )

    def test_each_command_has_exactly_one_implementation(self) -> None:
        for command in COMMANDS:
            self.assertNotEqual(bool(command.native_handler), bool(command.legacy), command.path)

    def test_longest_prefix_resolves_nested_compatibility_command(self) -> None:
        command, consumed = find_command(
            ["schedule", "legacy", "propose", "snapshot.json"]
        )
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(("schedule", "legacy", "propose"), command.path)
        self.assertEqual(MigrationState.DEPRECATED, command.migration)
        self.assertEqual(3, consumed)

    def test_every_script_is_registered_classified_or_a_compatibility_shim(self) -> None:
        expected = {
            "scripts/adaptive_session.py",
            "scripts/assessment_core.py",
            "scripts/backing_track_engine.py",
            "scripts/bass_engine.py",
            "scripts/build_practice_artifacts.py",
            "scripts/check_public_boundary.py",
            "scripts/discovery_catalog.py",
            "scripts/evidence_feedback.py",
            "scripts/export_practice_data.py",
            "scripts/generate_backing_tracks.py",
            "scripts/generate_practice_progression.py",
            "scripts/groove_catalog.py",
            "scripts/groove_engine.py",
            "scripts/midi_workflow.py",
            "scripts/progression_catalog.py",
            "scripts/resolve_backing_track_request.py",
            "scripts/scheduling.py",
            "scripts/scheduling_v2.py",
            "scripts/timing.py",
            "scripts/validate_repo.py",
            "tools/generate_midi.py",
        }
        classified = (
            registered_legacy_scripts() | INTERNAL_LIBRARY_SCRIPTS | COMPATIBILITY_SHIMS
        )
        self.assertEqual(expected, classified)


class CliRuntimeTests(unittest.TestCase):
    def test_missing_command_is_usage_error(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(2, main([]))
        self.assertIn("Stable commands", stderr.getvalue())

    def test_root_help_succeeds(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(0, main(["--help"]))
        self.assertIn("discover search", stdout.getvalue())

    def test_native_discovery_uses_explicit_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "request.json").write_text(
                json.dumps(
                    {
                        "target_type": "song",
                        "goal": "Find a song",
                        "constraints": {},
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "catalog.json").write_text(
                json.dumps({"version": 1, "items": []}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "discover",
                        "search",
                        "request.json",
                        "catalog.json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("degraded", payload["status"])
            self.assertEqual([], payload["candidates"])
            self.assertEqual("", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
