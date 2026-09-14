"""Shared CLI parsing rules for score-derived practice artifacts."""

from __future__ import annotations

from pathlib import PurePosixPath


class PracticePathError(ValueError):
    """A practice-artifact path crossed the explicit workspace boundary."""


def workspace_relative(path: str, *, label: str) -> str:
    value = PurePosixPath(path.replace("\\", "/"))
    if value.is_absolute() or not value.parts or ".." in value.parts:
        raise PracticePathError(f"{label} must be a workspace-relative path")
    return value.as_posix()


def tempo_factor(value: str) -> float:
    normalized = value.strip()
    if not normalized.endswith("%"):
        raise ValueError("tempo must be a percentage such as 75%")
    try:
        percent = float(normalized[:-1])
    except ValueError as exc:
        raise ValueError("tempo percentage must be numeric") from exc
    factor = percent / 100.0
    if factor <= 0:
        raise ValueError("tempo percentage must be positive")
    return factor
