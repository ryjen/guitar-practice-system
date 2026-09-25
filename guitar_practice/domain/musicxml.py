"""Minimal MusicXML import into the canonical Song model."""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import replace
from typing import TypeVar

from guitar_practice.domain.song import (
    MeterPoint,
    NoteEvent,
    Song,
    SongSection,
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


_STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _divisions(attributes: ET.Element | None, current: int) -> int:
    if attributes is None:
        return current
    value = _int_text(_first(attributes, "divisions"), "divisions")
    if value is None:
        return current
    if value <= 0:
        raise MusicXmlError("divisions must be positive")
    return value


def _pitched_midi_note(note: ET.Element) -> int | None:
    pitch = _first(note, "pitch")
    if pitch is None:
        return None
    step = (_text(_first(pitch, "step")) or "").upper()
    if step not in _STEP_TO_SEMITONE:
        raise MusicXmlError("pitch step must be A through G")
    octave = _int_text(_first(pitch, "octave"), "pitch octave")
    if octave is None:
        raise MusicXmlError("pitched note requires octave")
    alter_value = _float_value(_text(_first(pitch, "alter")), "pitch alter") or 0.0
    if not alter_value.is_integer():
        raise MusicXmlError("microtonal pitch alters are not supported for MIDI import")
    midi_note = 12 * (octave + 1) + _STEP_TO_SEMITONE[step] + int(alter_value)
    if not 0 <= midi_note <= 127:
        raise MusicXmlError("pitched note is outside the MIDI range")
    return midi_note


def _title(root: ET.Element, source_id: str) -> str:
    work = _first(root, "work")
    work_title = _text(_first(work, "work-title")) if work is not None else None
    movement_title = _text(_first(root, "movement-title"))
    return work_title or movement_title or source_id


def _unpitched_note_map(root: ET.Element) -> dict[str, dict[str, int]]:
    part_list = _first(root, "part-list")
    if part_list is None:
        return {}
    result: dict[str, dict[str, int]] = {}
    for score_part in _children(part_list, "score-part"):
        raw_part_id = score_part.attrib.get("id", "").strip()
        per_instrument: dict[str, int] = {}
        for midi_instrument in _children(score_part, "midi-instrument"):
            instrument_id = midi_instrument.attrib.get("id", "").strip()
            value = _int_text(_first(midi_instrument, "midi-unpitched"), "midi-unpitched")
            if value is None:
                continue
            if not 1 <= value <= 128:
                raise MusicXmlError("MusicXML midi-unpitched must be between 1 and 128")
            if instrument_id:
                per_instrument[instrument_id] = value - 1
        result[raw_part_id] = per_instrument
    return result


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


def _duration_quarters(element: ET.Element, divisions: int, label: str) -> float:
    raw = _float_value(_text(_first(element, "duration")), label)
    if raw is None or raw <= 0:
        raise MusicXmlError(f"{label} must be positive")
    return raw / divisions


def _note_midi_note(note: ET.Element, unpitched: dict[str, int]) -> int | None:
    if _first(note, "rest") is not None:
        return None
    pitched = _pitched_midi_note(note)
    if pitched is not None:
        return pitched
    if _first(note, "unpitched") is None:
        raise MusicXmlError("note must contain pitch, unpitched, or rest")
    instrument = _first(note, "instrument")
    instrument_id = instrument.attrib.get("id", "").strip() if instrument is not None else ""
    if instrument_id and instrument_id in unpitched:
        return unpitched[instrument_id]
    if len(unpitched) == 1:
        return next(iter(unpitched.values()))
    raise MusicXmlError("unpitched note has no unambiguous midi-unpitched identity")


def _parse_track_notes(root: ET.Element, tracks: tuple[SongTrack, ...]) -> tuple[SongTrack, ...]:
    part_list = _first(root, "part-list")
    assert part_list is not None
    raw_ids = [part.attrib.get("id", "").strip() for part in _children(part_list, "score-part")]
    track_by_raw_id = dict(zip(raw_ids, tracks, strict=True))
    unpitched_by_part = _unpitched_note_map(root)
    notes_by_track: dict[str, list[NoteEvent]] = {track.id: [] for track in tracks}

    for part in _children(root, "part"):
        raw_id = part.attrib.get("id", "").strip()
        track = track_by_raw_id.get(raw_id)
        if track is None:
            raise MusicXmlError(f"part references unknown score-part id: {raw_id}")
        divisions = 1
        numerator = 4
        denominator = 4
        measure_position = 0.0
        for measure in _children(part, "measure"):
            cursor = 0.0
            last_note_start: float | None = None
            for child in measure:
                kind = _local_name(child.tag)
                if kind == "attributes":
                    divisions = _divisions(child, divisions)
                    time = _first(child, "time")
                    if time is not None:
                        beats = _int_text(_first(time, "beats"), "time beats")
                        beat_type = _int_text(_first(time, "beat-type"), "time beat-type")
                        if beats is None or beat_type is None:
                            raise MusicXmlError("time signature requires beats and beat-type")
                        numerator, denominator = beats, beat_type
                    continue
                if kind in {"backup", "forward"}:
                    duration = _duration_quarters(child, divisions, f"{kind} duration")
                    cursor += duration if kind == "forward" else -duration
                    if cursor < 0:
                        raise MusicXmlError("backup moves before the start of a measure")
                    last_note_start = None
                    continue
                if kind != "note":
                    continue
                if _first(child, "grace") is not None:
                    raise MusicXmlError("grace notes are not yet supported for symbolic MIDI import")
                duration = _duration_quarters(child, divisions, "note duration")
                is_chord = _first(child, "chord") is not None
                if is_chord:
                    if last_note_start is None:
                        raise MusicXmlError("chord note has no preceding note onset")
                    start = last_note_start
                else:
                    start = measure_position + cursor
                    last_note_start = start
                midi_note = _note_midi_note(child, unpitched_by_part.get(raw_id, {}))
                if midi_note is not None:
                    notes_by_track[track.id].append(
                        NoteEvent(position=start, duration=duration, midi_note=midi_note)
                    )
                if not is_chord:
                    cursor += duration
            measure_position += numerator * (4.0 / denominator)

    return tuple(
        replace(
            track,
            notes=tuple(
                sorted(notes_by_track[track.id], key=lambda note: (note.position, note.midi_note))
            ),
        )
        for track in tracks
    )


def _parse_maps(root: ET.Element) -> tuple[tuple[TempoPoint, ...], tuple[MeterPoint, ...]]:
    first_part = _first(root, "part")
    if first_part is None:
        return (), ()

    position = 0.0
    numerator = 4
    denominator = 4
    divisions = 1
    tempo_points: list[TempoPoint] = []
    meter_points: list[MeterPoint] = []

    for measure in _children(first_part, "measure"):
        attributes = _first(measure, "attributes")
        if attributes is not None:
            divisions = _divisions(attributes, divisions)
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
                offset = (parsed_offset or 0.0) / divisions
            for sound in _descendants(direction, "sound"):
                bpm = _float_value(sound.attrib.get("tempo"), "sound tempo")
                if bpm is not None:
                    tempo_points.append(TempoPoint(position=position + offset, bpm=bpm))

        position += numerator * (4.0 / denominator)

    return tuple(tempo_points), tuple(meter_points)



def _measure_spans_quarters(part: ET.Element) -> tuple[float, ...]:
    numerator = 4
    denominator = 4
    divisions = 1
    spans: list[float] = []
    for measure in _children(part, "measure"):
        attributes = _first(measure, "attributes")
        divisions = _divisions(attributes, divisions)
        if attributes is not None:
            time = _first(attributes, "time")
            if time is not None:
                beats = _int_text(_first(time, "beats"), "time beats")
                beat_type = _int_text(_first(time, "beat-type"), "time beat-type")
                if beats is None or beat_type is None:
                    raise MusicXmlError("time signature requires beats and beat-type")
                numerator, denominator = beats, beat_type

        nominal = numerator * (4.0 / denominator)
        if measure.attrib.get("implicit", "no").casefold() != "yes":
            spans.append(nominal)
            continue

        cursor = 0.0
        maximum = 0.0
        for child in measure:
            kind = _local_name(child.tag)
            if kind in {"backup", "forward"}:
                duration = _duration_quarters(child, divisions, f"{kind} duration")
                cursor += duration if kind == "forward" else -duration
                if cursor < 0:
                    raise MusicXmlError("backup moves before the start of a measure")
                maximum = max(maximum, cursor)
            elif kind == "note" and _first(child, "grace") is None:
                duration = _duration_quarters(child, divisions, "note duration")
                if _first(child, "chord") is None:
                    cursor += duration
                    maximum = max(maximum, cursor)
        spans.append(maximum or nominal)
    return tuple(spans)


def _structural_duration_quarters(root: ET.Element) -> float | None:
    durations = [sum(_measure_spans_quarters(part)) for part in _children(root, "part")]
    return max(durations, default=0.0) or None


def _bar_boundaries(root: ET.Element) -> tuple[float, ...]:
    first_part = _first(root, "part")
    if first_part is None:
        return ()
    position = 0.0
    boundaries = [position]
    for span in _measure_spans_quarters(first_part):
        position += span
        boundaries.append(position)
    return tuple(boundaries)


def _sections(root: ET.Element) -> tuple[SongSection, ...]:
    first_part = _first(root, "part")
    if first_part is None:
        return ()
    measures = list(_children(first_part, "measure"))
    markers: list[tuple[int, str]] = []
    for bar, measure in enumerate(measures, start=1):
        names = [name for item in _descendants(measure, "rehearsal") if (name := _text(item))]
        if len(names) > 1:
            raise MusicXmlError("multiple rehearsal marks in one measure are not supported")
        if names:
            markers.append((bar, names[0]))
    return tuple(
        SongSection(
            name=name,
            start_bar=start,
            end_bar=(markers[index + 1][0] - 1 if index + 1 < len(markers) else len(measures)),
        )
        for index, (start, name) in enumerate(markers)
    )


_NAVIGATION_SOUND_ATTRIBUTES = frozenset({
    "dacapo", "dalsegno", "tocoda", "fine", "segno", "coda"
})


def _repeat_play_order(measures: list[ET.Element]) -> list[int]:
    active_start: int | None = None
    order: list[int] = []
    for index, measure in enumerate(measures):
        if any(True for _ in _descendants(measure, "ending")):
            raise MusicXmlError("MusicXML ending playback is not yet supported")
        repeats = list(_descendants(measure, "repeat"))
        forwards = [item for item in repeats if item.attrib.get("direction") == "forward"]
        backwards = [item for item in repeats if item.attrib.get("direction") == "backward"]
        if len(forwards) > 1 or len(backwards) > 1:
            raise MusicXmlError("multiple repeat marks in one measure are not supported")
        if forwards:
            if active_start is not None:
                raise MusicXmlError("nested forward repeats are not supported")
            active_start = index

        order.append(index)
        if backwards:
            repeat = backwards[0]
            raw_times = repeat.attrib.get("times")
            try:
                plays = int(raw_times) if raw_times is not None else 2
            except ValueError as exc:
                raise MusicXmlError("repeat times must be an integer") from exc
            if not 1 <= plays <= 32:
                raise MusicXmlError("repeat times must be between 1 and 32")
            start = active_start if active_start is not None else 0
            section = list(range(start, index + 1))
            for _ in range(plays - 1):
                order.extend(section)
            active_start = None
        if len(order) > 10_000:
            raise MusicXmlError("expanded repeat form is too large")
    return order


def _measure_start_states(
    measures: list[ET.Element],
) -> list[tuple[int, int, int]]:
    divisions = 1
    numerator = 4
    denominator = 4
    states: list[tuple[int, int, int]] = []
    for measure in measures:
        attributes = _first(measure, "attributes")
        divisions = _divisions(attributes, divisions)
        if attributes is not None:
            time = _first(attributes, "time")
            if time is not None:
                beats = _int_text(_first(time, "beats"), "time beats")
                beat_type = _int_text(_first(time, "beat-type"), "time beat-type")
                if beats is None or beat_type is None:
                    raise MusicXmlError("time signature requires beats and beat-type")
                numerator, denominator = beats, beat_type
        states.append((divisions, numerator, denominator))
    return states


def _tempo_start_states(measures: list[ET.Element]) -> list[float]:
    tempo = 120.0
    divisions = 1
    states: list[float] = []
    for measure in measures:
        attributes = _first(measure, "attributes")
        divisions = _divisions(attributes, divisions)
        states.append(tempo)
        events: list[tuple[float, float]] = []
        for direction in _children(measure, "direction"):
            offset_element = _first(direction, "offset")
            parsed_offset = (
                _float_value(_text(offset_element), "direction offset")
                if offset_element is not None
                else 0.0
            )
            offset = (parsed_offset or 0.0) / divisions
            for sound in _descendants(direction, "sound"):
                bpm = _float_value(sound.attrib.get("tempo"), "sound tempo")
                if bpm is not None:
                    events.append((offset, bpm))
        for _, bpm in sorted(events):
            tempo = bpm
    return states


def _inject_repeat_start_state(
    measure: ET.Element,
    *,
    divisions: int,
    numerator: int,
    denominator: int,
    tempo: float | None,
) -> None:
    attributes = ET.Element("attributes")
    ET.SubElement(attributes, "divisions").text = str(divisions)
    time = ET.SubElement(attributes, "time")
    ET.SubElement(time, "beats").text = str(numerator)
    ET.SubElement(time, "beat-type").text = str(denominator)
    measure.insert(0, attributes)
    if tempo is not None:
        direction = ET.Element("direction")
        direction_type = ET.SubElement(direction, "direction-type")
        ET.SubElement(direction_type, "words").text = "repeat-state"
        ET.SubElement(direction, "sound", {"tempo": f"{tempo:g}"})
        measure.insert(1, direction)


def _expand_simple_repeats(root: ET.Element) -> ET.Element:
    for sound in _descendants(root, "sound"):
        if _NAVIGATION_SOUND_ATTRIBUTES & set(sound.attrib):
            raise MusicXmlError("MusicXML jump navigation is not yet supported")

    if any(True for _ in _descendants(root, "ending")):
        raise MusicXmlError("MusicXML ending playback is not yet supported")

    parts = list(_children(root, "part"))
    if not parts:
        return root
    measure_sets = [list(_children(part, "measure")) for part in parts]
    repeat_flags = [
        any(any(True for _ in _descendants(measure, "repeat")) for measure in measures)
        for measures in measure_sets
    ]
    if not any(repeat_flags):
        return root

    reference_index = repeat_flags.index(True)
    expected_count = len(measure_sets[reference_index])
    if any(len(measures) != expected_count for measures in measure_sets):
        raise MusicXmlError("parts must have aligned measure counts for repeat expansion")
    order = _repeat_play_order(measure_sets[reference_index])
    for has_repeats, measures in zip(repeat_flags, measure_sets, strict=True):
        if has_repeats and _repeat_play_order(measures) != order:
            raise MusicXmlError("parts must use consistent repeat marks")

    state_sets = [_measure_start_states(measures) for measures in measure_sets]
    tempo_states = _tempo_start_states(measure_sets[0])
    expanded = copy.deepcopy(root)
    for part_index, part in enumerate(_children(expanded, "part")):
        measures = list(_children(part, "measure"))
        for measure in measures:
            part.remove(measure)
        for occurrence, index in enumerate(order):
            measure = copy.deepcopy(measures[index])
            is_jump = occurrence > 0 and index != order[occurrence - 1] + 1
            if is_jump:
                divisions, numerator, denominator = state_sets[part_index][index]
                _inject_repeat_start_state(
                    measure,
                    divisions=divisions,
                    numerator=numerator,
                    denominator=denominator,
                    tempo=tempo_states[index] if part_index == 0 else None,
                )
            part.append(measure)
    return expanded


def parse_musicxml(data: bytes, *, source_id: str) -> Song:
    """Parse the import-foundation subset of MusicXML into a canonical Song."""

    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError) as exc:
        raise MusicXmlError("malformed MusicXML") from exc

    if _local_name(root.tag) != "score-partwise":
        raise MusicXmlError("MusicXML root must be score-partwise")

    try:
        root = _expand_simple_repeats(root)
        tracks = _parse_track_notes(root, _parse_tracks(root))
        tempo_map, meter_map = _parse_maps(root)
        return Song(
            source_id=source_id,
            title=_title(root, source_id),
            tracks=tracks,
            tempo_map=tempo_map,
            meter_map=meter_map,
            duration_quarters=_structural_duration_quarters(root),
            bar_boundaries=_bar_boundaries(root),
            sections=_sections(root),
        )
    except MusicXmlError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise MusicXmlError(str(exc)) from exc
