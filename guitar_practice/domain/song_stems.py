"""Pure practice-tempo realization and imported-song stem selection."""

from __future__ import annotations

import math
from dataclasses import replace
from collections.abc import Callable, Iterable

from guitar_practice.domain.song import Song, SongTrack, TempoPoint, TrackRole


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
        default_selected=lambda track: track.classification.role is not TrackRole.GUITAR,
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
