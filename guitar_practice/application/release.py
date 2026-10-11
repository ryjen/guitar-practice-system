"""Deterministic versioned release preparation and verification."""

from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import tomllib
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import WorkspaceTree
from guitar_practice.application.practice_bundle import PracticeBundleBuilder
from guitar_practice.domain import release

_CHECKSUM_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ReleasePackager:
    tree: WorkspaceTree

    def _project_version(self) -> str:
        payload = tomllib.loads(self.tree.read_text("pyproject.toml"))
        version = payload.get("project", {}).get("version")
        if not isinstance(version, str) or not version:
            raise release.ReleaseError(
                "pyproject.toml project.version must be non-empty"
            )
        return version

    def _changed_paths(self, path: str | None) -> tuple[str, ...]:
        if path is None:
            return ()
        return tuple(
            line.strip()
            for line in self.tree.read_text(path).splitlines()
            if line.strip()
        )

    def _release_readme(
        self,
        *,
        tag: str,
        source_sha: str,
        previous_tag: str | None,
        changed_paths: tuple[str, ...],
    ) -> str:
        if previous_tag is not None and not release.TAG_PATTERN.fullmatch(previous_tag):
            raise release.ReleaseError(
                "previous tag must use vMAJOR.MINOR.PATCH"
            )
        changes = release.material_changes(changed_paths)

        def section(title: str, paths: tuple[str, ...]) -> list[str]:
            lines = [f"## {title}", ""]
            if paths:
                lines.extend(f"- {path}" for path in paths)
            else:
                lines.append("- No material source changes detected.")
            lines.append("")
            return lines

        previous = previous_tag or "none (initial release)"
        lines = [
            f"# Guitar Practice System {tag}",
            "",
            f"- Source tag: {tag}",
            f"- Source Git SHA: {source_sha}",
            f"- Project version: {self._project_version()}",
            f"- Previous release tag: {previous}",
            "",
        ]
        lines.extend(
            section(
                "Material backing-track changes",
                changes["backing_tracks"],
            )
        )
        lines.extend(
            section(
                "Material public contract/catalog changes",
                changes["contracts"],
            )
        )
        lines.extend(
            [
                "## Local regeneration",
                "",
                "From the tagged source revision:",
                "",
                "~~~bash",
                (
                    "guitarctl release prepare "
                    f"--tag {tag} --source-sha {source_sha} "
                    "--changed-paths generated/release-changes.txt"
                ),
                (
                    "guitarctl release verify "
                    f"--tag {tag} --source-sha {source_sha}"
                ),
                "~~~",
                "",
                "The release archive is an uncompressed deterministic tar. "
                "Internal files are covered by SHA256SUMS; the archive has "
                "its own .sha256 sidecar.",
                "",
            ]
        )
        return "\n".join(lines)

    def _archive_bytes(self, bundle: WorkspaceTree, root_name: str) -> bytes:
        output = io.BytesIO()
        with tarfile.open(
            fileobj=output,
            mode="w",
            format=tarfile.USTAR_FORMAT,
        ) as archive:
            for path in bundle.list_files("."):
                data = bundle.read_bytes(path)
                info = tarfile.TarInfo(name=f"{root_name}/{path}")
                info.size = len(data)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
        return output.getvalue()

    def prepare(
        self,
        output_dir: str,
        *,
        tag: str,
        source_sha: str,
        previous_tag: str | None = None,
        changed_paths_path: str | None = None,
    ) -> dict[str, Any]:
        project_version = self._project_version()
        release.validate_identity(tag, project_version, source_sha)
        changed_paths = self._changed_paths(changed_paths_path)
        readme = self._release_readme(
            tag=tag,
            source_sha=source_sha,
            previous_tag=previous_tag,
            changed_paths=changed_paths,
        )

        self.tree.remove_tree(output_dir)
        self.tree.make_directory(output_dir)
        root_name = f"guitar-practice-system-{tag}"
        bundle_path = f"{output_dir}/{root_name}"
        PracticeBundleBuilder(self.tree).build(
            bundle_path,
            source_sha=source_sha,
            source_tag=tag,
            release_readme=readme,
        )

        self.tree.write_text(f"{output_dir}/RELEASE.md", readme)
        bundle = self.tree.scoped(bundle_path)
        archive_name = f"{root_name}.tar"
        archive_path = f"{output_dir}/{archive_name}"
        archive_bytes = self._archive_bytes(bundle, root_name)
        self.tree.write_bytes(archive_path, archive_bytes)
        archive_hash = _sha256(archive_bytes)
        checksum_path = f"{archive_path}.sha256"
        self.tree.write_text(
            checksum_path,
            f"{archive_hash}  {archive_name}\n",
        )

        self.verify(
            output_dir,
            tag=tag,
            source_sha=source_sha,
        )
        return {
            "status": "prepared",
            "tag": tag,
            "source_sha": source_sha,
            "bundle": bundle_path,
            "archive": archive_path,
            "archive_sha256": archive_hash,
            "archive_checksum": checksum_path,
            "release_notes": f"{output_dir}/RELEASE.md",
        }

    def _verify_bundle_checksums(self, bundle: WorkspaceTree) -> None:
        lines = bundle.read_text("SHA256SUMS").splitlines()
        declared: dict[str, str] = {}
        for line in lines:
            try:
                digest, path = line.split("  ", 1)
            except ValueError as exc:
                raise release.ReleaseError(
                    f"invalid SHA256SUMS line: {line!r}"
                ) from exc
            if not _CHECKSUM_RE.fullmatch(digest) or not path:
                raise release.ReleaseError(
                    f"invalid SHA256SUMS line: {line!r}"
                )
            if path in declared:
                raise release.ReleaseError(
                    f"duplicate SHA256SUMS path: {path}"
                )
            declared[path] = digest

        expected_paths = set(bundle.list_files(".")) - {"SHA256SUMS"}
        if set(declared) != expected_paths:
            raise release.ReleaseError(
                "SHA256SUMS path set does not match release bundle"
            )
        for path, digest in declared.items():
            if _sha256(bundle.read_bytes(path)) != digest:
                raise release.ReleaseError(
                    f"bundle checksum mismatch: {path}"
                )

    def _verify_archive(
        self,
        archive_bytes: bytes,
        *,
        bundle: WorkspaceTree,
        root_name: str,
    ) -> None:
        expected = {
            f"{root_name}/{path}": bundle.read_bytes(path)
            for path in bundle.list_files(".")
        }
        try:
            with tarfile.open(
                fileobj=io.BytesIO(archive_bytes),
                mode="r:",
            ) as archive:
                members = archive.getmembers()
                actual_names = [member.name for member in members]
                if actual_names != sorted(expected):
                    raise release.ReleaseError(
                        "release archive path set/order does not match bundle"
                    )
                for member in members:
                    if (
                        not member.isfile()
                        or member.mtime != 0
                        or member.uid != 0
                        or member.gid != 0
                        or member.mode != 0o644
                    ):
                        raise release.ReleaseError(
                            f"non-deterministic archive metadata: {member.name}"
                        )
                    stream = archive.extractfile(member)
                    if stream is None or stream.read() != expected[member.name]:
                        raise release.ReleaseError(
                            f"archive content mismatch: {member.name}"
                        )
        except tarfile.TarError as exc:
            raise release.ReleaseError(
                f"invalid release archive: {exc}"
            ) from exc

    def verify(
        self,
        output_dir: str,
        *,
        tag: str,
        source_sha: str,
    ) -> dict[str, Any]:
        project_version = self._project_version()
        release.validate_identity(tag, project_version, source_sha)
        root_name = f"guitar-practice-system-{tag}"
        bundle = self.tree.scoped(f"{output_dir}/{root_name}")

        provenance = bundle.read("provenance.json")
        if provenance.get("sourceGitSha") != source_sha:
            raise release.ReleaseError(
                "release provenance source SHA does not match"
            )
        if provenance.get("sourceGitTag") != tag:
            raise release.ReleaseError(
                "release provenance source tag does not match"
            )
        if provenance.get("projectVersion") != project_version:
            raise release.ReleaseError(
                "release provenance project version does not match"
            )

        artifacts = {
            path: _sha256(bundle.read_bytes(path))
            for path in bundle.list_files(".")
            if path not in {"provenance.json", "SHA256SUMS"}
        }
        if provenance.get("artifacts") != artifacts:
            raise release.ReleaseError(
                "release provenance artifact hashes do not match"
            )
        self._verify_bundle_checksums(bundle)

        archive_name = f"{root_name}.tar"
        archive_path = f"{output_dir}/{archive_name}"
        archive_bytes = self.tree.read_bytes(archive_path)
        digest = _sha256(archive_bytes)
        checksum = self.tree.read_text(f"{archive_path}.sha256")
        if checksum != f"{digest}  {archive_name}\n":
            raise release.ReleaseError(
                "release archive checksum sidecar does not match"
            )
        self._verify_archive(
            archive_bytes,
            bundle=bundle,
            root_name=root_name,
        )

        return {
            "status": "verified",
            "tag": tag,
            "source_sha": source_sha,
            "archive": archive_path,
            "archive_sha256": digest,
        }
