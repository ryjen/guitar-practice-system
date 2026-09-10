"""Stable command-line entrypoint for Guitar Practice System."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Sequence

from guitar_practice import __version__
from guitar_practice.adapters.legacy import LegacyCommandError, run_script
from guitar_practice.interfaces.cli.commands import LEGACY_COMMANDS, LegacyCommand


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guitarctl",
        description="Deterministic, local-first Guitar Practice System CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    grouped: dict[str, list[LegacyCommand]] = defaultdict(list)
    for command in LEGACY_COMMANDS:
        grouped[command.path[0]].append(command)

    for root, commands in sorted(grouped.items()):
        direct = next((item for item in commands if len(item.path) == 1), None)
        nested = [item for item in commands if len(item.path) > 1]
        if direct and not nested:
            child = subparsers.add_parser(root, help=direct.help)
            child.set_defaults(_legacy=direct)
            child.add_argument("args", nargs=argparse.REMAINDER)
            continue

        child = subparsers.add_parser(root, help=f"{root.title()} commands")
        nested_parsers = child.add_subparsers(dest=f"{root}_command")
        if direct:
            child.set_defaults(_legacy=direct)
            child.add_argument("args", nargs=argparse.REMAINDER)
        for item in nested:
            leaf = nested_parsers.add_parser(item.path[1], help=item.help)
            leaf.set_defaults(_legacy=item)
            leaf.add_argument("args", nargs=argparse.REMAINDER)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = getattr(args, "_legacy", None)
    if command is None:
        parser.print_help(sys.stderr)
        return 2

    forwarded = getattr(args, "args", [])
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    try:
        return run_script(command.script, forwarded)
    except LegacyCommandError as exc:
        print(f"guitarctl: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
