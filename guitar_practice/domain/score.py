"""Canonical Score IR validation and deterministic JSON serialization."""

from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from math import gcd
from typing import Any

SCHEMA_ID = "guitar-practice.score"
SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_REQUIRED_TOP_LEVEL = {
    "schema",
    "version",
    "id",
    "metadata",
    "bars",
    "meter_map",
    "tempo_map",
    "parts",
}
_OPTIONAL_TOP_LEVEL = {
    "key_map",
    "sections",
    "rehearsal_marks",
    "harmony",
    "provenance",
}
_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class ScoreError(ValueError):
    """Raised when a Score IR document violates the canonical contract."""


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScoreError(f"{name} must be an object")
    return value


def _validate_unicode_scalar_text(value: str, name: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ScoreError(f"{name} must not contain surrogate code points")


def _string(value: Any, name: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScoreError(f"{name} must be a non-empty string")
    _validate_unicode_scalar_text(value, name)
    normalized = value.strip()
    if len(normalized) > maximum:
        raise ScoreError(f"{name} must be at most {maximum} characters")
    return normalized


def _slug(value: Any, name: str) -> str:
    result = _string(value, name, maximum=64)
    if value != result or not ID_PATTERN.fullmatch(result):
        raise ScoreError(f"{name} must be a lowercase slug: {value!r}")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ScoreError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ScoreError(f"{name} must be a non-negative integer")
    return value


def _fraction(value: Any, name: str, *, positive: bool = False) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ScoreError(f"{name} must be [numerator, denominator]")
    numerator, denominator = value
    if denominator <= 0:
        raise ScoreError(f"{name} denominator must be positive")
    if positive and numerator <= 0:
        raise ScoreError(f"{name} must be positive")
    if gcd(abs(numerator), denominator) != 1:
        raise ScoreError(f"{name} must be in lowest terms")
    return Fraction(numerator, denominator)


def _validate_json_value(value: Any, name: str) -> None:
    if isinstance(value, str):
        _validate_unicode_scalar_text(value, name)
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ScoreError(f"{name} must not contain non-finite numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{name}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ScoreError(f"{name} object keys must be strings")
            _validate_unicode_scalar_text(key, f"{name} object key")
            _validate_json_value(item, f"{name}.{key}")
        return
    raise ScoreError(f"{name} must contain only JSON-compatible values")


def _validate_provenance(value: Any, name: str) -> None:
    provenance = _object(value, name)
    allowed = {"kind", "source", "confidence", "alternatives"}
    unknown = set(provenance) - allowed
    if unknown:
        raise ScoreError(f"{name} provenance has unsupported fields: {sorted(unknown)}")
    kind = _string(provenance.get("kind"), f"{name}.kind", maximum=32)
    if kind not in {"user", "imported", "generated", "inferred"}:
        raise ScoreError(f"{name}.kind must be user, imported, generated, or inferred")
    _string(provenance.get("source"), f"{name}.source", maximum=200)

    inference_fields = {"confidence", "alternatives"} & set(provenance)
    if kind != "inferred" and inference_fields:
        raise ScoreError(
            f"{name} confidence/alternatives are only valid for inferred provenance"
        )
    if "confidence" in provenance:
        confidence = provenance["confidence"]
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ScoreError(f"{name}.confidence must be between 0 and 1")
    if "alternatives" in provenance:
        alternatives = provenance["alternatives"]
        if not isinstance(alternatives, list) or not alternatives:
            raise ScoreError(f"{name}.alternatives must be a non-empty list")
        for index, alternative in enumerate(alternatives):
            _validate_json_value(alternative, f"{name}.alternatives[{index}]")


def _validate_optional_provenance(container: dict[str, Any], name: str) -> None:
    if "provenance" in container:
        _validate_provenance(container["provenance"], f"{name}.provenance")


def _validate_source(value: Any, name: str) -> None:
    source = _object(value, name)
    if set(source) != {"kind", "id"}:
        raise ScoreError(f"{name} must contain only kind and id")
    kind = _string(source.get("kind"), f"{name}.kind", maximum=32)
    if kind not in {"user", "imported", "generated"}:
        raise ScoreError(f"{name}.kind must be user, imported, or generated")
    _string(source.get("id"), f"{name}.id", maximum=200)


def _validate_metadata(value: Any) -> None:
    metadata = _object(value, "metadata")
    allowed = {"title", "composer", "source", "provenance"}
    unknown = set(metadata) - allowed
    if unknown:
        raise ScoreError(f"metadata has unsupported fields: {sorted(unknown)}")
    _string(metadata.get("title"), "metadata.title")
    if "composer" in metadata:
        _string(metadata["composer"], "metadata.composer")
    if "source" in metadata:
        _validate_source(metadata["source"], "metadata.source")
    _validate_optional_provenance(metadata, "metadata")


def _validate_bars(value: Any) -> int:
    if not isinstance(value, list) or not value:
        raise ScoreError("bars must be a non-empty list")

    expected = 1
    allowed = {"number", "repeat_start", "repeat_end", "ending_numbers", "provenance"}
    for index, raw_bar in enumerate(value):
        bar = _object(raw_bar, f"bars[{index}]")
        unknown = set(bar) - allowed
        if unknown:
            raise ScoreError(f"bars[{index}] has unsupported fields: {sorted(unknown)}")
        number = _positive_int(bar.get("number"), f"bars[{index}].number")
        if number != expected:
            raise ScoreError("bars must be contiguous and numbered from 1")
        if "repeat_start" in bar and not isinstance(bar["repeat_start"], bool):
            raise ScoreError(f"bars[{index}].repeat_start must be a boolean")
        if "repeat_end" in bar:
            repeat_end = _positive_int(bar["repeat_end"], f"bars[{index}].repeat_end")
            if repeat_end < 2:
                raise ScoreError(f"bars[{index}].repeat_end must be at least 2")
        if "ending_numbers" in bar:
            endings = bar["ending_numbers"]
            if not isinstance(endings, list) or not endings:
                raise ScoreError(f"bars[{index}].ending_numbers must be a non-empty list")
            normalized: list[int] = []
            for ending_index, ending in enumerate(endings):
                normalized.append(
                    _positive_int(ending, f"bars[{index}].ending_numbers[{ending_index}]")
                )
            if len(set(normalized)) != len(normalized):
                raise ScoreError(f"bars[{index}].ending_numbers must be unique")
            if normalized != sorted(normalized):
                raise ScoreError(f"bars[{index}].ending_numbers must be sorted")
        _validate_optional_provenance(bar, f"bars[{index}]")
        expected += 1

    return len(value)


def _validate_meter_map(value: Any, bar_count: int) -> list[tuple[int, int, int]]:
    if not isinstance(value, list) or not value:
        raise ScoreError("meter_map must be a non-empty list")

    result: list[tuple[int, int, int]] = []
    previous_bar = 0
    for index, raw_entry in enumerate(value):
        entry = _object(raw_entry, f"meter_map[{index}]")
        allowed = {"bar", "beats", "beat_unit", "provenance"}
        unknown = set(entry) - allowed
        if unknown:
            raise ScoreError(f"meter_map[{index}] has unsupported fields: {sorted(unknown)}")
        bar = _positive_int(entry.get("bar"), f"meter_map[{index}].bar")
        beats = _positive_int(entry.get("beats"), f"meter_map[{index}].beats")
        beat_unit = _positive_int(entry.get("beat_unit"), f"meter_map[{index}].beat_unit")
        if bar > bar_count:
            raise ScoreError(f"meter_map[{index}].bar exceeds score bar count")
        if bar <= previous_bar:
            raise ScoreError("meter_map bars must be strictly increasing")
        if beat_unit not in {1, 2, 4, 8, 16, 32, 64}:
            raise ScoreError(f"meter_map[{index}].beat_unit is unsupported")
        if beats > 64:
            raise ScoreError(f"meter_map[{index}].beats is unsupported")
        _validate_optional_provenance(entry, f"meter_map[{index}]")
        previous_bar = bar
        result.append((bar, beats, beat_unit))

    if result[0][0] != 1:
        raise ScoreError("meter_map must start at bar 1")
    return result


def _meter_for_bar(meters: list[tuple[int, int, int]], bar: int) -> tuple[int, int]:
    active = meters[0]
    for candidate in meters[1:]:
        if candidate[0] > bar:
            break
        active = candidate
    return active[1], active[2]


def _validate_location(
    value: Any,
    name: str,
    *,
    bar_count: int,
    meters: list[tuple[int, int, int]],
) -> tuple[int, Fraction, int, int]:
    location = _object(value, name)
    if set(location) != {"bar", "beat"}:
        raise ScoreError(f"{name} must contain only bar and beat")
    bar = _positive_int(location.get("bar"), f"{name}.bar")
    if bar > bar_count:
        raise ScoreError(f"{name}.bar exceeds score bar count")
    beat = _fraction(location.get("beat"), f"{name}.beat", positive=True)
    beats, beat_unit = _meter_for_bar(meters, bar)
    if beat < 1 or beat >= beats + 1:
        raise ScoreError(f"{name}.beat must be inside bar {bar}")
    return bar, beat, beats, beat_unit


def _validate_tempo_map(
    value: Any,
    *,
    bar_count: int,
    meters: list[tuple[int, int, int]],
) -> None:
    if not isinstance(value, list):
        raise ScoreError("tempo_map must be a list")

    previous: tuple[int, Fraction] | None = None
    for index, raw_entry in enumerate(value):
        entry = _object(raw_entry, f"tempo_map[{index}]")
        allowed = {"location", "bpm", "beat_unit", "provenance"}
        unknown = set(entry) - allowed
        if unknown:
            raise ScoreError(f"tempo_map[{index}] has unsupported fields: {sorted(unknown)}")
        bar, beat, _, _ = _validate_location(
            entry.get("location"),
            f"tempo_map[{index}].location",
            bar_count=bar_count,
            meters=meters,
        )
        bpm = entry.get("bpm")
        if (
            isinstance(bpm, bool)
            or not isinstance(bpm, (int, float))
            or not math.isfinite(bpm)
            or bpm <= 0
        ):
            raise ScoreError(f"tempo_map[{index}].bpm must be a positive finite number")
        _fraction(entry.get("beat_unit"), f"tempo_map[{index}].beat_unit", positive=True)
        _validate_optional_provenance(entry, f"tempo_map[{index}]")
        current = (bar, beat)
        if previous is not None and current <= previous:
            raise ScoreError("tempo_map locations must be strictly increasing")
        previous = current


def _validate_key_map(value: Any, *, bar_count: int) -> None:
    if not isinstance(value, list) or not value:
        raise ScoreError("key_map must be a non-empty list when present")

    previous_bar = 0
    for index, raw_entry in enumerate(value):
        entry = _object(raw_entry, f"key_map[{index}]")
        allowed = {"bar", "fifths", "mode", "provenance"}
        unknown = set(entry) - allowed
        if unknown:
            raise ScoreError(f"key_map[{index}] has unsupported fields: {sorted(unknown)}")
        bar = _positive_int(entry.get("bar"), f"key_map[{index}].bar")
        if bar > bar_count:
            raise ScoreError(f"key_map[{index}].bar exceeds score bar count")
        if bar <= previous_bar:
            raise ScoreError("key_map bars must be strictly increasing")
        fifths = entry.get("fifths")
        if isinstance(fifths, bool) or not isinstance(fifths, int) or not -7 <= fifths <= 7:
            raise ScoreError(f"key_map[{index}].fifths must be an integer from -7 to 7")
        _string(entry.get("mode"), f"key_map[{index}].mode", maximum=32)
        _validate_optional_provenance(entry, f"key_map[{index}]")
        previous_bar = bar
    if value[0]["bar"] != 1:
        raise ScoreError("key_map must start at bar 1 when present")


def _validate_pitch(value: Any, name: str) -> tuple[str, int, int, int]:
    pitch = _object(value, name)
    if set(pitch) != {"step", "alter", "octave"}:
        raise ScoreError(f"{name} must contain only step, alter, and octave")
    step = pitch.get("step")
    if not isinstance(step, str) or step not in _PITCH_CLASS:
        raise ScoreError(f"{name}.step must be one of {sorted(_PITCH_CLASS)}")
    alter = pitch.get("alter")
    if isinstance(alter, bool) or not isinstance(alter, int) or not -2 <= alter <= 2:
        raise ScoreError(f"{name}.alter must be an integer from -2 to 2")
    octave = pitch.get("octave")
    if isinstance(octave, bool) or not isinstance(octave, int) or not -1 <= octave <= 9:
        raise ScoreError(f"{name}.octave must be an integer from -1 to 9")
    midi = 12 * (octave + 1) + _PITCH_CLASS[step] + alter
    if not 0 <= midi <= 127:
        raise ScoreError(f"{name} is outside the supported sounding pitch range")
    return step, alter, octave, midi


def _validate_tuning(value: Any, name: str) -> dict[int, int]:
    if not isinstance(value, list) or not value:
        raise ScoreError(f"{name} must be a non-empty list")
    tuning: dict[int, int] = {}
    for index, raw_string in enumerate(value):
        item = _object(raw_string, f"{name}[{index}]")
        if set(item) != {"string", "pitch"}:
            raise ScoreError(f"{name}[{index}] must contain only string and pitch")
        string_number = _positive_int(item.get("string"), f"{name}[{index}].string")
        if string_number in tuning:
            raise ScoreError(f"{name} contains duplicate string {string_number}")
        _, _, _, midi = _validate_pitch(item.get("pitch"), f"{name}[{index}].pitch")
        tuning[string_number] = midi
    return tuning


def _validate_instrument(value: Any, name: str) -> None:
    instrument = _object(value, name)
    allowed = {"name", "family", "midi"}
    unknown = set(instrument) - allowed
    if unknown:
        raise ScoreError(f"{name} has unsupported fields: {sorted(unknown)}")
    _string(instrument.get("name"), f"{name}.name")
    _string(instrument.get("family"), f"{name}.family", maximum=64)

    if "midi" in instrument:
        midi = _object(instrument["midi"], f"{name}.midi")
        allowed_midi = {"program", "channel", "percussion"}
        unknown_midi = set(midi) - allowed_midi
        if unknown_midi:
            raise ScoreError(
                f"{name}.midi has unsupported fields: {sorted(unknown_midi)}"
            )
        if not midi:
            raise ScoreError(f"{name}.midi must not be empty")
        if "program" in midi:
            program = midi["program"]
            if isinstance(program, bool) or not isinstance(program, int) or not 0 <= program <= 127:
                raise ScoreError(f"{name}.midi.program must be an integer from 0 to 127")
        if "channel" in midi:
            channel = midi["channel"]
            if isinstance(channel, bool) or not isinstance(channel, int) or not 1 <= channel <= 16:
                raise ScoreError(f"{name}.midi.channel must be an integer from 1 to 16")
        if "percussion" in midi and not isinstance(midi["percussion"], bool):
            raise ScoreError(f"{name}.midi.percussion must be a boolean")


def _validate_string_list(value: Any, name: str) -> None:
    if not isinstance(value, list):
        raise ScoreError(f"{name} must be a list")
    seen: set[str] = set()
    for index, item in enumerate(value):
        normalized = _string(item, f"{name}[{index}]", maximum=64)
        if normalized in seen:
            raise ScoreError(f"{name} must not contain duplicates")
        seen.add(normalized)


def _validate_techniques(value: Any, name: str) -> None:
    if not isinstance(value, list):
        raise ScoreError(f"{name} must be a list")
    for index, raw_technique in enumerate(value):
        technique = _object(raw_technique, f"{name}[{index}]")
        allowed = {"name", "amount"}
        unknown = set(technique) - allowed
        if unknown:
            raise ScoreError(f"{name}[{index}] has unsupported fields: {sorted(unknown)}")
        _string(technique.get("name"), f"{name}[{index}].name", maximum=64)
        if "amount" in technique:
            _fraction(technique["amount"], f"{name}[{index}].amount", positive=True)


def _validate_tuplet(value: Any, name: str) -> tuple[str, int, int, Fraction]:
    tuplet = _object(value, name)
    if set(tuplet) != {"id", "actual", "normal", "base"}:
        raise ScoreError(f"{name} must contain only id, actual, normal, and base")
    tuplet_id = _slug(tuplet.get("id"), f"{name}.id")
    actual = _positive_int(tuplet.get("actual"), f"{name}.actual")
    normal = _positive_int(tuplet.get("normal"), f"{name}.normal")
    base = _fraction(tuplet.get("base"), f"{name}.base", positive=True)
    return tuplet_id, actual, normal, base


def _validate_event(
    value: Any,
    name: str,
    *,
    bar_count: int,
    meters: list[tuple[int, int, int]],
    tuning: dict[int, int] | None,
    tuplets: dict[str, tuple[int, int, Fraction]],
) -> None:
    event = _object(value, name)
    kind = event.get("kind")
    common = {"kind", "location", "duration", "voice", "provenance"}
    note_only = {
        "pitch",
        "position",
        "tie",
        "tuplet",
        "articulations",
        "techniques",
        "dynamics",
    }
    if kind == "note":
        allowed = common | note_only
    elif kind == "rest":
        allowed = common
    else:
        raise ScoreError(f"{name}.kind must be 'note' or 'rest'")
    unknown = set(event) - allowed
    if unknown:
        raise ScoreError(f"{name} {kind} has unsupported fields: {sorted(unknown)}")

    _, beat, beats, beat_unit = _validate_location(
        event.get("location"),
        f"{name}.location",
        bar_count=bar_count,
        meters=meters,
    )
    duration = _fraction(event.get("duration"), f"{name}.duration", positive=True)
    _positive_int(event.get("voice"), f"{name}.voice")
    start = (beat - 1) * Fraction(1, beat_unit)
    bar_duration = Fraction(beats, beat_unit)
    if start + duration > bar_duration:
        raise ScoreError(f"{name} crosses bar boundary")
    _validate_optional_provenance(event, name)

    if kind == "rest":
        return

    if "pitch" not in event:
        raise ScoreError(f"{name}.note.pitch is required")
    _, _, _, pitch_midi = _validate_pitch(event["pitch"], f"{name}.pitch")

    if "position" in event:
        position = _object(event["position"], f"{name}.position")
        if set(position) != {"string", "fret"}:
            raise ScoreError(f"{name}.position must contain only string and fret")
        string_number = _positive_int(position.get("string"), f"{name}.position.string")
        fret = _nonnegative_int(position.get("fret"), f"{name}.position.fret")
        if fret > 36:
            raise ScoreError(f"{name}.position.fret must be at most 36")
        if tuning is None:
            raise ScoreError(f"{name}.position requires declared guitar tuning")
        if string_number not in tuning:
            raise ScoreError(f"{name}.position.string {string_number} is not present in tuning")
        if tuning[string_number] + fret != pitch_midi:
            raise ScoreError(f"{name}.pitch does not match guitar position")

    if "tie" in event:
        tie = event["tie"]
        if not isinstance(tie, str) or tie not in {"start", "continue", "stop"}:
            raise ScoreError(f"{name}.tie must be start, continue, or stop")
    if "articulations" in event:
        _validate_string_list(event["articulations"], f"{name}.articulations")
    if "techniques" in event:
        _validate_techniques(event["techniques"], f"{name}.techniques")
    if "dynamics" in event:
        _string(event["dynamics"], f"{name}.dynamics", maximum=32)
    if "tuplet" in event:
        tuplet_id, actual, normal, base = _validate_tuplet(event["tuplet"], f"{name}.tuplet")
        expected_duration = base * Fraction(normal, actual)
        if duration != expected_duration:
            raise ScoreError(f"{name} tuplet duration does not match base * normal / actual")
        definition = (actual, normal, base)
        existing = tuplets.get(tuplet_id)
        if existing is not None and existing != definition:
            raise ScoreError(f"{name} has inconsistent tuplet definition for {tuplet_id}")
        tuplets[tuplet_id] = definition


def _validate_parts(
    value: Any,
    *,
    bar_count: int,
    meters: list[tuple[int, int, int]],
) -> None:
    if not isinstance(value, list):
        raise ScoreError("parts must be a list")

    ids: set[str] = set()
    allowed = {"id", "name", "role", "instrument", "guitar", "events", "provenance"}
    for index, raw_part in enumerate(value):
        part = _object(raw_part, f"parts[{index}]")
        unknown = set(part) - allowed
        if unknown:
            raise ScoreError(f"parts[{index}] has unsupported fields: {sorted(unknown)}")
        part_id = _slug(part.get("id"), f"parts[{index}].id")
        if part_id in ids:
            raise ScoreError(f"duplicate part id: {part_id}")
        ids.add(part_id)
        _string(part.get("name"), f"parts[{index}].name")
        _string(part.get("role"), f"parts[{index}].role", maximum=64)
        _validate_instrument(part.get("instrument"), f"parts[{index}].instrument")
        _validate_optional_provenance(part, f"parts[{index}]")

        tuning: dict[int, int] | None = None
        if "guitar" in part:
            guitar = _object(part["guitar"], f"parts[{index}].guitar")
            if set(guitar) != {"tuning"}:
                raise ScoreError(f"parts[{index}].guitar must contain only tuning")
            tuning = _validate_tuning(guitar.get("tuning"), f"parts[{index}].guitar.tuning")

        events = part.get("events")
        if not isinstance(events, list):
            raise ScoreError(f"parts[{index}].events must be a list")
        tuplets: dict[str, tuple[int, int, Fraction]] = {}
        for event_index, event in enumerate(events):
            _validate_event(
                event,
                f"parts[{index}].events[{event_index}]",
                bar_count=bar_count,
                meters=meters,
                tuning=tuning,
                tuplets=tuplets,
            )


def _validate_sections(value: Any, *, bar_count: int) -> None:
    if not isinstance(value, list):
        raise ScoreError("sections must be a list")
    ids: set[str] = set()
    allowed = {"id", "label", "start_bar", "end_bar", "provenance"}
    for index, raw_section in enumerate(value):
        section = _object(raw_section, f"sections[{index}]")
        unknown = set(section) - allowed
        if unknown:
            raise ScoreError(f"sections[{index}] has unsupported fields: {sorted(unknown)}")
        section_id = _slug(section.get("id"), f"sections[{index}].id")
        if section_id in ids:
            raise ScoreError(f"duplicate section id: {section_id}")
        ids.add(section_id)
        _string(section.get("label"), f"sections[{index}].label")
        start_bar = _positive_int(section.get("start_bar"), f"sections[{index}].start_bar")
        end_bar = _positive_int(section.get("end_bar"), f"sections[{index}].end_bar")
        if start_bar > end_bar or end_bar > bar_count:
            raise ScoreError(f"sections[{index}] has invalid section range")
        _validate_optional_provenance(section, f"sections[{index}]")


def _validate_location_items(
    value: Any,
    name: str,
    *,
    bar_count: int,
    meters: list[tuple[int, int, int]],
    text_field: str,
) -> None:
    if not isinstance(value, list):
        raise ScoreError(f"{name} must be a list")
    previous: tuple[int, Fraction] | None = None
    for index, raw_item in enumerate(value):
        item = _object(raw_item, f"{name}[{index}]")
        allowed = {"location", text_field, "provenance"}
        unknown = set(item) - allowed
        if unknown:
            raise ScoreError(f"{name}[{index}] has unsupported fields: {sorted(unknown)}")
        bar, beat, _, _ = _validate_location(
            item.get("location"),
            f"{name}[{index}].location",
            bar_count=bar_count,
            meters=meters,
        )
        _string(item.get(text_field), f"{name}[{index}].{text_field}")
        _validate_optional_provenance(item, f"{name}[{index}]")
        current = (bar, beat)
        if previous is not None and current <= previous:
            raise ScoreError(f"{name} locations must be strictly increasing")
        previous = current


def validate(document: dict[str, Any]) -> None:
    """Validate one version-1 Score IR document."""

    if not isinstance(document, dict):
        raise ScoreError("score must be an object")

    missing = _REQUIRED_TOP_LEVEL - set(document)
    if missing:
        raise ScoreError(f"score is missing required fields: {sorted(missing)}")
    unknown = set(document) - _REQUIRED_TOP_LEVEL - _OPTIONAL_TOP_LEVEL
    if unknown:
        raise ScoreError(f"score has unsupported fields: {sorted(unknown)}")

    if document.get("schema") != SCHEMA_ID:
        raise ScoreError(f"schema must be {SCHEMA_ID!r}")
    version = document.get("version")
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != SCHEMA_VERSION
    ):
        raise ScoreError(f"version must be {SCHEMA_VERSION}")

    _slug(document.get("id"), "id")
    _validate_metadata(document.get("metadata"))
    bar_count = _validate_bars(document.get("bars"))
    meters = _validate_meter_map(document.get("meter_map"), bar_count)
    _validate_tempo_map(document.get("tempo_map"), bar_count=bar_count, meters=meters)
    if "key_map" in document:
        _validate_key_map(document["key_map"], bar_count=bar_count)
    if "sections" in document:
        _validate_sections(document["sections"], bar_count=bar_count)
    if "rehearsal_marks" in document:
        _validate_location_items(
            document["rehearsal_marks"],
            "rehearsal_marks",
            bar_count=bar_count,
            meters=meters,
            text_field="label",
        )
    if "harmony" in document:
        _validate_location_items(
            document["harmony"],
            "harmony",
            bar_count=bar_count,
            meters=meters,
            text_field="symbol",
        )
    _validate_parts(document.get("parts"), bar_count=bar_count, meters=meters)
    if "provenance" in document:
        _validate_provenance(document["provenance"], "score.provenance")


def dumps(document: dict[str, Any]) -> str:
    """Serialize a validated Score IR document to canonical JSON text."""

    validate(document)
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ScoreError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(text: str) -> dict[str, Any]:
    """Parse and validate Score IR JSON, rejecting duplicate object keys."""

    if not isinstance(text, str):
        raise ScoreError("score JSON must be text")
    try:
        document = json.loads(text, object_pairs_hook=_unique_object)
    except ScoreError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise ScoreError(f"invalid score JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ScoreError("score JSON root must be an object")
    validate(document)
    return document
