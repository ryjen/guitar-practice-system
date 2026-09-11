from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain.assessment import assess
from guitar_practice.domain.scheduling import approval_status, propose
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class NativePlanningCliTests(unittest.TestCase):
    def test_planning_commands_are_native(self) -> None:
        for tokens in (
            ["schedule", "propose"],
            ["schedule", "check-approval"],
            ["assess", "evaluate"],
        ):
            command, consumed = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(len(tokens), consumed)
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

    def test_schedule_cli_runs_without_repository_scripts(self) -> None:
        snapshot = json.loads(
            (ROOT / "examples" / "scheduling" / "v2-example-snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        expected = propose(snapshot)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "snapshot.json").write_text(
                json.dumps(snapshot),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "schedule",
                        "propose",
                        "snapshot.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(expected, json.loads(stdout.getvalue()))
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

            (workspace / "proposal.json").write_text(
                stdout.getvalue(),
                encoding="utf-8",
            )
            approval_stdout = io.StringIO()
            approval_stderr = io.StringIO()
            with contextlib.redirect_stdout(approval_stdout), contextlib.redirect_stderr(
                approval_stderr
            ):
                approval_result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "schedule",
                        "check-approval",
                        "proposal.json",
                        "snapshot.json",
                    ]
                )

            self.assertEqual(0, approval_result)
            self.assertEqual(
                approval_status(expected, snapshot),
                json.loads(approval_stdout.getvalue()),
            )
            self.assertEqual("", approval_stderr.getvalue())

    def test_assessment_cli_runs_without_repository_scripts(self) -> None:
        request = json.loads(
            (ROOT / "examples" / "assessment" / "slide-reliable-context.json").read_text(
                encoding="utf-8"
            )
        )
        gates = json.loads(
            (ROOT / "templates" / "assessment-gate-set.json").read_text(
                encoding="utf-8"
            )
        )
        expected = assess(request, gates)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "request.json").write_text(
                json.dumps(request),
                encoding="utf-8",
            )
            (workspace / "gates.json").write_text(
                json.dumps(gates),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "assess",
                        "evaluate",
                        "request.json",
                        "gates.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(expected, json.loads(stdout.getvalue()))
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
