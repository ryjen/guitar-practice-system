"""Pure immutable realizations derived from canonical Score IR."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Iterable, Mapping
from fractions import Fraction
from typing import Any

from guitar_practice.domain import score


class ScoreRealizationError(ValueError):
    """A requested practice realization cannot be derived safely."""


def _document(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    try:
        score.validate(document)
    except score.ScoreError as exc:
        raise ScoreRealizationError(str(exc)) from exc
    return document


def _fraction(value: Any, label: str) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ScoreRealizationError(f"{label} must be a rational pair")
    numerator, denominator = value
    if denominator <= 0:
        raise ScoreRealizationError(f"{label} denominator must be positive")
    return Fraction(numerator, denominator)


def _location_key(location: Mapping[str, Any]) -> tuple[int, Fraction]:
    bar = location.get("bar")
    if isinstance(bar, bool) or not isinstance(bar, int):
        raise ScoreRealizationError("location bar must be an integer")
    return bar, _fraction(location.get("beat"), "location beat")


def _derived_id(base: str, suffix: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", suffix.casefold()).strip("-")
    available = max(1, 64 - len(normalized) - 1)
    prefix = base[:available].rstrip("-") or "score"
    return f"{prefix}-{normalized}"[:64].rstrip("-")


def _mark_generated(document: dict[str, Any], *, suffix: str, operation: str) -> None:
    source_id = str(document["id"])
    document["id"] = _derived_id(source_id, suffix)
    document["provenance"] = {
        "kind": "generated",
        "source": f"score-realization:{operation}:{source_id}"[:200],
    }


def scale_tempo(document: Mapping[str, Any], factor: float) -> dict[str, Any]:
    """Scale every tempo point proportionally without mutating canonical input."""

    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ScoreRealizationError("tempo factor must be numeric")
    numeric = float(factor)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ScoreRealizationError("tempo factor must be a positive finite number")

    result = _document(document)
    for point in result["tempo_map"]:
        point["bpm"] = point["bpm"] * numeric

    percent = round(numeric * 1000)
    _mark_generated(
        result,
        suffix=f"tempo-{percent}",
        operation=f"tempo:{numeric:g}",
    )
    score.validate(result)
    return result


def _validated_part_ids(
    document: Mapping[str, Any],
    include_part_ids: Iterable[str],
    exclude_part_ids: Iterable[str],
) -> tuple[set[str], set[str]]:
    include = set(include_part_ids)
    exclude = set(exclude_part_ids)
    known = {str(part["id"]) for part in document["parts"]}
    unknown = (include | exclude) - known
    if unknown:
        raise ScoreRealizationError(f"unknown part id(s): {sorted(unknown)}")
    conflict = include & exclude
    if conflict:
        raise ScoreRealizationError(
            f"part id(s) cannot be both included and excluded: {sorted(conflict)}"
        )
    return include, exclude


def _role_is_inferred(part: Mapping[str, Any]) -> bool:
    provenance = part.get("provenance")
    return isinstance(provenance, Mapping) and provenance.get("kind") == "inferred"


def _select_parts(
    document: Mapping[str, Any],
    *,
    default_selected: Any,
    include_part_ids: Iterable[str],
    exclude_part_ids: Iterable[str],
    suffix: str,
    operation: str,
) -> dict[str, Any]:
    result = _document(document)
    include, exclude = _validated_part_ids(
        result,
        include_part_ids,
        exclude_part_ids,
    )
    result["parts"] = [
        part
        for part in result["parts"]
        if part["id"] not in exclude
        and (part["id"] in include or default_selected(part))
    ]
    _mark_generated(result, suffix=suffix, operation=operation)
    score.validate(result)
    return result


def select_backing_parts(
    document: Mapping[str, Any],
    *,
    include_part_ids: Iterable[str] = (),
    exclude_part_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Exclude authoritative guitar parts; retain inferred guitars unless overridden."""

    return _select_parts(
        document,
        default_selected=lambda part: not (
            part["role"] == "guitar" and not _role_is_inferred(part)
        ),
        include_part_ids=include_part_ids,
        exclude_part_ids=exclude_part_ids,
        suffix="backing",
        operation="select-backing",
    )


def select_drum_parts(
    document: Mapping[str, Any],
    *,
    include_part_ids: Iterable[str] = (),
    exclude_part_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Select drum-role parts with explicit include/exclude overrides."""

    return _select_parts(
        document,
        default_selected=lambda part: part["role"] == "drums",
        include_part_ids=include_part_ids,
        exclude_part_ids=exclude_part_ids,
        suffix="drums",
        operation="select-drums",
    )


def _bar_map(
    entries: list[dict[str, Any]],
    *,
    start_bar: int,
    end_bar: int,
) -> list[dict[str, Any]]:
    active: dict[str, Any] | None = None
    for entry in entries:
        if entry["bar"] <= start_bar:
            active = entry
        else:
            break
    if active is None:
        return []

    first = copy.deepcopy(active)
    first["bar"] = 1
    result = [first]
    for entry in entries:
        if start_bar < entry["bar"] <= end_bar:
            mapped = copy.deepcopy(entry)
            mapped["bar"] = entry["bar"] - start_bar + 1
            result.append(mapped)
    return result


def _tempo_map(
    entries: list[dict[str, Any]],
    *,
    start_bar: int,
    end_bar: int,
) -> list[dict[str, Any]]:
    start = (start_bar, Fraction(1, 1))
    active: dict[str, Any] | None = None
    for entry in entries:
        key = _location_key(entry["location"])
        if key <= start:
            active = entry
        else:
            break

    result: list[dict[str, Any]] = []
    if active is not None:
        first = copy.deepcopy(active)
        first["location"] = {"bar": 1, "beat": [1, 1]}
        if _location_key(active["location"]) != start:
            first["provenance"] = {
                "kind": "generated",
                "source": "score-realization:inherited-tempo",
            }
        result.append(first)

    for entry in entries:
        bar, beat = _location_key(entry["location"])
        if (bar, beat) <= start or bar > end_bar:
            continue
        mapped = copy.deepcopy(entry)
        mapped["location"]["bar"] = bar - start_bar + 1
        result.append(mapped)
    return result


def _location_items(
    entries: list[dict[str, Any]],
    *,
    start_bar: int,
    end_bar: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in entries:
        bar, _ = _location_key(entry["location"])
        if not start_bar <= bar <= end_bar:
            continue
        mapped = copy.deepcopy(entry)
        mapped["location"]["bar"] = bar - start_bar + 1
        result.append(mapped)
    return result


def slice_bars(
    document: Mapping[str, Any],
    start_bar: int,
    end_bar: int,
) -> dict[str, Any]:
    """Return a 1-based inclusive structural bar realization."""

    for value, label in ((start_bar, "start bar"), (end_bar, "end bar")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ScoreRealizationError(f"{label} must be a positive integer")
    if end_bar < start_bar:
        raise ScoreRealizationError("end bar must not precede start bar")

    result = _document(document)
    bar_count = len(result["bars"])
    if end_bar > bar_count:
        raise ScoreRealizationError(
            f"bar range exceeds score bar count ({bar_count})"
        )

    sliced_bars: list[dict[str, Any]] = []
    for number, original in enumerate(
        result["bars"][start_bar - 1 : end_bar],
        start=1,
    ):
        bar: dict[str, Any] = {"number": number}
        if "provenance" in original:
            bar["provenance"] = copy.deepcopy(original["provenance"])
        sliced_bars.append(bar)
    result["bars"] = sliced_bars

    result["meter_map"] = _bar_map(
        result["meter_map"],
        start_bar=start_bar,
        end_bar=end_bar,
    )
    result["tempo_map"] = _tempo_map(
        result["tempo_map"],
        start_bar=start_bar,
        end_bar=end_bar,
    )
    if "key_map" in result:
        result["key_map"] = _bar_map(
            result["key_map"],
            start_bar=start_bar,
            end_bar=end_bar,
        )

    for part in result["parts"]:
        events: list[dict[str, Any]] = []
        for event in part["events"]:
            bar, _ = _location_key(event["location"])
            if not start_bar <= bar <= end_bar:
                continue
            mapped = copy.deepcopy(event)
            mapped["location"]["bar"] = bar - start_bar + 1
            events.append(mapped)
        part["events"] = events

    if "sections" in result:
        sections: list[dict[str, Any]] = []
        for section in result["sections"]:
            if section["start_bar"] > end_bar or section["end_bar"] < start_bar:
                continue
            mapped = copy.deepcopy(section)
            mapped["start_bar"] = max(section["start_bar"], start_bar) - start_bar + 1
            mapped["end_bar"] = min(section["end_bar"], end_bar) - start_bar + 1
            sections.append(mapped)
        result["sections"] = sections

    for field in ("rehearsal_marks", "harmony"):
        if field in result:
            result[field] = _location_items(
                result[field],
                start_bar=start_bar,
                end_bar=end_bar,
            )

    _mark_generated(
        result,
        suffix=f"bars-{start_bar}-{end_bar}",
        operation=f"bars:{start_bar}:{end_bar}",
    )
    score.validate(result)
    return result


def resolve_section(
    document: Mapping[str, Any],
    name: str,
) -> Mapping[str, Any]:
    """Resolve one uniquely labelled section without guessing."""

    result = _document(document)
    normalized = name.strip().casefold()
    if not normalized:
        raise ScoreRealizationError("section name must be non-empty")
    matches = [
        section
        for section in result.get("sections", [])
        if section["label"].casefold() == normalized
    ]
    if not matches:
        raise ScoreRealizationError(f"unknown section: {name}")
    if len(matches) > 1:
        raise ScoreRealizationError(
            f"ambiguous section name: {name}; use an explicit bar range"
        )
    return copy.deepcopy(matches[0])


def slice_section(
    document: Mapping[str, Any],
    name: str,
) -> dict[str, Any]:
    """Return one uniquely named section as a structural realization."""

    section = resolve_section(document, name)
    return slice_bars(
        document,
        int(section["start_bar"]),
        int(section["end_bar"]),
    )
