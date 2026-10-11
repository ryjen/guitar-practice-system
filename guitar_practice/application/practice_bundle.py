"""Deterministic public practice-bundle construction."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
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
    "contracts/dsp",
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

    def _project_version(self) -> str:
        payload = tomllib.loads(self.tree.read_text("pyproject.toml"))
        version = payload.get("project", {}).get("version")
        if not isinstance(version, str) or not version:
            raise ValueError("pyproject.toml project.version must be non-empty")
        return version

    def _contract_versions(self) -> dict[str, int]:
        def version(path: str, *keys: str) -> int:
            value: Any = self.tree.read(path)
            for key in keys:
                if not isinstance(value, dict) or key not in value:
                    raise ValueError(
                        f"cannot resolve contract version from {path}: {'.'.join(keys)}"
                    )
                value = value[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"contract version in {path} must be a positive integer"
                )
            return value

        return {
            "practice-data": version(
                "catalogs/practice-data.json",
                "schemaVersion",
            ),
            "groove-catalog": version(
                "catalogs/grooves/catalog.json",
                "version",
            ),
            "progression-catalog": version(
                "catalogs/progressions/catalog.json",
                "version",
            ),
            "backing-track-request": version(
                "contracts/backing-tracks/backing-track-request.schema.json",
                "properties",
                "version",
                "const",
            ),
            "practice-progression": version(
                "contracts/backing-tracks/practice-progression.schema.json",
                "properties",
                "version",
                "const",
            ),
            "guitar-dsp.preset": version(
                "contracts/dsp/guitar-dsp-preset-v1.schema.json",
                "properties",
                "version",
                "const",
            ),
        }

    def _generator_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for path in GENERATOR_INPUTS:
            if not self.tree.exists(path):
                raise FileNotFoundError(f"missing generator input: {path}")
            hashes[path] = _sha256(self.tree.read_bytes(path))
        return hashes

    def build(
        self,
        output: str,
        *,
        source_sha: str,
        source_tag: str | None = None,
        release_readme: str | None = None,
    ) -> str:
        if not source_sha.strip():
            raise ValueError("source SHA must be non-empty")
        if source_tag is not None and not source_tag.strip():
            raise ValueError("source tag must be non-empty when provided")

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

        if release_readme is not None:
            bundle.write_text("RELEASE.md", release_readme)

        provenance: dict[str, Any] = {
            "schemaVersion": 1,
            "sourceGitSha": source_sha,
            "projectVersion": self._project_version(),
            "versionedContracts": self._contract_versions(),
            "runtime": {
                "python": sys.version.split()[0],
                "implementation": sys.implementation.name,
            },
            "generatorInputs": self._generator_hashes(),
            "artifacts": self._hashes(bundle),
        }
        if source_tag is not None:
            provenance["sourceGitTag"] = source_tag

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
