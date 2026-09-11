"""Deterministic BackingTrackRequest validation and resolution."""

from __future__ import annotations

import copy
import re
from typing import Any

from guitar_practice.domain import backing, bass, groove, midi, progression

REQUEST_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_INSTRUMENTATION = ("drums", "bass", "keys", "pad")
SUPPORTED_REQUEST_BASS_STYLES = ("auto",) + tuple(sorted(bass.SUPPORTED_STYLES))
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
        "instrument_intent": (
            "stable rhythmic reference selected from the public groove catalog"
        ),
    },
    "bass": {
        "name": "Bass",
        "role": "bass",
        "channel": 0,
        "program": 34,
        "velocity": 80,
        "instrument_intent": (
            "bounded bass accompaniment supporting the guitar practice part"
        ),
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
        raise midi.ManifestError(f"{name} must be {expected.__name__}")
    return value


def _int_field(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise midi.ManifestError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise midi.ManifestError(f"{name} must be between {minimum} and {maximum}")
    return value


def _non_empty_string(value: Any, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise midi.ManifestError(f"{name} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise midi.ManifestError(f"{name} must be at most {maximum} characters")
    return normalized


def _unknown_fields(data: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise midi.ManifestError(f"{name} has unsupported fields: {sorted(unknown)}")


def _validate_meter(value: Any) -> list[int]:
    meter = _require(value, list, "meter")
    if len(meter) != 2 or any(
        isinstance(item, bool) or not isinstance(item, int) for item in meter
    ):
        raise midi.ManifestError("meter must be [numerator, denominator]")
    numerator, denominator = meter
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16}:
        raise midi.ManifestError("unsupported meter")
    return [numerator, denominator]


def _validate_tonal_center(value: Any) -> str | None:
    if value is None:
        return None
    tonal_center = _non_empty_string(value, "tonal_center", maximum=8).upper()
    if tonal_center not in progression.NATURAL_TONAL_CENTERS:
        raise midi.ManifestError(
            "tonal_center must be one of C, D, E, F, G, A, B in BackingTrackRequest v1"
        )
    return tonal_center


def _validate_progression(value: Any, *, bars: int) -> list[str]:
    values = _require(value, list, "form.progression")
    if not values:
        raise midi.ManifestError("form.progression cannot be empty")
    if len(values) > bars:
        raise midi.ManifestError(
            "form.progression cannot contain more entries than form.bars"
        )

    result: list[str] = []
    for index, chord in enumerate(values):
        chord = _non_empty_string(
            chord,
            f"form.progression[{index}]",
            maximum=16,
        )
        if chord.upper() != "N.C.":
            midi.chord_notes(chord)
        result.append(chord)
    return result


def _resolve_form_chords(
    form: dict[str, Any],
    *,
    bars: int,
    key_signature: str,
    tonal_center: str | None,
    meter: list[int],
    progression_catalog: dict[str, Any],
) -> tuple[list[str], str | None]:
    has_progression = "progression" in form
    has_preset = "progression_preset" in form
    if has_progression == has_preset:
        raise midi.ManifestError(
            "form must contain exactly one of progression or progression_preset"
        )

    if has_progression:
        if tonal_center is not None:
            raise midi.ManifestError("tonal_center requires a modal progression preset")
        values = _validate_progression(form["progression"], bars=bars)
        return [values[index % len(values)] for index in range(bars)], None

    preset_id = _non_empty_string(
        form["progression_preset"],
        "form.progression_preset",
        maximum=64,
    )
    if not ID_PATTERN.fullmatch(preset_id):
        raise midi.ManifestError(
            "form.progression_preset must be lowercase kebab-case"
        )
    try:
        preset = progression.get_preset(progression_catalog, preset_id)
    except progression.ProgressionError as exc:
        raise midi.ManifestError(str(exc)) from exc
    if preset["meter"] != meter:
        raise midi.ManifestError(
            f"progression preset {preset_id!r} uses meter "
            f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
        )
    if preset["bars"] != bars:
        raise midi.ManifestError(
            f"form.bars {bars} does not match progression preset "
            f"{preset_id!r} length {preset['bars']}"
        )
    try:
        chords = progression.resolve_progression(
            progression_catalog,
            preset_id,
            key_signature,
            tonal_center=tonal_center,
        )
    except progression.ProgressionError as exc:
        raise midi.ManifestError(str(exc)) from exc
    return chords, preset_id


def _validate_instrumentation(value: Any) -> tuple[str, ...]:
    roles = _require(value, list, "instrumentation")
    if not roles:
        raise midi.ManifestError("instrumentation cannot be empty")
    if any(not isinstance(role, str) for role in roles):
        raise midi.ManifestError("instrumentation must contain strings")
    if len(set(roles)) != len(roles):
        raise midi.ManifestError("instrumentation cannot contain duplicates")
    unknown = set(roles) - set(SUPPORTED_INSTRUMENTATION)
    if unknown:
        raise midi.ManifestError(f"unsupported instrumentation: {sorted(unknown)}")
    if "drums" not in roles:
        raise midi.ManifestError(
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
        "arrangement": copy.deepcopy(arrangement),
    }
    backing.parse_arrangement_cycle(probe)
    return copy.deepcopy(arrangement)


def _resolve_bass_style(value: Any, *, preset_id: str) -> str:
    style = "auto" if value is None else value
    if not isinstance(style, str) or style not in SUPPORTED_REQUEST_BASS_STYLES:
        raise midi.ManifestError(
            f"bass_style must be one of {list(SUPPORTED_REQUEST_BASS_STYLES)}"
        )
    if style != "auto":
        return style
    resolved = AUTO_BASS_STYLE_BY_PRESET.get(preset_id)
    if resolved is None:
        raise midi.ManifestError(
            f"groove preset {preset_id!r} has no automatic bass style"
        )
    return resolved


def validate_request(
    request: dict[str, Any],
    groove_catalog: dict[str, Any],
    progression_catalog: dict[str, Any],
) -> None:
    _require(request, dict, "request")
    _unknown_fields(request, TOP_LEVEL_FIELDS, "request")

    if request.get("version") != REQUEST_VERSION:
        raise midi.ManifestError(f"request.version must be {REQUEST_VERSION}")

    request_id = _non_empty_string(request.get("id"), "id", maximum=64)
    if not ID_PATTERN.fullmatch(request_id):
        raise midi.ManifestError("id must be lowercase kebab-case")
    _non_empty_string(request.get("title"), "title", maximum=120)
    _non_empty_string(request.get("purpose"), "purpose", maximum=500)

    key_signature = _non_empty_string(
        request.get("key_signature"),
        "key_signature",
        maximum=16,
    )
    midi.key_signature_payload(key_signature)
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
    preset = groove.get_preset(groove_catalog, preset_id)
    if preset["meter"] != meter:
        raise midi.ManifestError(
            f"groove preset {preset_id!r} uses meter "
            f"{preset['meter'][0]}/{preset['meter'][1]}, not {meter[0]}/{meter[1]}"
        )
    minimum_tempo, maximum_tempo = preset["tempo_range_bpm"]
    if not minimum_tempo <= tempo <= maximum_tempo:
        raise midi.ManifestError(
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
        progression_catalog=progression_catalog,
    )
    if "section_name" in form:
        _non_empty_string(form["section_name"], "form.section_name", maximum=64)

    roles = _validate_instrumentation(request.get("instrumentation"))
    if "bass_style" in request and "bass" not in roles:
        raise midi.ManifestError("bass_style requires bass in instrumentation")
    if "bass" in roles:
        _resolve_bass_style(request.get("bass_style"), preset_id=preset_id)
    _validate_arrangement(request.get("arrangement"))


def resolve_request(
    request: dict[str, Any],
    groove_catalog: dict[str, Any],
    progression_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a validated request into a deterministic BackingTrackSpec."""
    validate_request(request, groove_catalog, progression_catalog)

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
    preset = groove.get_preset(groove_catalog, preset_id)
    form = request["form"]
    bars = form["bars"]
    chords, progression_preset = _resolve_form_chords(
        form,
        bars=bars,
        key_signature=key_signature,
        tonal_center=tonal_center,
        meter=meter,
        progression_catalog=progression_catalog,
    )
    section_name = _non_empty_string(
        form.get("section_name", "PRACTICE"),
        "form.section_name",
        maximum=64,
    )
    roles = _validate_instrumentation(request["instrumentation"])

    tracks: list[dict[str, Any]] = []
    for role in roles:
        track = copy.deepcopy(TRACK_TEMPLATES[role])
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
        progression_spec = progression.get_preset(
            progression_catalog,
            progression_preset,
        )
        modal_context = progression_spec.get("modal_context")
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
        "sections": [{"name": section_name, "bars": bars, "chords": chords}],
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

    backing.validate_manifest(spec, groove_catalog)
    return spec
