from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import unittest
from pathlib import Path
from unittest import mock

from guitar_practice.application.repository_validation import ValidationFailed
from guitar_practice.interfaces.cli.commands import (
    COMMANDS,
    COMPATIBILITY_SHIMS,
    MigrationState,
    registered_legacy_scripts,
)

ROOT = Path(__file__).resolve().parents[1]
DIRECT_INVOCATION = re.compile(r"\bpython3?\s+(?:scripts|tools)/[^\s]+\.py\b")


def _load_validate_repo_shim():
    path = ROOT / "scripts" / "validate_repo.py"
    spec = importlib.util.spec_from_file_location("validate_repo_compat", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CliCutoverPolicyTests(unittest.TestCase):
    def test_no_stable_command_remains_legacy(self) -> None:
        self.assertEqual(
            [],
            [
                command.path
                for command in COMMANDS
                if command.migration == MigrationState.LEGACY
            ],
        )

    def test_only_deprecated_scheduling_v1_uses_legacy_process_adapter(self) -> None:
        self.assertEqual(
            frozenset({"scripts/scheduling.py"}),
            registered_legacy_scripts(),
        )
        deprecated = [
            command
            for command in COMMANDS
            if command.migration == MigrationState.DEPRECATED
        ]
        self.assertTrue(deprecated)
        self.assertTrue(
            all(command.path[:2] == ("schedule", "legacy") for command in deprecated)
        )

    def test_workflows_do_not_know_compatibility_shim_filenames(self) -> None:
        forbidden_paths = set(COMPATIBILITY_SHIMS) | set(registered_legacy_scripts())
        findings: list[str] = []
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for shim in sorted(forbidden_paths):
                if shim in text:
                    findings.append(f"{path.relative_to(ROOT)}: {shim}")
            for match in DIRECT_INVOCATION.finditer(text):
                findings.append(
                    f"{path.relative_to(ROOT)}: direct invocation {match.group(0)}"
                )
        self.assertEqual([], findings)

    def test_preferred_docs_do_not_invoke_compatibility_scripts(self) -> None:
        findings: list[str] = []
        paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
        for path in paths:
            for match in DIRECT_INVOCATION.finditer(path.read_text(encoding="utf-8")):
                findings.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
        self.assertEqual([], findings)

    def test_validate_repo_shim_preserves_failure_diagnostics(self) -> None:
        module = _load_validate_repo_shim()
        failure = ValidationFailed(
            "Run Ruff static analysis",
            3,
            ["ruff diagnostic", "second diagnostic"],
        )
        stderr = io.StringIO()
        with mock.patch.object(module, "RepositoryValidation") as validation:
            validation.return_value.execute.side_effect = failure
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                stderr
            ):
                result = module.main()

        self.assertEqual(3, result)
        self.assertEqual(
            "Run Ruff static analysis failed\nruff diagnostic\nsecond diagnostic\n",
            stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
