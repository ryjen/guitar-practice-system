from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FIXTURE = ROOT / "examples" / "evidence" / "slide-feedback.json"


def adaptive_request() -> dict:
    return {
        "duration_minutes": 30,
        "environment": "headphones",
        "priorities": ["slide-foundations", "wah-rhythm"],
        "active_techniques": ["slide-foundations", "wah-rhythm"],
        "max_active_techniques": 3,
        "available_gear": ["guitar-fender-strat-white", "headphones"],
        "available_backing_tracks": ["slide-slow-blues-a-60"],
        "desired_genres": ["blues"],
        "theory_focus": ["chord tones"],
        "evidence": {
            "slide-foundations": {
                "largest_audible_defect": "pitch drifts during slow movement"
            }
        },
    }


def run_compatibility_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    )
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


class NativeAdvisoryCliTests(unittest.TestCase):
    def test_commands_are_native(self) -> None:
        for tokens in (
            ["evidence", "feedback"],
            ["session", "adapt"],
        ):
            with self.subTest(tokens=tokens):
                command, consumed = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(len(tokens), consumed)
                self.assertEqual(MigrationState.NATIVE, command.migration)
                self.assertIsNotNone(command.native_handler)
                self.assertIsNone(command.legacy)

    def test_evidence_feedback_matches_compatibility_script_exactly(self) -> None:
        fixture = json.loads(EVIDENCE_FIXTURE.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            input_path = workspace / "evidence.json"
            input_path.write_text(
                json.dumps(fixture),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "evidence",
                        "feedback",
                        "evidence.json",
                        "--as-of",
                        "2026-08-06",
                    ]
                )

            compat = run_compatibility_script(
                "evidence_feedback.py",
                str(input_path),
                "--as-of",
                "2026-08-06",
            )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(0, compat.returncode, compat.stderr)
            self.assertEqual(compat.stdout, stdout.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_evidence_feedback_accepts_raw_record_array(self) -> None:
        fixture = json.loads(EVIDENCE_FIXTURE.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "records.json").write_text(
                json.dumps(fixture["records"]),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "evidence",
                        "feedback",
                        "records.json",
                        "--as-of",
                        "2026-08-06",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("complete", payload["status"])
            self.assertEqual("2026-08-06", payload["as_of"])
            self.assertTrue(payload["targets"][0]["reliability_eligible"])

    def test_adaptive_session_matches_compatibility_script_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            input_path = workspace / "request.json"
            input_path.write_text(
                json.dumps(adaptive_request()),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "session",
                        "adapt",
                        "request.json",
                    ]
                )

            compat = run_compatibility_script(
                "adaptive_session.py",
                str(input_path),
            )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(0, compat.returncode, compat.stderr)
            self.assertEqual(compat.stdout, stdout.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("slide-foundations", payload["focus_technique"])
            self.assertFalse((workspace / "scripts").exists())

    def test_native_invalid_data_uses_stable_data_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "request.json").write_text(
                json.dumps({"duration_minutes": 20}),
                encoding="utf-8",
            )
            (workspace / "evidence.json").write_text(
                json.dumps({"records": []}),
                encoding="utf-8",
            )

            for tokens in (
                ["session", "adapt", "request.json"],
                [
                    "evidence",
                    "feedback",
                    "evidence.json",
                    "--as-of",
                    "2026-08-06",
                ],
            ):
                with self.subTest(tokens=tokens):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                        stderr
                    ):
                        result = main(
                            ["--workspace", str(workspace), *tokens]
                        )
                    self.assertEqual(65, result)
                    self.assertEqual("", stdout.getvalue())
                    self.assertTrue(stderr.getvalue().startswith("guitarctl: "))

    def test_native_inputs_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "session",
                        "adapt",
                        "../request.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("workspace-relative", stderr.getvalue())

    def test_compatibility_shims_define_no_decision_functions(self) -> None:
        for script in ("adaptive_session.py", "evidence_feedback.py"):
            with self.subTest(script=script):
                tree = ast.parse(
                    (ROOT / "scripts" / script).read_text(encoding="utf-8")
                )
                definitions = {
                    node.name
                    for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                self.assertEqual({"main"}, definitions)


if __name__ == "__main__":
    unittest.main()
