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


def bar_range(value: str) -> tuple[int, int]:
    """Parse a 1-based inclusive bar range such as 42:58."""

    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("bar range must use START:END")
    try:
        start, end = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("bar range values must be integers") from exc
    if start < 1 or end < 1:
        raise ValueError("bar range values must be positive")
    if end < start:
        raise ValueError("bar range end must not precede start")
    return start, end
