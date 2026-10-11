from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_bundle import (
    GENERATOR_INPUTS,
    PUBLIC_SOURCE_DIRS,
)
from guitar_practice.application.public_boundary import PublicBoundaryValidation
from guitar_practice.application.repository_validation import (
    RepositoryValidation,
    ValidationFailed,
    ValidationUnavailable,
)
from guitar_practice.application.ports import CommandResult
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "0123456789abcdef0123456789abcdef01234567"


def _copy(root: Path, relative: str) -> None:
    source = ROOT / relative
    target = root / relative
    if source.is_dir():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _prepare_operational_workspace(root: Path) -> None:
    for relative in PUBLIC_SOURCE_DIRS:
        _copy(root, relative)
    _copy(root, "catalogs/practice-data.json")

    catalog = json.loads(
        (ROOT / "catalogs" / "practice-data.json").read_text(encoding="utf-8")
    )
    for session in catalog["sessions"]:
        _copy(root, session["source"]["path"])

    for relative in GENERATOR_INPUTS:
        _copy(root, relative)


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
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
        timeout=120,
    )


class NativeOperationalCliTests(unittest.TestCase):
    def test_operational_commands_are_native(self) -> None:
        for tokens in (
            ["artifact", "build"],
            ["export", "practice-data"],
            ["validate", "repo"],
            ["validate", "public-boundary"],
        ):
            with self.subTest(tokens=tokens):
                command, consumed = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(len(tokens), consumed)
                self.assertEqual(MigrationState.NATIVE, command.migration)
                self.assertIsNotNone(command.native_handler)
                self.assertIsNone(command.legacy)

    def test_practice_data_export_matches_compatibility_output_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            _prepare_operational_workspace(workspace)

            native_stdout = io.StringIO()
            native_stderr = io.StringIO()
            with contextlib.redirect_stdout(native_stdout), contextlib.redirect_stderr(
                native_stderr
            ):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "export",
                        "practice-data",
                        "--output",
                        "native.json",
                    ]
                )

            shim_output = root / "shim.json"
            shim = _run_script(
                "export_practice_data.py",
                "--output",
                str(shim_output),
            )

            self.assertEqual(0, result)
            self.assertEqual("", native_stderr.getvalue())
            self.assertEqual(0, shim.returncode, shim.stderr)
            self.assertEqual(
                shim_output.read_bytes(),
                (workspace / "native.json").read_bytes(),
            )

            check_stdout = io.StringIO()
            check_stderr = io.StringIO()
            with contextlib.redirect_stdout(check_stdout), contextlib.redirect_stderr(
                check_stderr
            ):
                check_result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "export",
                        "practice-data",
                        "--output",
                        "native.json",
                        "--check",
                    ]
                )
            self.assertEqual(0, check_result)
            self.assertEqual("", check_stderr.getvalue())
            self.assertEqual("valid", json.loads(check_stdout.getvalue())["status"])

    def test_practice_data_check_fails_closed_for_stale_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            _prepare_operational_workspace(workspace)
            (workspace / "native.json").write_text("{}\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "export",
                        "practice-data",
                        "--output",
                        "native.json",
                        "--check",
                    ]
                )

            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertTrue(stderr.getvalue().startswith("guitarctl: "))

    def test_artifact_bundle_matches_compatibility_shim_including_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            _prepare_operational_workspace(workspace)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "artifact",
                        "build",
                        "--output-dir",
                        "bundle",
                        "--source-sha",
                        SOURCE_SHA,
                    ]
                )

            shim_bundle = root / "shim-bundle"
            shim = _run_script(
                "build_practice_artifacts.py",
                "--output-dir",
                str(shim_bundle),
                "--source-sha",
                SOURCE_SHA,
            )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(0, shim.returncode, shim.stderr)
            self.assertEqual(_files(shim_bundle), _files(workspace / "bundle"))

            provenance = json.loads(
                (workspace / "bundle" / "provenance.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(SOURCE_SHA, provenance["sourceGitSha"])
            self.assertIn(
                "guitar_practice/application/practice_bundle.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/domain/practice_data.py",
                provenance["generatorInputs"],
            )
            self.assertTrue((workspace / "bundle" / "SHA256SUMS").is_file())
            self.assertFalse((workspace / "scripts").is_dir())

    def test_operational_output_paths_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "artifact",
                        "build",
                        "--output-dir",
                        "../bundle",
                        "--source-sha",
                        SOURCE_SHA,
                    ]
                )
            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("workspace-relative", stderr.getvalue())

    def test_public_boundary_native_command_reports_exact_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "safe.md").write_text(
                "ordinary public guitar documentation\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "validate",
                        "public-boundary",
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual("passed", json.loads(stdout.getvalue())["status"])

            (workspace / "bad.md").write_text(
                "Do not mention " + "Open" + "AI" + " here.\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "validate",
                        "public-boundary",
                    ]
                )
            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn(
                "bad.md:1: contains boundary marker '" + "Open" + "AI" + "'",
                stderr.getvalue(),
            )


class FakeRunner:
    def __init__(self, returncodes: list[int]) -> None:
        self.returncodes = list(returncodes)
        self.commands: list[list[str]] = []

    def run(self, command) -> CommandResult:
        self.commands.append(list(command))
        return CommandResult(returncode=self.returncodes.pop(0))


class FakeProbe:
    def __init__(self, available: bool) -> None:
        self.value = available

    def available(self, module: str) -> bool:
        return self.value and module == "ruff"


class RepositoryValidationTests(unittest.TestCase):
    def _service(
        self,
        workspace: Path,
        *,
        returncodes: list[int],
        ruff: bool = True,
    ) -> tuple[RepositoryValidation, FakeRunner]:
        runner = FakeRunner(returncodes)
        service = RepositoryValidation(
            runner=runner,
            modules=FakeProbe(ruff),
            public_boundary=PublicBoundaryValidation(
                WorkspaceFileTree(workspace)
            ),
            python_executable=sys.executable,
        )
        return service, runner

    def test_missing_ruff_is_explicitly_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, runner = self._service(
                Path(directory),
                returncodes=[],
                ruff=False,
            )
            with self.assertRaises(ValidationUnavailable):
                service.execute()
            self.assertEqual([], runner.commands)

    def test_failed_child_check_preserves_failing_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, runner = self._service(
                Path(directory),
                returncodes=[0, 3],
            )
            with self.assertRaises(ValidationFailed) as caught:
                service.execute()
            self.assertEqual("Run Ruff static analysis", caught.exception.label)
            self.assertEqual(3, caught.exception.returncode)
            self.assertEqual(2, len(runner.commands))

    def test_public_boundary_failure_is_not_spawned_as_a_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bad.md").write_text(
                "OpenAI\n",
                encoding="utf-8",
            )
            service, runner = self._service(
                workspace,
                returncodes=[0, 0],
            )
            with self.assertRaises(ValidationFailed) as caught:
                service.execute()
            self.assertEqual(
                "Enforce public repository boundary",
                caught.exception.label,
            )
            self.assertEqual(1, caught.exception.returncode)
            self.assertEqual(2, len(runner.commands))

    def test_success_runs_compile_ruff_and_tests_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, runner = self._service(
                Path(directory),
                returncodes=[0, 0, 0],
            )
            report = service.execute()
            self.assertEqual(4, len(report))
            self.assertEqual(3, len(runner.commands))
            flattened = [" ".join(command) for command in runner.commands]
            self.assertFalse(
                any("check_public_boundary.py" in command for command in flattened)
            )


if __name__ == "__main__":
    unittest.main()
