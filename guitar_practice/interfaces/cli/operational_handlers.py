"""Native CLI handlers for operational repository tooling."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence

from guitar_practice.adapters.json_values import JsonValueFileReader
from guitar_practice.adapters.processes import PythonModuleProbe, SubprocessCommandRunner
from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_bundle import PracticeBundleBuilder
from guitar_practice.application.practice_data_export import (
    DEFAULT_OUTPUT as DEFAULT_PRACTICE_DATA_OUTPUT,
    PracticeDataExport,
)
from guitar_practice.application.public_boundary import PublicBoundaryValidation
from guitar_practice.application.repository_validation import (
    RepositoryValidation,
    ValidationFailed,
    ValidationUnavailable,
)
from guitar_practice.domain.practice_data import CatalogError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.practice_args import (
    PracticePathError,
    workspace_relative,
)
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _write_json(value: object, context: CliContext) -> None:
    json.dump(value, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")


def export_practice_data(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl export practice-data")
    parser.add_argument("--output", default=DEFAULT_PRACTICE_DATA_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(list(argv))

    try:
        output = workspace_relative(args.output, label="practice-data output")
        service = PracticeDataExport(
            values=JsonValueFileReader(context.workspace),
            tree=WorkspaceFileTree(context.workspace),
        )
        if args.check:
            service.check(output)
        else:
            service.export(output)
    except (
        PracticePathError,
        CatalogError,
        OSError,
        ValueError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {
            "status": "valid" if args.check else "exported",
            "output": output,
        },
        context,
    )
    return exit_codes.OK


def artifact_build(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl artifact build")
    parser.add_argument(
        "--output-dir",
        default="generated/practice-bundle",
    )
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args(list(argv))

    try:
        output = workspace_relative(args.output_dir, label="artifact output")
        built = PracticeBundleBuilder(
            WorkspaceFileTree(context.workspace)
        ).build(
            output,
            source_sha=args.source_sha,
        )
    except (
        PracticePathError,
        CatalogError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json({"status": "built", "output": built}, context)
    return exit_codes.OK


def validate_public_boundary(
    argv: Sequence[str],
    context: CliContext,
) -> int:
    parser = argparse.ArgumentParser(
        prog="guitarctl validate public-boundary"
    )
    parser.parse_args(list(argv))

    try:
        findings = PublicBoundaryValidation(
            WorkspaceFileTree(context.workspace)
        ).validate()
    except OSError as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    if findings:
        for finding in findings:
            print(f"guitarctl: {finding}", file=context.stderr)
        return exit_codes.DATA_ERROR

    _write_json(
        {"status": "passed", "findings": []},
        context,
    )
    return exit_codes.OK


def validate_repo(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl validate repo")
    parser.parse_args(list(argv))

    try:
        service = RepositoryValidation(
            runner=SubprocessCommandRunner(context.workspace),
            modules=PythonModuleProbe(),
            public_boundary=PublicBoundaryValidation(
                WorkspaceFileTree(context.workspace)
            ),
            python_executable=sys.executable,
        )
        report = service.execute()
    except ValidationUnavailable as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.UNAVAILABLE
    except ValidationFailed as exc:
        print(f"guitarctl: {exc.label} failed", file=context.stderr)
        for detail in exc.details:
            print(f"guitarctl: {detail}", file=context.stderr)
        return exit_codes.DATA_ERROR
    except OSError as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.INTERNAL

    _write_json({"status": "passed", "checks": report}, context)
    return exit_codes.OK


OPERATIONAL_HANDLERS: dict[str, NativeHandler] = {
    "artifact-build": artifact_build,
    "export-practice-data": export_practice_data,
    "validate-public-boundary": validate_public_boundary,
    "validate-repo": validate_repo,
}
