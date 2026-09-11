"""Compatibility process adapter for registered legacy entrypoints.

This module contains no product logic. It exists only while old repository scripts
are strangled behind the stable command surface.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


class LegacyCommandError(RuntimeError):
    pass


def _extract_global_options(
    argv: Sequence[str], option_names: Sequence[str]
) -> tuple[list[str], list[str]]:
    """Move registered parent-parser options ahead of a fixed legacy subcommand."""

    names = set(option_names)
    globals_: list[str] = []
    remainder: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        name = value.split("=", 1)[0]
        if name in names:
            globals_.append(value)
            if "=" not in value:
                index += 1
                if index >= len(argv):
                    raise LegacyCommandError(f"missing value for legacy option {name}")
                globals_.append(argv[index])
        else:
            remainder.append(value)
        index += 1
    return globals_, remainder


def compose_argv(
    argv: Sequence[str],
    *,
    prefix: Sequence[str] = (),
    global_options: Sequence[str] = (),
) -> list[str]:
    globals_, remainder = _extract_global_options(argv, global_options)
    return [*globals_, *prefix, *remainder]


def run_script(
    *,
    workspace: Path,
    script: str,
    argv: Sequence[str],
    prefix: Sequence[str] = (),
    global_options: Sequence[str] = (),
) -> int:
    root = workspace.resolve()
    path = (root / script).resolve()
    if not path.is_relative_to(root):
        raise LegacyCommandError(f"legacy command target escapes workspace: {script}")
    if not path.is_file():
        raise LegacyCommandError(
            f"legacy command target not found under workspace {root}: {script}"
        )

    completed = subprocess.run(
        [
            sys.executable,
            str(path),
            *compose_argv(argv, prefix=prefix, global_options=global_options),
        ],
        cwd=root,
        check=False,
    )
    return completed.returncode
