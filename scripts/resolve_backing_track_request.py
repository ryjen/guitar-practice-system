#!/usr/bin/env python3
"""Resolve a bounded BackingTrackRequest into a canonical BackingTrackSpec."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import backing_track_engine
import bass_engine
import groove_catalog
import midi_workflow
import progression_catalog


REQUEST_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_INSTRUMENTATION = ("drums", "bass", "keys", "pad")
SUPPORTED_REQUEST_BASS_STYLES = ("auto",) + tuple(sorted(bass_engine.SUPPORTED_STYLES))
AUTO_BASS_STYLE_BY_PRESET = {
    "blues-shuffle": "kick-root-fifth",
    "country-train": "kick-root-fifth",
    "funk-wah-16": "kick-root-octave",
    "jazz-swing": "walking",
    "alt-rock": "kick-root",
    "80s-rock": "kick-root-fifth",
    "odd-7-8": "kick-root-fifth",
    "call-response-2x2": "kick-root",
}
TOP_LEVEL_FIELDS = {
    "version",
    "id",
    "title",
    "purpose",
    "key_signature",
    "tonal_center",
    "tempo_bpm",
    "meter",
    "groove_preset",
    "bass_style",
    "count_in_bars",
    "form",
    "instrumentation",
    "arrangement",
}
FORM_FIELDS = {"bars", "progression", "progression_preset", "section_name"}

TRACK_TEMPLATES: dict[str, dict[str, Any]] = {
    "drums": {
        "name": "Drums",
        "role": "drums",
        "channel": 9,
        "velocity": 88,
        "instrument_intent": "stable rhythmic reference selected from the public groove catalog",
    },
    "bass": {
        "name": "Bass",
        "role": "bass",
        "channel": 0,
        "program": 34,
        "velocity": 80,
        "instrument_intent": "bounded bass accompaniment supporting the guitar practice part",
    },
    "keys": {
        "name": "Keys",
        "role": "keys",
        "channel": 1,
        "program": 4,
        "velocity": 68,
        "instrument_intent": "light chord support that leaves room for guitar",
    },
    "pad": {
        "name": "Pad",
        "role": "pad",
        "channel": 2,
        "program": 89,
        "velocity": 58,
        "instrument_intent": "sustained harmonic support kept below the guitar part",
    },
}


def _require(value: Any, expected: type, name: str) -> Any:
    if not isinstance(value, expected):
        raise midi_workflow.ManifestError(f"{name} must be {expected.__name__}")
    return value


def _int_field(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi_workflow.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi_workflow.ManifestError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def _non_empty_string(value: Any, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise midi_workflow.ManifestError(f"{name} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise midi_workflow.ManifestError(
            f"{name} must be at most {maximum} characters"
        )
    return normalized


def _unknown_fields(data: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise midi_workflow.ManifestError(
            f"{name} has unsupported fields: {sorted(unknown)}"
        )


def _validate_meter(value: Any) -> list[int]:
    meter = _require(value, list, "meter")
    if len(meter) != 2 or any(
        isinstance(item, bool) or not isinstance(item, int) for item in meter
    ):
        raise midi_workflow.ManifestError("meter must be [numerator, denominator]")
    numerator, denominator = meter
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
        raise midi_workflow.ManifestError("unsupported meter")
    return [numerator, denominator]


def _validate_tonal_center(value: Any) -> str | None:
    if value is None:
        return None
    tonal_center = _non_empty_string(value, "tonal_center", maximum=8).upper()
    if tonal_center not in progression_catalog.NATURAL_TONAL_CENTERS:
        raise midi_workflow.ManifestError(
            "tonal_center must be one of C, D, E, F, G, A, B in BackingTrackRequest v1"
        )
    return tonal_center


def _validate_progression(value: Any, *, bars: int) -> list[str]:
    progression = _require(value, list, "form.progression")
    if not progression:
        raise midi_workflow.ManifestError("form.progression cannot be empty")
    if len(progression) > bars:
        raise midi_workflow.ManifestError(
            "form.progression cannot contain more entries than form.bars"
        )

    result: list[str] = []
    for index, chord in enumerate(progression):
        chord = _non_empty_string(
            chord,
            f"form.progression[{index}]",
            maximum=16,
        )
        if chord.upper() != "N.C.":
            midi_workflow.chord_notes(chord)
        result.append(chord)
    return result


def _resolve_form_chords(
    form: dict[str, Any],
    *,
    bars: int,
    key_signature: str,
    tonal_center: str | None,
    meter: list[int],
) -> tuple[list[str], str | None]:
    has_progression = "progression" in form
    has_preset = "progression_preset" in form
    if has_progression == has_preset:
        raise midi_workflow.ManifestError(
            "form must contain exactly one of progression or progression_preset"
        )

    if has_progression:
        if tonal_center is not None:
            raise midi_workflow.ManifestError(
                "tonal_center requires a modal progression preset"
            )
        progression = _validate_progression(form["progression"], bars=bars)
        chords = [progression[index % len(progression)] for index in range(bars)]
        return chords, None

    preset_id = _non_empty_string(
        form["progression_preset"],
        "form.progression_preset",
        maximum=64,
    )
    if not ID_PATTERN.fullmatch(preset_id):
        raise midi_workflow.ManifestError(
            "form.progression_preset must be lowercase kebab-case"
        )
    preset = progression_catalog.get_preset(preset_id)
    if preset["meter"] != meter:
        raise midi_workflow.ManifestError(
            f"progression preset {preset_id!r} uses meter "
            f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
        )
    if preset["bars"] != bars:
        raise midi_workflow.ManifestError(
            f"form.bars {bars} does not match progression preset "
            f"{preset_id!r} length {preset['bars']}"
        )
    chords = progression_catalog.resolve_progression(
        preset_id,
        key_signature,
        tonal_center=tonal_center,
    )
    return chords, preset_id


def _validate_instrumentation(value: Any) -> tuple[str, ...]:
    roles = _require(value, list, "instrumentation")
    if not roles:
        raise midi_workflow.ManifestError("instrumentation cannot be empty")
    if any(not isinstance(role, str) for role in roles):
        raise midi_workflow.ManifestError("instrumentation must contain strings")
    if len(set(roles)) != len(roles):
        raise midi_workflow.ManifestError("instrumentation cannot contain duplicates")
    unknown = set(roles) - set(SUPPORTED_INSTRUMENTATION)
    if unknown:
        raise midi_workflow.ManifestError(
            f"unsupported instrumentation: {sorted(unknown)}"
        )
    if "drums" not in roles:
        raise midi_workflow.ManifestError(
            "instrumentation must include drums when groove_preset is supplied"
        )
    return tuple(role for role in SUPPORTED_INSTRUMENTATION if role in roles)


def _validate_arrangement(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    arrangement = _require(value, dict, "arrangement")
    probe = {
        "count_in_bars": 0,
        "sections": [{"bars": 1}],
        "arrangement": json.loads(json.dumps(arrangement)),
    }
    backing_track_engine.parse_arrangement_cycle(probe)
    return json.loads(json.dumps(arrangement))


def _resolve_bass_style(value: Any, *, preset_id: str) -> str:
    style = "auto" if value is None else value
    if not isinstance(style, str) or style not in SUPPORTED_REQUEST_BASS_STYLES:
        raise midi_workflow.ManifestError(
            f"bass_style must be one of {list(SUPPORTED_REQUEST_BASS_STYLES)}"
        )
    if style != "auto":
        return style
    resolved = AUTO_BASS_STYLE_BY_PRESET.get(preset_id)
    if resolved is None:
        raise midi_workflow.ManifestError(
            f"groove preset {preset_id!r} has no automatic bass style"
        )
    return resolved


def validate_request(request: dict[str, Any]) -> None:
    _require(request, dict, "request")
    _unknown_fields(request, TOP_LEVEL_FIELDS, "request")

    if request.get("version") != REQUEST_VERSION:
        raise midi_workflow.ManifestError(
            f"request.version must be {REQUEST_VERSION}"
        )

    request_id = _non_empty_string(request.get("id"), "id", maximum=64)
    if not ID_PATTERN.fullmatch(request_id):
        raise midi_workflow.ManifestError("id must be lowercase kebab-case")
    _non_empty_string(request.get("title"), "title", maximum=120)
    _non_empty_string(request.get("purpose"), "purpose", maximum=500)

    key_signature = _non_empty_string(
        request.get("key_signature"),
        "key_signature",
        maximum=16,
    )
    midi_workflow.key_signature_payload(key_signature)
    tonal_center = _validate_tonal_center(request.get("tonal_center"))

    meter = _validate_meter(request.get("meter"))
    tempo = _int_field(
        request.get("tempo_bpm"),
        name="tempo_bpm",
        minimum=20,
        maximum=300,
    )
    _int_field(
        request.get("count_in_bars", 1),
        name="count_in_bars",
        minimum=0,
        maximum=4,
    )

    preset_id = _non_empty_string(
        request.get("groove_preset"),
        "groove_preset",
        maximum=64,
    )
    preset = groove_catalog.get_preset(preset_id)
    if preset["meter"] != meter:
        raise midi_workflow.ManifestError(
            f"groove preset {preset_id!r} uses meter "
            f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
        )
    minimum_tempo, maximum_tempo = preset["tempo_range_bpm"]
    if not minimum_tempo <= tempo <= maximum_tempo:
        raise midi_workflow.ManifestError(
            f"tempo_bpm {tempo} is outside groove preset {preset_id!r} range "
            f"{minimum_tempo}..{maximum_tempo}"
        )

    form = _require(request.get("form"), dict, "form")
    _unknown_fields(form, FORM_FIELDS, "form")
    bars = _int_field(form.get("bars"), name="form.bars", minimum=1, maximum=128)
    _resolve_form_chords(
        form,
        bars=bars,
        key_signature=key_signature,
        tonal_center=tonal_center,
        meter=meter,
    )
    if "section_name" in form:
        _non_empty_string(
            form["section_name"],
            "form.section_name",
            maximum=64,
        )

    roles = _validate_instrumentation(request.get("instrumentation"))
    if "bass_style" in request and "bass" not in roles:
        raise midi_workflow.ManifestError(
            "bass_style requires bass in instrumentation"
        )
    if "bass" in roles:
        _resolve_bass_style(request.get("bass_style"), preset_id=preset_id)
    _validate_arrangement(request.get("arrangement"))


def resolve_request(request: dict[str, Any]) -> dict[str, Any]:
    """Resolve a validated request into a deterministic BackingTrackSpec dictionary."""
    validate_request(request)

    request_id = _non_empty_string(request["id"], "id", maximum=64)
    title = _non_empty_string(request["title"], "title", maximum=120)
    purpose = _non_empty_string(request["purpose"], "purpose", maximum=500)
    key_signature = _non_empty_string(
        request["key_signature"],
        "key_signature",
        maximum=16,
    )
    tonal_center = _validate_tonal_center(request.get("tonal_center"))
    meter = _validate_meter(request["meter"])
    tempo_bpm = request["tempo_bpm"]
    count_in_bars = request.get("count_in_bars", 1)
    preset_id = _non_empty_string(
        request["groove_preset"],
        "groove_preset",
        maximum=64,
    )
    preset = groove_catalog.get_preset(preset_id)
    form = request["form"]
    bars = form["bars"]
    chords, progression_preset = _resolve_form_chords(
        form,
        bars=bars,
        key_signature=key_signature,
        tonal_center=tonal_center,
        meter=meter,
    )
    section_name = _non_empty_string(
        form.get("section_name", "PRACTICE"),
        "form.section_name",
        maximum=64,
    )
    roles = _validate_instrumentation(request["instrumentation"])

    tracks: list[dict[str, Any]] = []
    for role in roles:
        track = json.loads(json.dumps(TRACK_TEMPLATES[role]))
        if role == "drums":
            track["groove_preset"] = preset_id
        elif role == "bass":
            track["bass"] = {
                "style": _resolve_bass_style(
                    request.get("bass_style"),
                    preset_id=preset_id,
                )
            }
        tracks.append(track)

    provenance: dict[str, Any] = {
        "type": "request",
        "notes": "Resolved deterministically from BackingTrackRequest version 1.",
    }
    if progression_preset is not None:
        provenance["progression_preset"] = progression_preset
        progression = progression_catalog.get_preset(progression_preset)
        modal_context = progression.get("modal_context")
        if modal_context is not None:
            provenance["mode"] = modal_context["mode"]
            provenance["tonal_center"] = tonal_center
            provenance["key_signature"] = key_signature

    spec: dict[str, Any] = {
        "id": request_id,
        "title": title,
        "purpose": purpose,
        "linked_techniques": list(preset["practice_intents"]),
        "linked_songs": [],
        "key_signature": key_signature,
        "tempo_bpm": tempo_bpm,
        "meter": meter,
        "feel": preset["description"],
        "count_in_bars": count_in_bars,
        "sections": [
            {
                "name": section_name,
                "bars": bars,
                "chords": chords,
            }
        ],
        "tracks": tracks,
        "provenance": provenance,
        "outputs": {
            "midi": f"generated/backing-tracks/{request_id}.mid",
            "audio": None,
            "daw_project": None,
        },
    }
    arrangement = _validate_arrangement(request.get("arrangement"))
    if arrangement is not None:
        spec["arrangement"] = arrangement

    backing_track_engine.validate_manifest(spec)
    return spec


def resolve_file(path: Path) -> dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    return resolve_request(request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        spec = resolve_file(args.request)
        payload = json.dumps(spec, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(payload, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
    except (OSError, json.JSONDecodeError, midi_workflow.ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
