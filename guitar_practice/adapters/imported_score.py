"""Transient MusicXML import model and deterministic track-role classification."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class TrackRole(StrEnum):
    GUITAR = "guitar"
    BASS = "bass"
    DRUMS = "drums"
    KEYS = "keys"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClassificationSource(StrEnum):
    EXPLICIT = "explicit"
    INSTRUMENT = "instrument"
    MIDI = "midi"
    PERCUSSION = "percussion"
    NAME_HEURISTIC = "name-heuristic"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TrackClassification:
    role: TrackRole
    source: ClassificationSource


@dataclass(frozen=True)
class ImportedTempoPoint:
    position: float
    bpm: float

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("tempo position must be non-negative")
        if self.bpm <= 0:
            raise ValueError("tempo BPM must be positive")


@dataclass(frozen=True)
class ImportedMeterPoint:
    position: float
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("meter position must be non-negative")
        if self.numerator <= 0:
            raise ValueError("meter numerator must be positive")
        if self.denominator <= 0 or self.denominator & (self.denominator - 1):
            raise ValueError("meter denominator must be a positive power of two")


@dataclass(frozen=True)
class ImportedNoteEvent:
    position: float
    duration: float
    midi_note: int
    velocity: int = 80

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("note position must be non-negative")
        if self.duration <= 0:
            raise ValueError("note duration must be positive")
        if isinstance(self.midi_note, bool) or not 0 <= self.midi_note <= 127:
            raise ValueError("MIDI note must be between 0 and 127")
        if isinstance(self.velocity, bool) or not 1 <= self.velocity <= 127:
            raise ValueError("note velocity must be between 1 and 127")


@dataclass(frozen=True)
class ImportedSection:
    name: str
    start_bar: int
    end_bar: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("section name must be non-empty")


@dataclass(frozen=True)
class ImportedTrack:
    id: str
    name: str
    classification: TrackClassification
    instrument_name: str | None = None
    midi_program: int | None = None
    midi_channel: int | None = None
    is_percussion: bool = False
    notes: tuple[ImportedNoteEvent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _validate_id(self.id, "track id")
        if not isinstance(self.name, str):
            raise ValueError("track name must be a string")
        if self.midi_program is not None and not 0 <= self.midi_program <= 127:
            raise ValueError("MIDI program must be between 0 and 127")
        if self.midi_channel is not None and not 1 <= self.midi_channel <= 16:
            raise ValueError("MIDI channel must be between 1 and 16")
        if tuple(sorted(self.notes, key=lambda note: note.position)) != self.notes:
            raise ValueError("track notes must be ordered by position")


@dataclass(frozen=True)
class ImportedScore:
    source_id: str
    title: str
    tracks: tuple[ImportedTrack, ...] = field(default_factory=tuple)
    tempo_map: tuple[ImportedTempoPoint, ...] = field(default_factory=tuple)
    meter_map: tuple[ImportedMeterPoint, ...] = field(default_factory=tuple)
    duration_quarters: float | None = None
    bar_boundaries: tuple[float, ...] = field(default_factory=tuple)
    sections: tuple[ImportedSection, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _validate_id(self.source_id, "source id")
        if not isinstance(self.title, str):
            raise ValueError("imported score title must be a string")
        track_ids = [track.id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("imported score track ids must be unique")
        if tuple(sorted(self.tempo_map, key=lambda item: item.position)) != self.tempo_map:
            raise ValueError("tempo map must be ordered by position")
        if tuple(sorted(self.meter_map, key=lambda item: item.position)) != self.meter_map:
            raise ValueError("meter map must be ordered by position")
        if self.duration_quarters is not None:
            duration = self.duration_quarters
            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(float(duration))
                or duration <= 0
            ):
                raise ValueError("imported score duration must be a positive finite number")
        if self.bar_boundaries:
            boundaries = self.bar_boundaries
            if self.duration_quarters is None:
                raise ValueError("bar boundaries require structural duration")
            if boundaries[0] != 0.0:
                raise ValueError("bar boundaries must start at zero")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in boundaries
            ):
                raise ValueError("bar boundaries must be finite numbers")
            if any(right <= left for left, right in zip(boundaries, boundaries[1:])):
                raise ValueError("bar boundaries must increase strictly")
            if not math.isclose(float(boundaries[-1]), float(self.duration_quarters)):
                raise ValueError("bar boundaries must end at structural duration")
        if self.sections:
            if len(self.bar_boundaries) < 2:
                raise ValueError("sections require structural bar boundaries")
            bar_count = len(self.bar_boundaries) - 1
            previous_end = 0
            for section in self.sections:
                if section.start_bar < 1 or section.end_bar < section.start_bar:
                    raise ValueError("section bar range must be positive and ordered")
                if section.end_bar > bar_count:
                    raise ValueError("section exceeds structural bar count")
                if section.start_bar <= previous_end:
                    raise ValueError("sections must be ordered and non-overlapping")
                previous_end = section.end_bar


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or _SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"{label} must contain only letters, digits, '.', '_' or '-'")


def _instrument_role(instrument_name: str | None) -> TrackRole | None:
    if not instrument_name:
        return None
    value = instrument_name.casefold()
    if "bass" in value:
        return TrackRole.BASS
    if "guitar" in value:
        return TrackRole.GUITAR
    if any(token in value for token in ("drum", "percussion")):
        return TrackRole.DRUMS
    if any(token in value for token in ("piano", "organ", "keyboard", "keys")):
        return TrackRole.KEYS
    return None


def _midi_role(program: int | None) -> TrackRole | None:
    if program is None:
        return None
    if 24 <= program <= 31:
        return TrackRole.GUITAR
    if 32 <= program <= 39:
        return TrackRole.BASS
    if 0 <= program <= 7 or 16 <= program <= 23:
        return TrackRole.KEYS
    return None


def _name_role(name: str) -> TrackRole | None:
    value = name.casefold()
    if "bass" in value:
        return TrackRole.BASS
    if any(token in value for token in ("drum", "percussion", "kit")):
        return TrackRole.DRUMS
    if "guitar" in value or "gtr" in value:
        return TrackRole.GUITAR
    if any(token in value for token in ("piano", "organ", "keyboard", "keys")):
        return TrackRole.KEYS
    return None


def classify_track(
    *,
    name: str,
    instrument_name: str | None,
    midi_program: int | None,
    is_percussion: bool,
    override: TrackRole | None = None,
) -> TrackClassification:
    """Classify a track without turning weak inference into destructive authority."""

    if override is not None:
        return TrackClassification(override, ClassificationSource.EXPLICIT)

    instrument_role = _instrument_role(instrument_name)
    if instrument_role is not None:
        return TrackClassification(instrument_role, ClassificationSource.INSTRUMENT)

    midi_role = _midi_role(midi_program)
    if midi_role is not None:
        return TrackClassification(midi_role, ClassificationSource.MIDI)

    if is_percussion:
        return TrackClassification(TrackRole.DRUMS, ClassificationSource.PERCUSSION)

    name_role = _name_role(name)
    if name_role is not None:
        return TrackClassification(name_role, ClassificationSource.NAME_HEURISTIC)

    return TrackClassification(TrackRole.UNKNOWN, ClassificationSource.UNKNOWN)


