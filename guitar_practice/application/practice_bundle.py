"""Deterministic public practice-bundle construction."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.generation import GenerateBackingCatalog
from guitar_practice.application.ports import WorkspaceTree
from guitar_practice.application.practice_data_export import PracticeDataExport

PUBLIC_SOURCE_DIRS = (
    "backing-tracks",
    "catalogs/grooves",
    "catalogs/progressions",
    "contracts/backing-tracks",
    "contracts/progressions",
)
GENERATOR_INPUTS = (
    "guitar_practice/adapters/binary_files.py",
    "guitar_practice/adapters/json_files.py",
    "guitar_practice/adapters/workspace_tree.py",
    "guitar_practice/application/generation.py",
    "guitar_practice/application/practice_bundle.py",
    "guitar_practice/application/practice_data_export.py",
    "guitar_practice/domain/backing.py",
    "guitar_practice/domain/bass.py",
    "guitar_practice/domain/groove.py",
    "guitar_practice/domain/midi.py",
    "guitar_practice/domain/practice_data.py",
    "scripts/backing_track_engine.py",
    "scripts/bass_engine.py",
    "scripts/build_practice_artifacts.py",
    "scripts/export_practice_data.py",
    "scripts/generate_backing_tracks.py",
    "scripts/groove_catalog.py",
    "scripts/groove_engine.py",
    "scripts/midi_workflow.py",
    "scripts/progression_catalog.py",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class PracticeBundleBuilder:
    tree: WorkspaceTree

    def _hashes(self, tree: WorkspaceTree) -> dict[str, str]:
        return {
            path: _sha256(tree.read_bytes(path))
            for path in tree.list_files(".")
            if path not in {"provenance.json", "SHA256SUMS"}
        }

    def _generator_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for path in GENERATOR_INPUTS:
            if not self.tree.exists(path):
                raise FileNotFoundError(f"missing generator input: {path}")
            hashes[path] = _sha256(self.tree.read_bytes(path))
        return hashes

    def build(self, output: str, *, source_sha: str) -> str:
        if not source_sha.strip():
            raise ValueError("source SHA must be non-empty")

        self.tree.remove_tree(output)
        self.tree.make_directory(output)
        bundle = self.tree.scoped(output)

        for source in PUBLIC_SOURCE_DIRS:
            if not self.tree.exists(source):
                raise FileNotFoundError(
                    f"missing public source directory: {source}"
                )
            self.tree.copy_tree(source, f"{output}/{source}")

        PracticeDataExport(
            values=self.tree,
            tree=self.tree,
        ).export(f"{output}/exports/practice-data.json")

        GenerateBackingCatalog(
            documents=bundle,
            locator=bundle,
            artifacts=bundle,
        ).execute()

        provenance: dict[str, Any] = {
            "schemaVersion": 1,
            "sourceGitSha": source_sha,
            "runtime": {
                "python": sys.version.split()[0],
                "implementation": sys.implementation.name,
            },
            "generatorInputs": self._generator_hashes(),
            "artifacts": self._hashes(bundle),
        }
        bundle.write_text(
            "provenance.json",
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        )

        checksum_lines = [
            f"{_sha256(bundle.read_bytes(path))}  {path}"
            for path in bundle.list_files(".")
            if path != "SHA256SUMS"
        ]
        bundle.write_text(
            "SHA256SUMS",
            "\n".join(checksum_lines) + "\n",
        )
        return output
