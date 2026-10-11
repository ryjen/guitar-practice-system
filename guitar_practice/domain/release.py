"""Pure release identity and material-change rules."""

from __future__ import annotations

import re
from collections.abc import Iterable

TAG_PATTERN = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ReleaseError(ValueError):
    """A versioned release request is unsafe or internally inconsistent."""


def validate_identity(tag: str, project_version: str, source_sha: str) -> None:
    if not isinstance(tag, str) or not TAG_PATTERN.fullmatch(tag):
        raise ReleaseError("release tag must use vMAJOR.MINOR.PATCH")
    if not isinstance(project_version, str) or tag != f"v{project_version}":
        raise ReleaseError(
            f"release tag {tag!r} does not match project version {project_version!r}"
        )
    if not isinstance(source_sha, str) or not SHA_PATTERN.fullmatch(source_sha):
        raise ReleaseError("source SHA must be a lowercase 40-character Git SHA")


def material_changes(paths: Iterable[str]) -> dict[str, tuple[str, ...]]:
    backing: list[str] = []
    contracts: list[str] = []
    for raw in paths:
        if not isinstance(raw, str):
            raise ReleaseError("changed paths must be strings")
        path = raw.strip()
        if not path:
            continue
        if len(path) > 500 or path.startswith("/") or ".." in path.split("/"):
            raise ReleaseError(f"unsafe changed path: {raw!r}")
        if path.startswith(("backing-tracks/", "catalogs/grooves/")):
            backing.append(path)
        if (
            path.startswith(("contracts/", "catalogs/progressions/"))
            or path == "catalogs/practice-data.json"
        ):
            contracts.append(path)

    return {
        "backing_tracks": tuple(sorted(set(backing))),
        "contracts": tuple(sorted(set(contracts))),
    }
