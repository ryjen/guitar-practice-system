#!/usr/bin/env python3
"""Compatibility entrypoint for bulk deterministic backing-track generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import midi_workflow as _midi_workflow  # noqa: E402
from guitar_practice.adapters.binary_files import BinaryFileStore  # noqa: E402
from guitar_practice.adapters.json_files import JsonFileStore  # noqa: E402
from guitar_practice.application.generation import (  # noqa: E402
    GenerateBackingCatalog,
    manifest_output_path as _manifest_output_path,
)

midi_workflow = _midi_workflow
BACKING_TRACKS = ROOT / "backing-tracks"


def discover_manifests(root: Path = BACKING_TRACKS) -> list[Path]:
    return sorted(root.glob("*/manifest.json"))


def manifest_output_path(manifest_path: Path, repo_root: Path = ROOT) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return repo_root / _manifest_output_path(manifest)


def generate_all(
    *,
    manifest_root: Path = BACKING_TRACKS,
    repo_root: Path = ROOT,
) -> list[dict[str, Any]]:
    workspace = manifest_root.parent
    documents = JsonFileStore(workspace)
    return GenerateBackingCatalog(
        documents=documents,
        locator=documents,
        artifacts=BinaryFileStore(repo_root),
        manifest_pattern=f"{manifest_root.name}/*/manifest.json",
    ).execute()


def main() -> int:
    try:
        results = generate_all()
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
