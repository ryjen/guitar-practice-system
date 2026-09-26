"""Pure practice transforms over canonical Score IR."""

from __future__ import annotations

import copy
import math
from collections.abc import Iterable
from typing import Any

from guitar_practice.domain import score


class ScoreTransformError(ValueError):
    """A requested practice transform cannot preserve Score IR semantics."""


def _validated(document: dict[str, Any]) -> dict[str, Any]:
    score.validate(document)
    return copy.deepcopy(document)


def scale_tempo(document: dict[str, Any], factor: float) -> dict[str, Any]:
    """Return a validated copy with every tempo event scaled proportionally."""

    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ScoreTransformError("tempo factor must be numeric")
    numeric = float(factor)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ScoreTransformError("tempo factor must be a positive finite number")

    realized = _validated(document)
    for item in realized["tempo_map"]:
        item["bpm"] = item["bpm"] * numeric
        item["provenance"] = {
            "kind": "generated",
            "source": f"practice-tempo:{numeric:g}",
        }
    score.validate(realized)
    return realized


def _ids(
    document: dict[str, Any],
    include_part_ids: Iterable[str],
    exclude_part_ids: Iterable[str],
) -> tuple[set[str], set[str]]:
    include = set(include_part_ids)
    exclude = set(exclude_part_ids)
    known = {part["id"] for part in document["parts"]}
    unknown = (include | exclude) - known
    if unknown:
        raise ScoreTransformError(f"unknown part id(s): {sorted(unknown)}")
    conflict = include & exclude
    if conflict:
        raise ScoreTransformError(
            f"part id(s) cannot be both included and excluded: {sorted(conflict)}"
        )
    return include, exclude


def _strong_role(part: dict[str, Any], role: str) -> bool:
    if part.get("role") != role:
        return False
    provenance = part.get("provenance")
    return not (
        isinstance(provenance, dict)
        and provenance.get("kind") == "inferred"
    )


def select_backing_parts(
    document: dict[str, Any],
    *,
    include_part_ids: Iterable[str] = (),
    exclude_part_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select accompaniment, conservatively excluding strongly identified guitar parts."""

    score.validate(document)
    include, exclude = _ids(document, include_part_ids, exclude_part_ids)
    return [
        copy.deepcopy(part)
        for part in document["parts"]
        if part["id"] not in exclude
        and (
            part["id"] in include
            or not _strong_role(part, "guitar")
        )
    ]


def select_drum_parts(
    document: dict[str, Any],
    *,
    include_part_ids: Iterable[str] = (),
    exclude_part_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select drum parts, allowing explicit inclusion of ambiguous parts."""

    score.validate(document)
    include, exclude = _ids(document, include_part_ids, exclude_part_ids)
    return [
        copy.deepcopy(part)
        for part in document["parts"]
        if part["id"] not in exclude
        and (
            part["id"] in include
            or part.get("role") == "drums"
        )
    ]


def resolve_section(document: dict[str, Any], name: str) -> dict[str, Any]:
    """Resolve one uniquely labelled section without guessing."""

    score.validate(document)
    normalized = name.strip().casefold()
    if not normalized:
        raise ScoreTransformError("section name must be non-empty")
    matches = [
        section
        for section in document.get("sections", [])
        if section["label"].casefold() == normalized
    ]
    if not matches:
        raise ScoreTransformError(f"unknown section: {name}")
    if len(matches) > 1:
        raise ScoreTransformError(f"ambiguous section name: {name}; use --bars")
    return copy.deepcopy(matches[0])


def _active_bar_entry(
    entries: list[dict[str, Any]],
    *,
    bar: int,
) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    for item in entries:
        if item["bar"] > bar:
            break
        active = item
    return copy.deepcopy(active) if active is not None else None


def _active_location_entry(
    entries: list[dict[str, Any]],
    *,
    bar: int,
) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    for item in entries:
        location = item["location"]
        if (location["bar"], tuple(location["beat"])) > (bar, (1, 1)):
            break
        active = item
    return copy.deepcopy(active) if active is not None else None


def _remap_location(item: dict[str, Any], start_bar: int) -> dict[str, Any]:
    mapped = copy.deepcopy(item)
    mapped["location"]["bar"] -= start_bar - 1
    return mapped


def slice_bars(
    document: dict[str, Any],
    start_bar: int,
    end_bar: int,
) -> dict[str, Any]:
    """Return a 1-based inclusive structural bar slice remapped to bar one."""

    score.validate(document)
    for value, label in ((start_bar, "start bar"), (end_bar, "end bar")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ScoreTransformError(f"{label} must be a positive integer")
    if end_bar < start_bar:
        raise ScoreTransformError("end bar must not precede start bar")

    bar_count = len(document["bars"])
    if end_bar > bar_count:
        raise ScoreTransformError(f"bar range exceeds score bar count ({bar_count})")

    selected_bars = document["bars"][start_bar - 1 : end_bar]
    if any(
        set(bar) & {"repeat_start", "repeat_end", "ending_numbers"}
        for bar in selected_bars
    ):
        raise ScoreTransformError(
            "practice slicing of canonical repeat/ending bars is not supported; "
            "expand playback form before slicing"
        )

    result = _validated(document)
    result["bars"] = [
        {
            "number": index,
            **(
                {"provenance": copy.deepcopy(bar["provenance"])}
                if "provenance" in bar
                else {}
            ),
        }
        for index, bar in enumerate(selected_bars, start=1)
    ]

    active_meter = _active_bar_entry(document["meter_map"], bar=start_bar)
    assert active_meter is not None
    active_meter["bar"] = 1
    meter_map = [active_meter]
    meter_map.extend(
        {
            **copy.deepcopy(item),
            "bar": item["bar"] - start_bar + 1,
        }
        for item in document["meter_map"]
        if start_bar < item["bar"] <= end_bar
    )
    result["meter_map"] = meter_map

    active_tempo = _active_location_entry(document["tempo_map"], bar=start_bar)
    tempo_map: list[dict[str, Any]] = []
    if active_tempo is not None:
        active_tempo["location"] = {"bar": 1, "beat": [1, 1]}
        tempo_map.append(active_tempo)
    for item in document["tempo_map"]:
        location = item["location"]
        if start_bar <= location["bar"] <= end_bar:
            mapped = _remap_location(item, start_bar)
            if (
                tempo_map
                and mapped["location"] == tempo_map[-1]["location"]
            ):
                tempo_map[-1] = mapped
            else:
                tempo_map.append(mapped)
    result["tempo_map"] = tempo_map

    if "key_map" in document:
        active_key = _active_bar_entry(document["key_map"], bar=start_bar)
        key_map: list[dict[str, Any]] = []
        if active_key is not None:
            active_key["bar"] = 1
            key_map.append(active_key)
        for item in document["key_map"]:
            if start_bar < item["bar"] <= end_bar:
                mapped = copy.deepcopy(item)
                mapped["bar"] -= start_bar - 1
                key_map.append(mapped)
        result["key_map"] = key_map

    parts: list[dict[str, Any]] = []
    for part in document["parts"]:
        mapped_part = copy.deepcopy(part)
        mapped_part["events"] = [
            _remap_location(event, start_bar)
            for event in part["events"]
            if start_bar <= event["location"]["bar"] <= end_bar
        ]
        parts.append(mapped_part)
    result["parts"] = parts

    sections: list[dict[str, Any]] = []
    for section in document.get("sections", []):
        if section["start_bar"] <= end_bar and section["end_bar"] >= start_bar:
            mapped = copy.deepcopy(section)
            mapped["start_bar"] = max(section["start_bar"], start_bar) - start_bar + 1
            mapped["end_bar"] = min(section["end_bar"], end_bar) - start_bar + 1
            sections.append(mapped)
    if "sections" in result:
        result["sections"] = sections

    for field in ("rehearsal_marks", "harmony"):
        if field in document:
            result[field] = [
                _remap_location(item, start_bar)
                for item in document[field]
                if start_bar <= item["location"]["bar"] <= end_bar
            ]

    score.validate(result)
    return result


def slice_section(document: dict[str, Any], name: str) -> dict[str, Any]:
    section = resolve_section(document, name)
    return slice_bars(document, section["start_bar"], section["end_bar"])
