"""Repository validation orchestration over explicit process/filesystem ports."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_practice.application.ports import CommandRunner, ModuleProbe
from guitar_practice.application.public_boundary import PublicBoundaryValidation


class ValidationUnavailable(RuntimeError):
    """A required validation dependency is unavailable."""


class ValidationFailed(RuntimeError):
    def __init__(self, label: str, returncode: int, details: list[str] | None = None) -> None:
        super().__init__(label)
        self.label = label
        self.returncode = returncode
        self.details = details or []


@dataclass(frozen=True)
class RepositoryValidation:
    runner: CommandRunner
    modules: ModuleProbe
    public_boundary: PublicBoundaryValidation
    python_executable: str

    def execute(self) -> list[dict[str, object]]:
        if not self.modules.available("ruff"):
            raise ValidationUnavailable(
                "Ruff is required for repository validation. "
                "Install pinned development dependencies with: "
                "python -m pip install -r requirements-dev.txt"
            )

        source_dirs = ["guitar_practice", "scripts", "tests", "tools"]
        checks = (
            (
                "Compile Python sources",
                [
                    self.python_executable,
                    "-m",
                    "compileall",
                    "-q",
                    *source_dirs,
                ],
            ),
            (
                "Run Ruff static analysis",
                [
                    self.python_executable,
                    "-m",
                    "ruff",
                    "check",
                    *source_dirs,
                ],
            ),
        )

        report: list[dict[str, object]] = []
        for label, command in checks:
            result = self.runner.run(command)
            report.append({"label": label, "returncode": result.returncode})
            if result.returncode != 0:
                details = [
                    line
                    for line in (result.stderr + "\n" + result.stdout).splitlines()
                    if line.strip()
                ]
                raise ValidationFailed(label, result.returncode, details)

        findings = self.public_boundary.validate()
        report.append(
            {
                "label": "Enforce public repository boundary",
                "returncode": 0 if not findings else 1,
                "findings": findings,
            }
        )
        if findings:
            raise ValidationFailed(
                "Enforce public repository boundary",
                1,
                findings,
            )

        label = "Run unit tests"
        result = self.runner.run(
            [
                self.python_executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ]
        )
        report.append({"label": label, "returncode": result.returncode})
        if result.returncode != 0:
            details = [
                line
                for line in (result.stderr + "\n" + result.stdout).splitlines()
                if line.strip()
            ]
            raise ValidationFailed(label, result.returncode, details)
        return report
