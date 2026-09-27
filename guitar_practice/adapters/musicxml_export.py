"""Deterministic MusicXML 4.0 export from canonical Score IR."""

from __future__ import annotations

import copy
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Mapping, Sequence
from fractions import Fraction
from itertools import groupby
from typing import Any

from guitar_practice.application.ports import ExportedScore, ScoreExportDiagnostic
from guitar_practice.domain import score


class MusicXmlExportError(ValueError):
    """Score IR cannot be represented safely by the deterministic exporter."""


_NOTE_TYPES: tuple[tuple[Fraction, str], ...] = (
    (Fraction(8, 1), "maxima"),
    (Fraction(4, 1), "long"),
    (Fraction(2, 1), "breve"),
    (Fraction(1, 1), "whole"),
    (Fraction(1, 2), "half"),
    (Fraction(1, 4), "quarter"),
    (Fraction(1, 8), "eighth"),
    (Fraction(1, 16), "16th"),
    (Fraction(1, 32), "32nd"),
    (Fraction(1, 64), "64th"),
    (Fraction(1, 128), "128th"),
    (Fraction(1, 256), "256th"),
    (Fraction(1, 512), "512th"),
    (Fraction(1, 1024), "1024th"),
)
_ARTICULATIONS = {
    "accent",
    "breath-mark",
    "caesura",
    "detached-legato",
    "doit",
    "falloff",
    "plop",
    "scoop",
    "spiccato",
    "staccatissimo",
    "staccato",
    "stress",
    "strong-accent",
    "tenuto",
    "unstress",
}
_DYNAMICS = {
    "p",
    "pp",
    "ppp",
    "pppp",
    "ppppp",
    "pppppp",
    "f",
    "ff",
    "fff",
    "ffff",
    "fffff",
    "ffffff",
    "mp",
    "mf",
    "sf",
    "sfp",
    "sfpp",
    "fp",
    "rf",
    "rfz",
    "sfz",
    "sffz",
    "fz",
    "n",
    "pf",
    "sfzp",
}
_CHORD_ROOT = re.compile(r"^([A-G])([#b]?)(.*)$")


def _fraction(value: Sequence[int]) -> Fraction:
    return Fraction(int(value[0]), int(value[1]))


def _number(value: int | float | Fraction) -> str:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return format(float(value), ".12g")
    if isinstance(value, int):
        return str(value)
    if value.is_integer():
        return str(int(value))
    return format(value, ".12g")


def _pitch_midi(pitch: Mapping[str, Any]) -> int:
    classes = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    return 12 * (int(pitch["octave"]) + 1) + classes[str(pitch["step"])] + int(
        pitch["alter"]
    )


def _meter_for_bar(document: Mapping[str, Any], bar: int) -> tuple[int, int]:
    active = document["meter_map"][0]
    for candidate in document["meter_map"][1:]:
        if int(candidate["bar"]) > bar:
            break
        active = candidate
    return int(active["beats"]), int(active["beat_unit"])


def _offset_quarters(document: Mapping[str, Any], location: Mapping[str, Any]) -> Fraction:
    bar = int(location["bar"])
    _, beat_unit = _meter_for_bar(document, bar)
    beat = _fraction(location["beat"])
    return (beat - 1) * Fraction(4, beat_unit)


def _duration_quarters(event: Mapping[str, Any]) -> Fraction:
    return _fraction(event["duration"]) * 4


def _exact_ticks(value: Fraction, divisions: int, label: str) -> int:
    ticks = value * divisions
    if ticks.denominator != 1:
        raise MusicXmlExportError(f"{label} cannot be represented at divisions={divisions}")
    return ticks.numerator


def _divisions(document: Mapping[str, Any]) -> int:
    denominators = [1]
    for part in document["parts"]:
        for event in part["events"]:
            denominators.append(_duration_quarters(event).denominator)
            denominators.append(
                _offset_quarters(document, event["location"]).denominator
            )
    for field in ("tempo_map", "harmony", "rehearsal_marks"):
        for item in document.get(field, []):
            denominators.append(
                _offset_quarters(document, item["location"]).denominator
            )
    result = math.lcm(*denominators)
    if result > 1_000_000:
        raise MusicXmlExportError(
            f"exact MusicXML timing requires excessive divisions value: {result}"
        )
    return result


def _type_and_dots(value: Fraction) -> tuple[str, int] | None:
    for base, name in _NOTE_TYPES:
        for dots in range(4):
            factor = Fraction((2 ** (dots + 1)) - 1, 2**dots)
            if base * factor == value:
                return name, dots
    return None


def _child(parent: ET.Element, tag: str, text: str | int | None = None, **attrs: str) -> ET.Element:
    element = ET.SubElement(parent, tag, attrs)
    if text is not None:
        element.text = str(text)
    return element


def _emit_pitch(parent: ET.Element, pitch: Mapping[str, Any]) -> None:
    node = _child(parent, "pitch")
    _child(node, "step", str(pitch["step"]))
    alter = int(pitch["alter"])
    if alter:
        _child(node, "alter", alter)
    _child(node, "octave", int(pitch["octave"]))


def _emit_note_type(
    parent: ET.Element,
    event: Mapping[str, Any],
    diagnostics: list[ScoreExportDiagnostic],
    path: str,
) -> None:
    written = (
        _fraction(event["tuplet"]["base"])
        if "tuplet" in event
        else _fraction(event["duration"])
    )
    notation = _type_and_dots(written)
    if notation is None:
        diagnostics.append(
            ScoreExportDiagnostic(
                "warning",
                "written-duration-type-omitted",
                path,
                f"written duration {list(event['duration'])} has no standard MusicXML note type",
            )
        )
        return
    name, dots = notation
    _child(parent, "type", name)
    for _ in range(dots):
        _child(parent, "dot")


def _emit_dynamic(notations: ET.Element, dynamic: str) -> None:
    node = _child(notations, "dynamics")
    if dynamic in _DYNAMICS:
        _child(node, dynamic)
    else:
        _child(node, "other-dynamics", dynamic)


def _emit_articulations(
    notations: ET.Element,
    articulations: Sequence[str],
    diagnostics: list[ScoreExportDiagnostic],
    path: str,
) -> None:
    if not articulations:
        return
    node = _child(notations, "articulations")
    for name in articulations:
        if name in _ARTICULATIONS:
            _child(node, name)
        else:
            _child(node, "other-articulation", name)
            diagnostics.append(
                ScoreExportDiagnostic(
                    "warning",
                    "generic-articulation",
                    path,
                    f"articulation {name!r} exported as MusicXML other-articulation",
                )
            )


def _emit_technical(
    notations: ET.Element,
    event: Mapping[str, Any],
    diagnostics: list[ScoreExportDiagnostic],
    path: str,
) -> None:
    position = event.get("position")
    techniques = event.get("techniques", [])
    if position is None and not techniques:
        return
    node = _child(notations, "technical")
    for technique in techniques:
        name = str(technique["name"])
        if name == "bend" and "amount" in technique:
            bend = _child(node, "bend")
            _child(bend, "bend-alter", _number(_fraction(technique["amount"])))
        elif name == "harmonic":
            _child(node, "harmonic")
        elif name == "natural-harmonic":
            harmonic = _child(node, "harmonic")
            _child(harmonic, "natural")
        elif name == "artificial-harmonic":
            harmonic = _child(node, "harmonic")
            _child(harmonic, "artificial")
        else:
            _child(node, "other-technical", name)
            diagnostics.append(
                ScoreExportDiagnostic(
                    "warning",
                    "generic-technique",
                    path,
                    f"technique {name!r} exported as MusicXML other-technical",
                )
            )
    if position is not None:
        _child(node, "string", int(position["string"]))
        _child(node, "fret", int(position["fret"]))


def _tuplet_bounds(part: Mapping[str, Any]) -> dict[str, tuple[int, int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for event in part["events"]:
        tuplet = event.get("tuplet")
        if tuplet is not None:
            grouped[str(tuplet["id"])].append(id(event))
    return {key: (values[0], values[-1]) for key, values in grouped.items()}


def _emit_notations(
    note: ET.Element,
    event: Mapping[str, Any],
    diagnostics: list[ScoreExportDiagnostic],
    path: str,
    tuplet_bounds: Mapping[str, tuple[int, int]],
) -> None:
    needs = any(
        field in event
        for field in ("tie", "tuplet", "articulations", "techniques", "dynamics", "position")
    )
    if not needs:
        return
    notations = _child(note, "notations")

    tie = event.get("tie")
    if tie is not None:
        _child(notations, "tied", type=str(tie))

    tuplet = event.get("tuplet")
    if tuplet is not None:
        tuplet_id = str(tuplet["id"])
        first, last = tuplet_bounds[tuplet_id]
        if id(event) == first:
            _child(notations, "tuplet", type="start", number="1")
        if id(event) == last:
            _child(notations, "tuplet", type="stop", number="1")

    if "articulations" in event:
        _emit_articulations(
            notations,
            event["articulations"],
            diagnostics,
            path,
        )
    if "dynamics" in event:
        _emit_dynamic(notations, str(event["dynamics"]))
    _emit_technical(notations, event, diagnostics, path)


def _emit_note(
    measure: ET.Element,
    event: Mapping[str, Any],
    *,
    divisions: int,
    chord: bool,
    guitar: bool,
    diagnostics: list[ScoreExportDiagnostic],
    path: str,
    tuplet_bounds: Mapping[str, tuple[int, int]],
) -> None:
    node = _child(measure, "note")
    if chord:
        _child(node, "chord")
    if event["kind"] == "rest":
        _child(node, "rest")
    else:
        _emit_pitch(node, event["pitch"])
    _child(node, "duration", _exact_ticks(_duration_quarters(event), divisions, path))

    tie = event.get("tie")
    if tie == "start":
        _child(node, "tie", type="start")
    elif tie == "stop":
        _child(node, "tie", type="stop")
    elif tie == "continue":
        _child(node, "tie", type="stop")
        _child(node, "tie", type="start")

    _child(node, "voice", int(event["voice"]))
    _emit_note_type(node, event, diagnostics, path)
    if "tuplet" in event:
        tm = _child(node, "time-modification")
        tuplet = event["tuplet"]
        _child(tm, "actual-notes", int(tuplet["actual"]))
        _child(tm, "normal-notes", int(tuplet["normal"]))
        normal = _type_and_dots(_fraction(tuplet["base"]))
        if normal is not None:
            _child(tm, "normal-type", normal[0])
            for _ in range(normal[1]):
                _child(tm, "normal-dot")
    if guitar:
        _child(node, "staff", 1)
    if event["kind"] == "note":
        _emit_notations(
            node,
            event,
            diagnostics,
            path,
            tuplet_bounds,
        )


def _emit_voice_events(
    measure: ET.Element,
    document: Mapping[str, Any],
    part: Mapping[str, Any],
    bar: int,
    divisions: int,
    diagnostics: list[ScoreExportDiagnostic],
) -> None:
    by_voice: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for event in part["events"]:
        if int(event["location"]["bar"]) == bar:
            by_voice[int(event["voice"])].append(event)
    if not by_voice:
        return

    tuplet_bounds = _tuplet_bounds(part)
    voices = sorted(by_voice)
    for voice_index, voice in enumerate(voices):
        events = sorted(
            by_voice[voice],
            key=lambda event: (
                _offset_quarters(document, event["location"]),
                -_duration_quarters(event),
                _pitch_midi(event["pitch"]) if event["kind"] == "note" else -1,
            ),
        )
        cursor = 0
        for onset, grouped_iter in groupby(
            events,
            key=lambda event: _exact_ticks(
                _offset_quarters(document, event["location"]),
                divisions,
                "event location",
            ),
        ):
            grouped = list(grouped_iter)
            if onset < cursor:
                raise MusicXmlExportError(
                    f"parts[{part['id']}] bar {bar} voice {voice} contains overlapping events"
                )
            if onset > cursor:
                forward = _child(measure, "forward")
                _child(forward, "duration", onset - cursor)
                _child(forward, "voice", voice)
                cursor = onset

            durations = {
                _exact_ticks(_duration_quarters(event), divisions, "event duration")
                for event in grouped
            }
            if len(grouped) > 1 and (
                len(durations) != 1 or any(event["kind"] != "note" for event in grouped)
            ):
                raise MusicXmlExportError(
                    f"parts[{part['id']}] bar {bar} voice {voice} simultaneous events must be equal-duration notes"
                )
            duration = next(iter(durations))
            for index, event in enumerate(grouped):
                path = (
                    f"parts[{part['id']}].events[bar={bar},beat={event['location']['beat']},"
                    f"voice={voice}]"
                )
                _emit_note(
                    measure,
                    event,
                    divisions=divisions,
                    chord=index > 0,
                    guitar="guitar" in part,
                    diagnostics=diagnostics,
                    path=path,
                    tuplet_bounds=tuplet_bounds,
                )
            cursor += duration

        if voice_index < len(voices) - 1 and cursor:
            backup = _child(measure, "backup")
            _child(backup, "duration", cursor)


def _emit_key(attributes: ET.Element, entry: Mapping[str, Any]) -> None:
    node = _child(attributes, "key")
    _child(node, "fifths", int(entry["fifths"]))
    _child(node, "mode", str(entry["mode"]))


def _emit_time(attributes: ET.Element, entry: Mapping[str, Any]) -> None:
    node = _child(attributes, "time")
    _child(node, "beats", int(entry["beats"]))
    _child(node, "beat-type", int(entry["beat_unit"]))


def _emit_guitar_staff(attributes: ET.Element, part: Mapping[str, Any]) -> None:
    tuning = part["guitar"]["tuning"]
    _child(attributes, "staves", 2)
    clef = _child(attributes, "clef", number="1")
    _child(clef, "sign", "G")
    _child(clef, "line", 2)
    tab = _child(attributes, "clef", number="2")
    _child(tab, "sign", "TAB")
    _child(tab, "line", 5)

    details = _child(attributes, "staff-details", number="2")
    _child(details, "staff-type", "alternate")
    _child(details, "staff-lines", len(tuning))
    ordered = sorted(tuning, key=lambda item: int(item["string"]), reverse=True)
    for line, string in enumerate(ordered, start=1):
        staff_tuning = _child(details, "staff-tuning", line=str(line))
        pitch = string["pitch"]
        _child(staff_tuning, "tuning-step", str(pitch["step"]))
        alter = int(pitch["alter"])
        if alter:
            _child(staff_tuning, "tuning-alter", alter)
        _child(staff_tuning, "tuning-octave", int(pitch["octave"]))


def _emit_clef(attributes: ET.Element, part: Mapping[str, Any]) -> None:
    if "guitar" in part:
        _emit_guitar_staff(attributes, part)
        return
    clef = _child(attributes, "clef")
    role = str(part["role"])
    if role == "bass":
        _child(clef, "sign", "F")
        _child(clef, "line", 4)
    elif role == "drums":
        _child(clef, "sign", "percussion")
    else:
        _child(clef, "sign", "G")
        _child(clef, "line", 2)


def _map_at_bar(entries: Sequence[Mapping[str, Any]], bar: int) -> Mapping[str, Any] | None:
    return next((entry for entry in entries if int(entry["bar"]) == bar), None)


def _emit_attributes(
    measure: ET.Element,
    document: Mapping[str, Any],
    part: Mapping[str, Any],
    bar: int,
    divisions: int,
) -> None:
    meter = _map_at_bar(document["meter_map"], bar)
    key = _map_at_bar(document.get("key_map", []), bar)
    if bar != 1 and meter is None and key is None:
        return
    attributes = _child(measure, "attributes")
    if bar == 1:
        _child(attributes, "divisions", divisions)
    if key is not None:
        _emit_key(attributes, key)
    if meter is not None:
        _emit_time(attributes, meter)
    if bar == 1:
        _emit_clef(attributes, part)


def _emit_tempo_direction(
    measure: ET.Element,
    document: Mapping[str, Any],
    entry: Mapping[str, Any],
    divisions: int,
    diagnostics: list[ScoreExportDiagnostic],
) -> None:
    direction = _child(measure, "direction", placement="above")
    direction_type = _child(direction, "direction-type")
    metronome = _child(direction_type, "metronome")
    beat_unit = _fraction(entry["beat_unit"])
    notation = _type_and_dots(beat_unit)
    bpm = Fraction(str(entry["bpm"]))
    if notation is None:
        quarter_bpm = bpm * beat_unit * 4
        _child(metronome, "beat-unit", "quarter")
        _child(metronome, "per-minute", _number(quarter_bpm))
        diagnostics.append(
            ScoreExportDiagnostic(
                "warning",
                "normalized-tempo-unit",
                "tempo_map",
                f"tempo beat unit {entry['beat_unit']} normalized to quarter-note BPM",
            )
        )
    else:
        name, dots = notation
        _child(metronome, "beat-unit", name)
        for _ in range(dots):
            _child(metronome, "beat-unit-dot")
        _child(metronome, "per-minute", _number(bpm))

    offset = _exact_ticks(
        _offset_quarters(document, entry["location"]),
        divisions,
        "tempo offset",
    )
    if offset:
        _child(direction, "offset", offset)
    quarter_bpm = bpm * beat_unit * 4
    _child(direction, "sound", tempo=_number(quarter_bpm))


def _emit_rehearsal(
    measure: ET.Element,
    label: str,
    offset: int,
) -> None:
    direction = _child(measure, "direction", placement="above")
    direction_type = _child(direction, "direction-type")
    _child(direction_type, "rehearsal", label)
    if offset:
        _child(direction, "offset", offset)


def _emit_harmony(
    measure: ET.Element,
    document: Mapping[str, Any],
    entry: Mapping[str, Any],
    divisions: int,
) -> None:
    node = _child(measure, "harmony")
    symbol = str(entry["symbol"])
    match = _CHORD_ROOT.match(symbol)
    if match is not None:
        root = _child(node, "root")
        _child(root, "root-step", match.group(1))
        accidental = match.group(2)
        if accidental:
            _child(root, "root-alter", 1 if accidental == "#" else -1)
    else:
        _child(node, "function", symbol)
    kind = _child(node, "kind", "other")
    kind.set("text", symbol)
    offset = _exact_ticks(
        _offset_quarters(document, entry["location"]),
        divisions,
        "harmony offset",
    )
    if offset:
        _child(node, "offset", offset)


def _ending_text(values: set[int]) -> str:
    return ",".join(str(value) for value in sorted(values))


def _emit_barlines(
    measure: ET.Element,
    bars: Sequence[Mapping[str, Any]],
    bar: int,
) -> None:
    current = bars[bar - 1]
    previous = set(bars[bar - 2].get("ending_numbers", [])) if bar > 1 else set()
    following = set(bars[bar].get("ending_numbers", [])) if bar < len(bars) else set()
    endings = set(current.get("ending_numbers", []))
    starting = endings - previous
    stopping = endings - following

    if current.get("repeat_start") or starting:
        left = _child(measure, "barline", location="left")
        if starting:
            _child(left, "ending", number=_ending_text(starting), type="start")
        if current.get("repeat_start"):
            _child(left, "repeat", direction="forward")

    if current.get("repeat_end") or stopping:
        right = _child(measure, "barline", location="right")
        if stopping:
            _child(right, "ending", number=_ending_text(stopping), type="stop")
        if current.get("repeat_end"):
            _child(
                right,
                "repeat",
                direction="backward",
                times=str(int(current["repeat_end"])),
            )


def _emit_global_measure_content(
    measure: ET.Element,
    document: Mapping[str, Any],
    bar: int,
    divisions: int,
    diagnostics: list[ScoreExportDiagnostic],
) -> None:
    for section in document.get("sections", []):
        if int(section["start_bar"]) == bar:
            _emit_rehearsal(measure, str(section["label"]), 0)
    for mark in document.get("rehearsal_marks", []):
        if int(mark["location"]["bar"]) == bar:
            offset = _exact_ticks(
                _offset_quarters(document, mark["location"]),
                divisions,
                "rehearsal offset",
            )
            _emit_rehearsal(measure, str(mark["label"]), offset)
    for tempo in document["tempo_map"]:
        if int(tempo["location"]["bar"]) == bar:
            _emit_tempo_direction(measure, document, tempo, divisions, diagnostics)
    for harmony in document.get("harmony", []):
        if int(harmony["location"]["bar"]) == bar:
            _emit_harmony(measure, document, harmony, divisions)


def _part_list(root: ET.Element, document: Mapping[str, Any]) -> list[str]:
    part_list = _child(root, "part-list")
    ids: list[str] = []
    for index, part in enumerate(document["parts"], start=1):
        part_id = f"P{index}"
        ids.append(part_id)
        score_part = _child(part_list, "score-part", id=part_id)
        _child(score_part, "part-name", str(part["name"]))
        instrument_id = f"{part_id}-I1"
        score_instrument = _child(score_part, "score-instrument", id=instrument_id)
        _child(score_instrument, "instrument-name", str(part["instrument"]["name"]))
        midi = part["instrument"].get("midi")
        if midi:
            midi_instrument = _child(score_part, "midi-instrument", id=instrument_id)
            if "channel" in midi:
                _child(midi_instrument, "midi-channel", int(midi["channel"]))
            elif midi.get("percussion"):
                _child(midi_instrument, "midi-channel", 10)
            if "program" in midi:
                _child(midi_instrument, "midi-program", int(midi["program"]) + 1)
    return ids


class MusicXmlExporter:
    """Export canonical Score IR as deterministic uncompressed MusicXML 4.0."""

    def export(self, document: Mapping[str, Any]) -> ExportedScore:
        candidate = copy.deepcopy(dict(document))
        try:
            score.validate(candidate)
        except score.ScoreError as exc:
            raise MusicXmlExportError(str(exc)) from exc
        if not candidate["parts"]:
            raise MusicXmlExportError("MusicXML export requires at least one score part")

        divisions = _divisions(candidate)
        diagnostics: list[ScoreExportDiagnostic] = []
        root = ET.Element("score-partwise", {"version": "4.0"})
        work = _child(root, "work")
        _child(work, "work-title", str(candidate["metadata"]["title"]))
        identification = _child(root, "identification")
        encoding = _child(identification, "encoding")
        _child(encoding, "software", "guitar-practice-system guitarctl")

        part_ids = _part_list(root, candidate)
        for part_index, (part_id, part) in enumerate(
            zip(part_ids, candidate["parts"], strict=True)
        ):
            part_node = _child(root, "part", id=part_id)
            for bar in range(1, len(candidate["bars"]) + 1):
                measure = _child(part_node, "measure", number=str(bar))
                _emit_attributes(measure, candidate, part, bar, divisions)
                if part_index == 0:
                    _emit_global_measure_content(
                        measure,
                        candidate,
                        bar,
                        divisions,
                        diagnostics,
                    )
                _emit_voice_events(
                    measure,
                    candidate,
                    part,
                    bar,
                    divisions,
                    diagnostics,
                )
                _emit_barlines(measure, candidate["bars"], bar)

        ET.indent(root, space="  ")
        body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"
        ).encode("utf-8")
        return ExportedScore(data=data, diagnostics=tuple(diagnostics))
