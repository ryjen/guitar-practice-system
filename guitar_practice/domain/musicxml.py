"""Minimal MusicXML import into the canonical Song model."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from typing import TypeVar

from guitar_practice.domain.song import (
    MeterPoint,
    Song,
    SongTrack,
    TempoPoint,
    classify_track,
)


class MusicXmlError(ValueError):
    """Raised when MusicXML cannot satisfy the imported-song contract."""


_Element = TypeVar("_Element", bound=ET.Element)
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element if _local_name(child.tag) == name)


def _first(element: ET.Element, name: str) -> ET.Element | None:
    return next(iter(_children(element, name)), None)


def _descendants(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element.iter() if _local_name(child.tag) == name)


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _int_text(element: ET.Element | None, label: str) -> int | None:
    value = _text(element)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise MusicXmlError(f"{label} must be an integer") from exc


def _float_value(value: str | None, label: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise MusicXmlError(f"{label} must be numeric") from exc


def _part_id(raw_id: str, index: int) -> str:
    if _SAFE_ID.fullmatch(raw_id):
        return raw_id
    return f"part-{index}"


def _title(root: ET.Element, source_id: str) -> str:
    work = _first(root, "work")
    work_title = _text(_first(work, "work-title")) if work is not None else None
    movement_title = _text(_first(root, "movement-title"))
    return work_title or movement_title or source_id


def _parse_tracks(root: ET.Element) -> tuple[SongTrack, ...]:
    part_list = _first(root, "part-list")
    if part_list is None:
        raise MusicXmlError("score-partwise document is missing part-list")

    seen_raw_ids: set[str] = set()
    tracks: list[SongTrack] = []
    for index, score_part in enumerate(_children(part_list, "score-part"), start=1):
        raw_id = score_part.attrib.get("id", "").strip()
        if not raw_id:
            raise MusicXmlError("score-part id must be non-empty")
        if raw_id in seen_raw_ids:
            raise MusicXmlError(f"duplicate score-part id: {raw_id}")
        seen_raw_ids.add(raw_id)

        name = _text(_first(score_part, "part-name")) or raw_id
        score_instrument = _first(score_part, "score-instrument")
        instrument_name = (
            _text(_first(score_instrument, "instrument-name"))
            if score_instrument is not None
            else None
        )
        midi_instrument = _first(score_part, "midi-instrument")
        midi_channel = (
            _int_text(_first(midi_instrument, "midi-channel"), "midi-channel")
            if midi_instrument is not None
            else None
        )
        xml_program = (
            _int_text(_first(midi_instrument, "midi-program"), "midi-program")
            if midi_instrument is not None
            else None
        )
        if xml_program is not None and not 1 <= xml_program <= 128:
            raise MusicXmlError("MusicXML midi-program must be between 1 and 128")
        midi_program = xml_program - 1 if xml_program is not None else None
        has_unpitched = (
            midi_instrument is not None
            and _first(midi_instrument, "midi-unpitched") is not None
        )
        is_percussion = midi_channel == 10 or has_unpitched

        tracks.append(
            SongTrack(
                id=_part_id(raw_id, index),
                name=name,
                classification=classify_track(
                    name=name,
                    instrument_name=instrument_name,
                    midi_program=midi_program,
                    is_percussion=is_percussion,
                ),
                instrument_name=instrument_name,
                midi_program=midi_program,
                midi_channel=midi_channel,
                is_percussion=is_percussion,
            )
        )

    if not tracks:
        raise MusicXmlError("score-partwise document has no score-part entries")
    return tuple(tracks)


def _parse_maps(root: ET.Element) -> tuple[tuple[TempoPoint, ...], tuple[MeterPoint, ...]]:
    first_part = _first(root, "part")
    if first_part is None:
        return (), ()

    position = 0.0
    numerator = 4
    denominator = 4
    tempo_points: list[TempoPoint] = []
    meter_points: list[MeterPoint] = []

    for measure in _children(first_part, "measure"):
        attributes = _first(measure, "attributes")
        if attributes is not None:
            time = _first(attributes, "time")
            if time is not None:
                beats = _int_text(_first(time, "beats"), "time beats")
                beat_type = _int_text(_first(time, "beat-type"), "time beat-type")
                if beats is None or beat_type is None:
                    raise MusicXmlError("time signature requires beats and beat-type")
                meter = MeterPoint(position=position, numerator=beats, denominator=beat_type)
                if not meter_points or meter_points[-1] != meter:
                    meter_points.append(meter)
                numerator, denominator = beats, beat_type

        for direction in _children(measure, "direction"):
            offset = 0.0
            offset_element = _first(direction, "offset")
            if offset_element is not None:
                parsed_offset = _float_value(_text(offset_element), "direction offset")
                offset = parsed_offset or 0.0
            for sound in _descendants(direction, "sound"):
                bpm = _float_value(sound.attrib.get("tempo"), "sound tempo")
                if bpm is not None:
                    tempo_points.append(TempoPoint(position=position + offset, bpm=bpm))

        position += numerator * (4.0 / denominator)

    return tuple(tempo_points), tuple(meter_points)


def parse_musicxml(data: bytes, *, source_id: str) -> Song:
    """Parse the import-foundation subset of MusicXML into a canonical Song."""

    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError) as exc:
        raise MusicXmlError("malformed MusicXML") from exc

    if _local_name(root.tag) != "score-partwise":
        raise MusicXmlError("MusicXML root must be score-partwise")

    try:
        tracks = _parse_tracks(root)
        tempo_map, meter_map = _parse_maps(root)
        return Song(
            source_id=source_id,
            title=_title(root, source_id),
            tracks=tracks,
            tempo_map=tempo_map,
            meter_map=meter_map,
        )
    except MusicXmlError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise MusicXmlError(str(exc)) from exc
