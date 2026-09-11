"""CLI handlers for deterministic groove catalog operations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.groove import DEFAULT_CATALOG, GrooveCatalog
from guitar_practice.domain.midi import ManifestError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def _parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"guitarctl groove {command}")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help="Groove catalog JSON")
    return parser


def _service(context: CliContext, catalog: str) -> GrooveCatalog:
    return GrooveCatalog(JsonFileStore(context.workspace), catalog)


def _write_json(value: object, context: CliContext) -> None:
    # Preserve the historical groove-catalog JSON field order during migration.
    json.dump(value, context.stdout, indent=2)
    context.stdout.write("\n")


def groove_validate(argv: Sequence[str], context: CliContext) -> int:
    parser = _parser("validate")
    try:
        args = parser.parse_args(list(argv))
        result = _service(context, args.catalog).validate()
    except (ManifestError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


def groove_list(argv: Sequence[str], context: CliContext) -> int:
    parser = _parser("list")
    try:
        args = parser.parse_args(list(argv))
        result = _service(context, args.catalog).list()
    except (ManifestError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


def groove_show(argv: Sequence[str], context: CliContext) -> int:
    parser = _parser("show")
    parser.add_argument("preset_id")
    try:
        args = parser.parse_args(list(argv))
        result = _service(context, args.catalog).show(args.preset_id)
    except (ManifestError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR
    _write_json(result, context)
    return exit_codes.OK


GROOVE_HANDLERS: dict[str, NativeHandler] = {
    "groove-validate": groove_validate,
    "groove-list": groove_list,
    "groove-show": groove_show,
}
