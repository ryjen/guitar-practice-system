"""Pure validation/rendering rules for the public practice-data catalog."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Mapping


class CatalogError(ValueError):
    """Practice-data catalog is invalid or inconsistent."""


def _require_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{path} must be a non-empty string")
    return value


def validate_catalog(data: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate structure and return repository-relative source references."""

    if data.get("schemaVersion") != 1:
        raise CatalogError("schemaVersion must be 1")

    allocations = data.get("durationAllocations")
    if not isinstance(allocations, dict) or set(allocations) != {"15", "30", "45"}:
        raise CatalogError(
            "durationAllocations must define 15, 30, and 45 minute plans"
        )
    for duration, values in allocations.items():
        if (
            not isinstance(values, list)
            or len(values) != 3
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                for value in values
            )
        ):
            raise CatalogError(
                f"durationAllocations.{duration} must contain three positive integers"
            )
        if sum(values) != int(duration):
            raise CatalogError(
                f"durationAllocations.{duration} must sum to {duration}"
            )

    sessions = data.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise CatalogError("sessions must be a non-empty list")

    source_paths: list[str] = []
    session_ids: set[str] = set()
    for index, session in enumerate(sessions):
        path = f"sessions[{index}]"
        if not isinstance(session, dict):
            raise CatalogError(f"{path} must be an object")
        session_id = _require_text(session.get("id"), f"{path}.id")
        if session_id in session_ids:
            raise CatalogError(f"duplicate session id: {session_id}")
        session_ids.add(session_id)

        for field in ("technique", "key", "meter", "title", "intent", "space"):
            _require_text(session.get(field), f"{path}.{field}")
        for field in ("useCase", "gear"):
            value = session.get(field)
            if not isinstance(value, dict):
                raise CatalogError(f"{path}.{field} must be an object")
            _require_text(value.get("title"), f"{path}.{field}.title")
            _require_text(value.get("copy"), f"{path}.{field}.copy")

        tempo = session.get("tempo")
        if not isinstance(tempo, dict):
            raise CatalogError(f"{path}.tempo must be an object")
        slow, medium, fast = (
            tempo.get(name) for name in ("slow", "medium", "fast")
        )
        if not all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and 30 <= value <= 240
            for value in (slow, medium, fast)
        ):
            raise CatalogError(
                f"{path}.tempo values must be integer BPM values from 30 to 240"
            )
        if not slow < medium < fast:
            raise CatalogError(
                f"{path}.tempo must be strictly increasing slow < medium < fast"
            )
        _require_text(tempo.get("pulse"), f"{path}.tempo.pulse")
        beats_per_bar = tempo.get("beatsPerBar")
        if (
            isinstance(beats_per_bar, bool)
            or not isinstance(beats_per_bar, int)
            or beats_per_bar <= 0
        ):
            raise CatalogError(
                f"{path}.tempo.beatsPerBar must be a positive integer"
            )

        stages = session.get("stages")
        if not isinstance(stages, list) or len(stages) != 3:
            raise CatalogError(
                f"{path}.stages must contain exactly three stages"
            )
        for stage_index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                raise CatalogError(
                    f"{path}.stages[{stage_index}] must be an object"
                )
            _require_text(
                stage.get("title"),
                f"{path}.stages[{stage_index}].title",
            )
            _require_text(
                stage.get("copy"),
                f"{path}.stages[{stage_index}].copy",
            )

        source = session.get("source")
        if not isinstance(source, dict):
            raise CatalogError(f"{path}.source must be an object")
        _require_text(source.get("label"), f"{path}.source.label")
        source_path = _require_text(
            source.get("path"),
            f"{path}.source.path",
        )
        relative = PurePosixPath(source_path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or source_path.startswith(("http://", "https://"))
        ):
            raise CatalogError(
                f"{path}.source.path must be a repository-relative path"
            )
        source_paths.append(relative.as_posix())

    techniques = data.get("techniques")
    if not isinstance(techniques, list) or not techniques:
        raise CatalogError("techniques must be a non-empty list")
    technique_ids: set[str] = set()
    for index, technique in enumerate(techniques):
        path = f"techniques[{index}]"
        if not isinstance(technique, dict):
            raise CatalogError(f"{path} must be an object")
        technique_id = _require_text(technique.get("id"), f"{path}.id")
        if technique_id in technique_ids:
            raise CatalogError(f"duplicate technique id: {technique_id}")
        technique_ids.add(technique_id)
        _require_text(technique.get("name"), f"{path}.name")
        _require_text(technique.get("copy"), f"{path}.copy")
        items = technique.get("items")
        if not isinstance(items, list) or not items:
            raise CatalogError(f"{path}.items must be a non-empty list")
        for item_index, item in enumerate(items):
            _require_text(item, f"{path}.items[{item_index}]")

    return tuple(source_paths)


def render_catalog(data: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(data),
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    ) + "\n"
