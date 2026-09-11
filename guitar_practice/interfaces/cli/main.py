"""Stable command-line entrypoint for Guitar Practice System."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from guitar_practice import __version__
from guitar_practice.adapters.legacy import LegacyCommandError, run_script
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.commands import (
    COMMANDS,
    MigrationState,
    commands_below,
    find_command,
)
from guitar_practice.interfaces.cli.handler_registry import NATIVE_HANDLERS
from guitar_practice.interfaces.cli.runtime import CliContext


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guitarctl",
        add_help=False,
        description="Deterministic, local-first Guitar Practice System CLI",
    )
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Repository/workspace root for relative paths and compatibility commands",
    )
    parser.add_argument("tokens", nargs=argparse.REMAINDER)
    return parser


def _print_root_help(stream: TextIO) -> None:
    print(
        "usage: guitarctl [--workspace PATH] <command> [args...]\n\n"
        "Stable commands:\n",
        file=stream,
        end="",
    )
    width = max(len(" ".join(command.path)) for command in COMMANDS)
    for command in COMMANDS:
        path = " ".join(command.path)
        suffix = " [deprecated]" if command.migration is MigrationState.DEPRECATED else ""
        print(f"  {path:<{width}}  {command.help}{suffix}", file=stream)
    print(
        "\nGlobal options must appear before the command. "
        "Use '<command> --help' for package-native command help.",
        file=stream,
    )


def _print_prefix_help(prefix: Sequence[str], stream: TextIO) -> None:
    matches = commands_below(prefix)
    if not matches:
        return
    print(f"Available under {' '.join(prefix)!r}:", file=stream)
    for command in matches:
        print(f"  {' '.join(command.path)}  {command.help}", file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version:
        print(f"guitarctl {__version__}")
        return exit_codes.OK

    tokens = list(args.tokens)
    if tokens[:1] == ["--"]:
        tokens = tokens[1:]

    if args.help and not tokens:
        _print_root_help(sys.stdout)
        return exit_codes.OK
    if not tokens:
        _print_root_help(sys.stderr)
        return exit_codes.USAGE

    command, consumed = find_command(tokens)
    if command is None:
        prefix_matches = commands_below(tokens)
        if prefix_matches:
            _print_prefix_help(tokens, sys.stderr)
        else:
            print(f"guitarctl: unknown command: {' '.join(tokens)}", file=sys.stderr)
            _print_prefix_help(tokens[:1], sys.stderr)
        return exit_codes.USAGE

    forwarded = tokens[consumed:]
    context = CliContext(Path(args.workspace), sys.stdout, sys.stderr)

    if command.native_handler:
        handler = NATIVE_HANDLERS.get(command.native_handler)
        if handler is None:
            print(
                f"guitarctl: native handler is not registered: {command.native_handler}",
                file=sys.stderr,
            )
            return exit_codes.INTERNAL
        try:
            return handler(forwarded, context)
        except SystemExit as exc:
            return int(exc.code or 0)

    assert command.legacy is not None
    if command.migration is MigrationState.DEPRECATED:
        print(
            f"guitarctl: warning: {' '.join(command.path)} is a compatibility command",
            file=sys.stderr,
        )
    try:
        return run_script(
            workspace=context.workspace,
            script=command.legacy.script,
            argv=forwarded,
            prefix=command.legacy.prefix,
            global_options=command.legacy.global_options,
        )
    except LegacyCommandError as exc:
        print(f"guitarctl: {exc}", file=sys.stderr)
        return exit_codes.UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
