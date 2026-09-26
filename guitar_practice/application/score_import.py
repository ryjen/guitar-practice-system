"""Application orchestration for importing external scores into canonical Score IR."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import PurePosixPath
from typing import Any, Mapping

from guitar_practice.adapters.imported_score import (
    ClassificationSource,
    ImportedMeterPoint,
    ImportedNoteEvent,
    ImportedScore,
    ImportedTrack,
)
from guitar_practice.adapters.musicxml_import import parse_musicxml
from guitar_practice.application.ports import JsonDocumentStore, ScoreConverter
from guitar_practice.domain import score

SUPPORTED_SCORE_SUFFIXES = frozenset(
    {".gp", ".gp3", ".gp4", ".gp5", ".gpx", ".musicxml", ".xml"}
)


class UnsupportedScoreFormat(ValueError):
    """The source extension is not accepted by the score import boundary."""


class ScoreImportError(ValueError):
    """Imported musical data cannot be represented safely in Score IR."""


def _path(source_path: str) -> PurePosixPath:
    return PurePosixPath(source_path.replace("\\", "/"))


def source_id_for(source_path: str) -> str:
    stem = _path(source_path).stem.casefold()
    safe = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return safe[:64] or "score"


def validate_source_format(source_path: str) -> None:
    suffix = _path(source_path).suffix.casefold()
    if suffix not in SUPPORTED_SCORE_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SCORE_SUFFIXES))
        raise UnsupportedScoreFormat(
            f"unsupported score format {suffix or '<none>'}; expected one of: {supported}"
        )


def _exact_fraction(value: int | float, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreImportError(f"{label} must be numeric")
    if not math.isfinite(float(value)):
        raise ScoreImportError(f"{label} must be finite")
    result = Fraction(str(value)).limit_denominator(65_536)
    if not math.isclose(float(result), float(value), rel_tol=0.0, abs_tol=1e-9):
        raise ScoreImportError(f"{label} cannot be represented exactly enough")
    return result


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _boundaries(imported: ImportedScore) -> tuple[Fraction, ...]:
    values = tuple(
        _exact_fraction(value, f"bar_boundaries[{index}]")
        for index, value in enumerate(imported.bar_boundaries)
    )
    if len(values) < 2 or values[0] != 0:
        raise ScoreImportError("imported score must provide structural bar boundaries")
    return values


def _bar_for_position(position: Fraction, boundaries: tuple[Fraction, ...]) -> int:
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=True), start=1):
        if start <= position < end:
            return index
    raise ScoreImportError(f"position {float(position):g} is outside the structural score")


def _bar_for_boundary(position: Fraction, boundaries: tuple[Fraction, ...]) -> int:
    for index, boundary in enumerate(boundaries[:-1], start=1):
        if position == boundary:
            return index
    raise ScoreImportError("meter changes must occur at structural bar boundaries")


def _meter_map(
    imported: ImportedScore,
    boundaries: tuple[Fraction, ...],
) -> list[dict[str, Any]]:
    points = imported.meter_map or (
        ImportedMeterPoint(position=0.0, numerator=4, denominator=4),
    )
    result: list[dict[str, Any]] = []
    for point in points:
        position = _exact_fraction(point.position, "meter position")
        bar = _bar_for_boundary(position, boundaries)
        entry = {
            "bar": bar,
            "beats": point.numerator,
            "beat_unit": point.denominator,
            "provenance": {"kind": "imported", "source": "musicxml:meter"},
        }
        if result and result[-1]["bar"] == bar:
            result[-1] = entry
        else:
            result.append(entry)
    if not result or result[0]["bar"] != 1:
        raise ScoreImportError("imported meter map must establish bar 1")
    return result


def _active_meter(bar: int, meters: list[dict[str, Any]]) -> tuple[int, int]:
    active = meters[0]
    for candidate in meters[1:]:
        if candidate["bar"] > bar:
            break
        active = candidate
    return int(active["beats"]), int(active["beat_unit"])


def _location(
    position_quarters: Fraction,
    boundaries: tuple[Fraction, ...],
    meters: list[dict[str, Any]],
) -> dict[str, Any]:
    bar = _bar_for_position(position_quarters, boundaries)
    _, beat_unit = _active_meter(bar, meters)
    offset_quarters = position_quarters - boundaries[bar - 1]
    beat = Fraction(1, 1) + offset_quarters * beat_unit / 4
    return {"bar": bar, "beat": _pair(beat)}


_PITCHES = (
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
)


def _pitch(midi_note: int) -> dict[str, Any]:
    step, alter = _PITCHES[midi_note % 12]
    return {"step": step, "alter": alter, "octave": midi_note // 12 - 1}


def _classification_provenance(track: ImportedTrack) -> dict[str, Any]:
    source = f"track-role:{track.classification.source.value}"
    if track.classification.source in {
        ClassificationSource.NAME_HEURISTIC,
        ClassificationSource.UNKNOWN,
    }:
        return {"kind": "inferred", "source": source, "confidence": 0.5}
    return {"kind": "imported", "source": source}


def _part_id(track: ImportedTrack, used: set[str], index: int) -> str:
    basis = track.id or track.name or f"part-{index}"
    base = re.sub(r"[^a-z0-9]+", "-", basis.casefold()).strip("-")[:48] or f"part-{index}"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base[:54]}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _note_events(
    note: ImportedNoteEvent,
    boundaries: tuple[Fraction, ...],
    meters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    start = _exact_fraction(note.position, "note position")
    remaining = _exact_fraction(note.duration, "note duration")
    if remaining <= 0:
        raise ScoreImportError("note duration must be positive")

    segments: list[tuple[Fraction, Fraction]] = []
    cursor = start
    while remaining > 0:
        bar = _bar_for_position(cursor, boundaries)
        end = boundaries[bar]
        duration = min(remaining, end - cursor)
        if duration <= 0:
            raise ScoreImportError("note cannot advance across structural bars")
        segments.append((cursor, duration))
        cursor += duration
        remaining -= duration

    events: list[dict[str, Any]] = []
    for index, (position, duration_quarters) in enumerate(segments):
        event: dict[str, Any] = {
            "kind": "note",
            "location": _location(position, boundaries, meters),
            "duration": _pair(duration_quarters / 4),
            "voice": 1,
            "pitch": _pitch(note.midi_note),
            "provenance": {"kind": "imported", "source": "musicxml:note"},
        }
        if len(segments) > 1:
            if index == 0:
                event["tie"] = "start"
            elif index == len(segments) - 1:
                event["tie"] = "stop"
            else:
                event["tie"] = "continue"
        events.append(event)
    return events


def imported_to_score_ir(
    imported: ImportedScore,
    *,
    source_path: str,
    converter: str,
) -> dict[str, Any]:
    """Map transient import DTOs into the one persisted canonical Score IR."""

    boundaries = _boundaries(imported)
    meters = _meter_map(imported, boundaries)
    score_id = source_id_for(source_path)
    source_label = f"{converter}:{score_id}"[:200]

    tempo_map: list[dict[str, Any]] = []
    for point in imported.tempo_map:
        position = _exact_fraction(point.position, "tempo position")
        tempo_map.append(
            {
                "location": _location(position, boundaries, meters),
                "bpm": point.bpm,
                "beat_unit": [1, 4],
                "provenance": {"kind": "imported", "source": "musicxml:tempo"},
            }
        )

    used_ids: set[str] = set()
    parts: list[dict[str, Any]] = []
    for index, track in enumerate(imported.tracks, start=1):
        part_id = _part_id(track, used_ids, index)
        role = track.classification.role.value
        instrument_name = (track.instrument_name or track.name or "Unknown instrument").strip()
        family = role if role not in {"unknown"} else "other"
        events: list[dict[str, Any]] = []
        for note in track.notes:
            events.extend(_note_events(note, boundaries, meters))
        parts.append(
            {
                "id": part_id,
                "name": track.name.strip() or part_id,
                "role": role,
                "instrument": {"name": instrument_name, "family": family},
                "events": events,
                "provenance": _classification_provenance(track),
            }
        )

    section_ids: set[str] = set()
    sections: list[dict[str, Any]] = []
    rehearsal_marks: list[dict[str, Any]] = []
    for index, section in enumerate(imported.sections, start=1):
        raw_id = re.sub(r"[^a-z0-9]+", "-", section.name.casefold()).strip("-") or f"section-{index}"
        section_id = raw_id[:48]
        suffix = 2
        while section_id in section_ids:
            section_id = f"{raw_id[:54]}-{suffix}"
            suffix += 1
        section_ids.add(section_id)
        sections.append(
            {
                "id": section_id,
                "label": section.name,
                "start_bar": section.start_bar,
                "end_bar": section.end_bar,
                "provenance": {"kind": "imported", "source": "musicxml:rehearsal"},
            }
        )
        rehearsal_marks.append(
            {
                "location": {"bar": section.start_bar, "beat": [1, 1]},
                "label": section.name,
                "provenance": {"kind": "imported", "source": "musicxml:rehearsal"},
            }
        )

    document: dict[str, Any] = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": score_id,
        "metadata": {
            "title": imported.title.strip() or score_id,
            "source": {"kind": "imported", "id": score_id},
            "provenance": {"kind": "imported", "source": source_label},
        },
        "bars": [{"number": number} for number in range(1, len(boundaries))],
        "meter_map": meters,
        "tempo_map": tempo_map,
        "parts": parts,
        "provenance": {"kind": "imported", "source": source_label},
    }
    if sections:
        document["sections"] = sections
        document["rehearsal_marks"] = rehearsal_marks

    score.validate(document)
    return document


@dataclass(frozen=True)
class ImportScore:
    converter: ScoreConverter
    documents: JsonDocumentStore

    def execute(self, source_path: str, output_path: str) -> Mapping[str, Any]:
        validate_source_format(source_path)
        converted = self.converter.convert(source_path)
        imported = parse_musicxml(
            converted.musicxml,
            source_id=source_id_for(source_path),
        )
        document = imported_to_score_ir(
            imported,
            source_path=source_path,
            converter=converted.converter,
        )
        self.documents.write(output_path, document)
        return document
