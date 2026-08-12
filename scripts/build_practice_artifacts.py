#!/usr/bin/env python3
"""Build a deterministic public practice-data bundle.

The bundle is derived entirely from repository-owned canonical sources. Generated
MIDI remains non-canonical build output; this script packages it with the public
metadata needed to understand and reproduce it, plus deterministic provenance and
checksums. CI uses the bundle only for validation and does not upload it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import export_practice_data
import generate_backing_tracks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "generated" / "practice-bundle"
PUBLIC_SOURCE_DIRS = (
    Path("backing-tracks"),
    Path("catalogs/grooves"),
    Path("contracts/backing-tracks"),
)
GENERATOR_INPUTS = (
    Path("scripts/backing_track_engine.py"),
    Path("scripts/build_practice_artifacts.py"),
    Path("scripts/export_practice_data.py"),
    Path("scripts/generate_backing_tracks.py"),
    Path("scripts/groove_catalog.py"),
    Path("scripts/groove_engine.py"),
    Path("scripts/midi_workflow.py"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def copy_public_sources(output: Path) -> None:
    for relative in PUBLIC_SOURCE_DIRS:
        source = ROOT / relative
        if not source.exists():
            raise FileNotFoundError(f"missing public source directory: {relative}")
        shutil.copytree(source, output / relative)


def build_provenance(output: Path, source_sha: str) -> dict[str, object]:
    payload_hashes = {
        str(path.relative_to(output)): sha256_file(path)
        for path in iter_files(output)
        if path.name not in {"provenance.json", "SHA256SUMS"}
    }
    generator_hashes = {
        str(relative): sha256_file(ROOT / relative) for relative in GENERATOR_INPUTS
    }
    return {
        "schemaVersion": 1,
        "sourceGitSha": source_sha,
        "runtime": {
            "python": sys.version.split()[0],
            "implementation": sys.implementation.name,
        },
        "generatorInputs": generator_hashes,
        "artifacts": payload_hashes,
    }


def write_checksums(output: Path) -> None:
    checksum_path = output / "SHA256SUMS"
    lines = []
    for path in iter_files(output):
        if path == checksum_path:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(output)}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bundle(output: Path, source_sha: str) -> None:
    if not source_sha.strip():
        raise ValueError("source SHA must be non-empty")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    copy_public_sources(output)
    export_practice_data.export(output / "exports" / "practice-data.json")
    generate_backing_tracks.generate_all(repo_root=output)

    provenance = build_provenance(output, source_sha)
    (output / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_checksums(output)


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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(output.relative_to(ROOT) if output.is_relative_to(ROOT) else output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
