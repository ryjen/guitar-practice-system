#!/usr/bin/env python3
"""Compatibility shim for package-native practice bundle construction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_bundle import (
    GENERATOR_INPUTS as GENERATOR_INPUTS,
    PUBLIC_SOURCE_DIRS as PUBLIC_SOURCE_DIRS,
    PracticeBundleBuilder,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "generated" / "practice-bundle"


def build_bundle(output: Path, source_sha: str) -> None:
    PracticeBundleBuilder(WorkspaceFileTree(ROOT)).build(
        str(output),
        source_sha=source_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="bundle directory (default: generated/practice-bundle)",
    )
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    try:
        build_bundle(output, args.source_sha)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output.relative_to(ROOT) if output.is_relative_to(ROOT) else output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
