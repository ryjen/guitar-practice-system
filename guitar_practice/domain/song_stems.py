"""Pure practice-tempo realization and imported-song stem selection."""

from __future__ import annotations

import math
from dataclasses import replace
from collections.abc import Callable, Iterable

from guitar_practice.domain.song import (
    ClassificationSource,
    MeterPoint,
    Song,
    SongSection,
    SongTrack,
    TempoPoint,
    TrackRole,
)

_STRONG_CLASSIFICATION_SOURCES = frozenset(
    {
        ClassificationSource.EXPLICIT,
        ClassificationSource.INSTRUMENT,
        ClassificationSource.MIDI,
        ClassificationSource.PERCUSSION,
    }
)


def scale_tempo(song: Song, factor: float) -> Song:
    """Return a derived song with every tempo point scaled proportionally."""

    if not isinstance(factor, (int, float)) or isinstance(factor, bool):
        raise ValueError("tempo factor must be numeric")
    numeric = float(factor)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError("tempo factor must be a positive finite number")
    return replace(
        song,
        tempo_map=tuple(
            TempoPoint(position=point.position, bpm=point.bpm * numeric)
            for point in song.tempo_map
        ),
    )


def _validated_ids(
    song: Song,
    include_track_ids: Iterable[str],
    exclude_track_ids: Iterable[str],
) -> tuple[set[str], set[str]]:
    include = set(include_track_ids)
    exclude = set(exclude_track_ids)
    known = {track.id for track in song.tracks}
    unknown = (include | exclude) - known
    if unknown:
        raise ValueError(f"unknown track id(s): {sorted(unknown)}")
    conflict = include & exclude
    if conflict:
        raise ValueError(f"track id(s) cannot be both included and excluded: {sorted(conflict)}")
    return include, exclude


def _select(
    song: Song,
    *,
    default_selected: Callable[[SongTrack], bool],
    include_track_ids: Iterable[str],
    exclude_track_ids: Iterable[str],
) -> tuple[SongTrack, ...]:
    include, exclude = _validated_ids(song, include_track_ids, exclude_track_ids)
    return tuple(
        track
        for track in song.tracks
        if track.id not in exclude and (track.id in include or default_selected(track))
    )


def select_backing_tracks(
    song: Song,
    *,
    include_track_ids: Iterable[str] = (),
    exclude_track_ids: Iterable[str] = (),
) -> tuple[SongTrack, ...]:
    """Select accompaniment, excluding guitar-role tracks unless explicitly included."""

    return _select(
        song,
        default_selected=lambda track: not (
            track.classification.role is TrackRole.GUITAR
            and track.classification.source in _STRONG_CLASSIFICATION_SOURCES
        ),
        include_track_ids=include_track_ids,
        exclude_track_ids=exclude_track_ids,
    )


def select_drum_tracks(
    song: Song,
    *,
    include_track_ids: Iterable[str] = (),
    exclude_track_ids: Iterable[str] = (),
) -> tuple[SongTrack, ...]:
    """Select drum-role tracks, allowing explicit inclusion of ambiguous tracks."""

    return _select(
        song,
        default_selected=lambda track: track.classification.role is TrackRole.DRUMS,
        include_track_ids=include_track_ids,
        exclude_track_ids=exclude_track_ids,
    )


def slice_bars(song: Song, start_bar: int, end_bar: int) -> Song:
    """Return a 1-based inclusive structural bar slice remapped to position zero."""

    for value, label in ((start_bar, "start bar"), (end_bar, "end bar")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{label} must be a positive integer")
    if end_bar < start_bar:
        raise ValueError("end bar must not precede start bar")
    if len(song.bar_boundaries) < 2:
        raise ValueError("song has no structural bar boundaries")

    bar_count = len(song.bar_boundaries) - 1
    if end_bar > bar_count:
        raise ValueError(f"bar range exceeds song bar count ({bar_count})")

    left = song.bar_boundaries[start_bar - 1]
    right = song.bar_boundaries[end_bar]
    duration = right - left

    def effective_tempo() -> float:
        bpm = 120.0
        for point in song.tempo_map:
            if point.position > left:
                break
            bpm = point.bpm
        return bpm

    def effective_meter() -> tuple[int, int]:
        numerator, denominator = 4, 4
        for point in song.meter_map:
            if point.position > left:
                break
            numerator, denominator = point.numerator, point.denominator
        return numerator, denominator

    sliced_tracks = []
    for track in song.tracks:
        notes = []
        for note in track.notes:
            note_start = max(note.position, left)
            note_end = min(note.position + note.duration, right)
            if note_start < note_end:
                notes.append(
                    replace(
                        note,
                        position=note_start - left,
                        duration=note_end - note_start,
                    )
                )
        sliced_tracks.append(replace(track, notes=tuple(notes)))

    tempo_map = [TempoPoint(position=0.0, bpm=effective_tempo())]
    tempo_map.extend(
        TempoPoint(position=point.position - left, bpm=point.bpm)
        for point in song.tempo_map
        if left < point.position < right
    )

    numerator, denominator = effective_meter()
    meter_map = [MeterPoint(position=0.0, numerator=numerator, denominator=denominator)]
    meter_map.extend(
        MeterPoint(
            position=point.position - left,
            numerator=point.numerator,
            denominator=point.denominator,
        )
        for point in song.meter_map
        if left < point.position < right
    )

    boundaries = tuple(
        point - left
        for point in song.bar_boundaries[start_bar - 1 : end_bar + 1]
    )
    sections = tuple(
        SongSection(
            name=section.name,
            start_bar=max(section.start_bar, start_bar) - start_bar + 1,
            end_bar=min(section.end_bar, end_bar) - start_bar + 1,
        )
        for section in song.sections
        if section.start_bar <= end_bar and section.end_bar >= start_bar
    )
    return replace(
        song,
        tracks=tuple(sliced_tracks),
        tempo_map=tuple(tempo_map),
        meter_map=tuple(meter_map),
        duration_quarters=duration,
        bar_boundaries=boundaries,
        sections=sections,
    )


def resolve_section(song: Song, name: str) -> SongSection:
    """Resolve one uniquely named rehearsal section without guessing."""

    normalized = name.strip().casefold()
    if not normalized:
        raise ValueError("section name must be non-empty")
    matches = [section for section in song.sections if section.name.casefold() == normalized]
    if not matches:
        raise ValueError(f"unknown section: {name}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous section name: {name}; use --bars")
    return matches[0]


def slice_section(song: Song, name: str) -> Song:
    """Return one uniquely named structural rehearsal section."""

    section = resolve_section(song, name)
    return slice_bars(song, section.start_bar, section.end_bar)
