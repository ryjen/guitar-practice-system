#!/usr/bin/env python3
"""Generate and validate every committed backing-track manifest.

Generated MIDI remains a local build artifact under ``generated/backing-tracks``.
The manifest is authoritative for the output path. Backing-track orchestration
resolves named groove presets and arrangement-wide gap cycles before delegating
to the deterministic MIDI and groove renderers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import backing_track_engine
import midi_workflow


ROOT = Path(__file__).resolve().parents[1]
BACKING_TRACKS = ROOT / "backing-tracks"


def discover_manifests(root: Path = BACKING_TRACKS) -> list[Path]:
    return sorted(root.glob("*/manifest.json"))


def manifest_output_path(manifest_path: Path, repo_root: Path = ROOT) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get("midi"), str):
        raise midi_workflow.ManifestError("manifest outputs.midi must be a path string")

    relative = Path(outputs["midi"])
    if relative.is_absolute() or ".." in relative.parts:
        raise midi_workflow.ManifestError("outputs.midi must remain inside the repository")
    if relative.suffix.lower() != ".mid":
        raise midi_workflow.ManifestError("outputs.midi must end in .mid")
    if relative.parts[:2] != ("generated", "backing-tracks"):
        raise midi_workflow.ManifestError(
            "outputs.midi must be under generated/backing-tracks"
        )
    if relative.name != f"{manifest.get('id')}.mid":
        raise midi_workflow.ManifestError("outputs.midi filename must match manifest id")
    return repo_root / relative


def generate_all(
    *,
    manifest_root: Path = BACKING_TRACKS,
    repo_root: Path = ROOT,
) -> list[dict[str, Any]]:
    manifests = discover_manifests(manifest_root)
    if not manifests:
        raise midi_workflow.ManifestError("no backing-track manifests found")

    results: list[dict[str, Any]] = []
    for manifest_path in manifests:
        output = manifest_output_path(manifest_path, repo_root)
        backing_track_engine.generate(manifest_path, output)
        report = midi_workflow.validate_output(manifest_path, output)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results.append(
            {
                "id": manifest["id"],
                "manifest": str(manifest_path.relative_to(manifest_root.parent)),
                "output": str(output.relative_to(repo_root)),
                "tracks": report["tracks"],
                "markers": report["markers"],
            }
        )
    return results


def main() -> int:
    try:
        results = generate_all()
    except (OSError, json.JSONDecodeError, midi_workflow.ManifestError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
