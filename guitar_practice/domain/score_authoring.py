"""Pure immutable authoring transforms over canonical Score IR."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from guitar_practice.domain import score


class ScoreAuthoringError(ValueError):
    """A requested canonical score edit cannot be applied safely."""


@dataclass(frozen=True)
class FormSection:
    id: str
    label: str
    bars: int


def _document(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    try:
        score.validate(document)
    except score.ScoreError as exc:
        raise ScoreAuthoringError(str(exc)) from exc
    return document


def _validate_result(document: dict[str, Any]) -> dict[str, Any]:
    try:
        score.validate(document)
    except score.ScoreError as exc:
        raise ScoreAuthoringError(str(exc)) from exc
    return document


def _has_positioned_content(document: Mapping[str, Any]) -> bool:
    if document.get("harmony") or document.get("rehearsal_marks"):
        return True
    if any(part.get("events") for part in document["parts"]):
        return True
    if any(set(bar) - {"number"} for bar in document["bars"]):
        return True
    if any(entry["bar"] > 1 for entry in document["meter_map"]):
        return True
    if any(entry["location"]["bar"] > 1 for entry in document["tempo_map"]):
        return True
    if any(entry["bar"] > 1 for entry in document.get("key_map", [])):
        return True
    return False


def replace_form(
    document: Mapping[str, Any],
    sections: Sequence[FormSection],
) -> dict[str, Any]:
    """Replace draft bar/section structure without discarding positioned content."""

    result = _document(document)
    if _has_positioned_content(result):
        raise ScoreAuthoringError("score form replacement requires an empty draft")
    if not sections:
        raise ScoreAuthoringError("form must contain at least one section")

    seen: set[str] = set()
    normalized: list[FormSection] = []
    for item in sections:
        if not isinstance(item.id, str) or not item.id:
            raise ScoreAuthoringError("section id must be a non-empty string")
        if item.id in seen:
            raise ScoreAuthoringError(f"duplicate section id: {item.id}")
        if not isinstance(item.label, str) or not item.label.strip():
            raise ScoreAuthoringError("section label must be a non-empty string")
        if isinstance(item.bars, bool) or not isinstance(item.bars, int) or item.bars <= 0:
            raise ScoreAuthoringError("section bar count must be a positive integer")
        seen.add(item.id)
        normalized.append(item)

    total = sum(item.bars for item in normalized)
    result["bars"] = [{"number": number} for number in range(1, total + 1)]

    start = 1
    mapped_sections: list[dict[str, Any]] = []
    for item in normalized:
        end = start + item.bars - 1
        mapped_sections.append(
            {
                "id": item.id,
                "label": item.label.strip(),
                "start_bar": start,
                "end_bar": end,
            }
        )
        start = end + 1
    result["sections"] = mapped_sections
    return _validate_result(result)


def _active_meter(document: Mapping[str, Any], bar: int) -> tuple[int, int]:
    active = document["meter_map"][0]
    for candidate in document["meter_map"][1:]:
        if candidate["bar"] > bar:
            break
        active = candidate
    return int(active["beats"]), int(active["beat_unit"])


def _location_key(entry: Mapping[str, Any]) -> tuple[int, Fraction]:
    location = entry["location"]
    beat = location["beat"]
    return int(location["bar"]), Fraction(int(beat[0]), int(beat[1]))


def replace_harmony(
    document: Mapping[str, Any],
    *,
    start_bar: int,
    end_bar: int,
    bars: Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Replace harmony in one explicit inclusive bar range."""

    result = _document(document)
    for value, label in ((start_bar, "start bar"), (end_bar, "end bar")):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ScoreAuthoringError(f"{label} must be a positive integer")
    if end_bar < start_bar:
        raise ScoreAuthoringError("end bar must not precede start bar")
    if end_bar > len(result["bars"]):
        raise ScoreAuthoringError("harmony range exceeds score bar count")

    expected = end_bar - start_bar + 1
    if len(bars) != expected:
        raise ScoreAuthoringError(f"harmony input must contain exactly {expected} bar cells")

    retained = [
        copy.deepcopy(entry)
        for entry in result.get("harmony", [])
        if not start_bar <= int(entry["location"]["bar"]) <= end_bar
    ]
    generated: list[dict[str, Any]] = []
    for offset, cell in enumerate(bars):
        bar = start_bar + offset
        if not isinstance(cell, Sequence) or isinstance(cell, (str, bytes)):
            raise ScoreAuthoringError("each harmony bar cell must be a sequence of chord symbols")
        symbols = list(cell)
        if not symbols:
            continue
        beats, _ = _active_meter(result, bar)
        count = len(symbols)
        for index, symbol in enumerate(symbols):
            if not isinstance(symbol, str) or not symbol.strip():
                raise ScoreAuthoringError("chord symbols must be non-empty strings")
            beat = Fraction(1, 1) + Fraction(index * beats, count)
            generated.append(
                {
                    "location": {
                        "bar": bar,
                        "beat": [beat.numerator, beat.denominator],
                    },
                    "symbol": symbol.strip(),
                    "provenance": {
                        "kind": "user",
                        "source": "score-authoring:chords",
                    },
                }
            )

    result["harmony"] = sorted(retained + generated, key=_location_key)
    return _validate_result(result)



def _event_sort_key(event: Mapping[str, Any]) -> tuple[int, Fraction, int, int, str]:
    bar, beat = _location_key(event)
    pitch = event.get("pitch")
    midi_hint = -1
    if isinstance(pitch, Mapping):
        step_order = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        step = str(pitch.get("step", "C"))
        alter = pitch.get("alter", 0)
        octave = pitch.get("octave", -1)
        if (
            step in step_order
            and isinstance(alter, int)
            and not isinstance(alter, bool)
            and isinstance(octave, int)
            and not isinstance(octave, bool)
        ):
            midi_hint = 12 * (octave + 1) + step_order[step] + alter
    return (
        bar,
        beat,
        int(event.get("voice", 0)),
        midi_hint,
        str(event.get("kind", "")),
    )


def replace_part_notes(
    document: Mapping[str, Any],
    *,
    part_id: str,
    notes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Replace note events for one explicit part while preserving non-note events."""

    result = _document(document)
    if not isinstance(part_id, str) or not part_id:
        raise ScoreAuthoringError("part id must be a non-empty string")

    matches = [part for part in result["parts"] if part["id"] == part_id]
    if not matches:
        raise ScoreAuthoringError(f"unknown part id: {part_id}")
    if len(matches) != 1:
        raise ScoreAuthoringError(f"ambiguous part id: {part_id}")
    if not isinstance(notes, Sequence) or isinstance(notes, (str, bytes)):
        raise ScoreAuthoringError("notes must be a sequence")

    generated: list[dict[str, Any]] = []
    for index, raw_note in enumerate(notes):
        if not isinstance(raw_note, Mapping):
            raise ScoreAuthoringError(f"notes[{index}] must be an object")
        note = copy.deepcopy(dict(raw_note))
        kind = note.get("kind")
        if kind not in {None, "note"}:
            raise ScoreAuthoringError(f"notes[{index}].kind must be note when present")
        note["kind"] = "note"
        note.setdefault(
            "provenance",
            {"kind": "user", "source": "score-authoring:notes"},
        )
        generated.append(note)

    part = matches[0]
    retained = [
        copy.deepcopy(event)
        for event in part["events"]
        if event.get("kind") != "note"
    ]
    part["events"] = sorted(retained + generated, key=_event_sort_key)
    return _validate_result(result)



def _note_selector(value: Mapping[str, Any], label: str) -> tuple[dict[str, Any], int, dict[str, Any]]:
    if set(value) != {"location", "voice", "pitch"}:
        raise ScoreAuthoringError(
            f"{label} must contain exactly location, voice, and pitch"
        )
    location = value["location"]
    pitch = value["pitch"]
    voice = value["voice"]
    if not isinstance(location, Mapping) or not isinstance(pitch, Mapping):
        raise ScoreAuthoringError(f"{label} location and pitch must be objects")
    if isinstance(voice, bool) or not isinstance(voice, int) or voice <= 0:
        raise ScoreAuthoringError(f"{label}.voice must be a positive integer")
    return copy.deepcopy(dict(location)), voice, copy.deepcopy(dict(pitch))


def _select_note(
    part: Mapping[str, Any],
    selector: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    location, voice, pitch = _note_selector(selector, label)
    matches = [
        event
        for event in part["events"]
        if event.get("kind") == "note"
        and event.get("location") == location
        and event.get("voice") == voice
        and event.get("pitch") == pitch
    ]
    if not matches:
        raise ScoreAuthoringError(f"{label} matched no note")
    if len(matches) != 1:
        raise ScoreAuthoringError(f"{label} matched multiple notes")
    return matches[0]


def apply_note_positions(
    document: Mapping[str, Any],
    *,
    part_id: str,
    positions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply string/fret positions through exact canonical note selectors."""

    result = _document(document)
    matches = [part for part in result["parts"] if part["id"] == part_id]
    if not matches:
        raise ScoreAuthoringError(f"unknown part id: {part_id}")
    if len(matches) != 1:
        raise ScoreAuthoringError(f"ambiguous part id: {part_id}")
    if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes)):
        raise ScoreAuthoringError("positions must be a sequence")

    part = matches[0]
    for index, raw_patch in enumerate(positions):
        if not isinstance(raw_patch, Mapping):
            raise ScoreAuthoringError(f"positions[{index}] must be an object")
        if set(raw_patch) != {"selector", "position"}:
            raise ScoreAuthoringError(
                f"positions[{index}] must contain exactly selector and position"
            )
        position = raw_patch["position"]
        if not isinstance(position, Mapping):
            raise ScoreAuthoringError(f"positions[{index}].position must be an object")
        note = _select_note(
            part,
            raw_patch["selector"],
            label=f"positions[{index}].selector",
        )
        note["position"] = copy.deepcopy(dict(position))
        note.setdefault(
            "provenance",
            {"kind": "user", "source": "score-authoring:voicing"},
        )

    return _validate_result(result)
