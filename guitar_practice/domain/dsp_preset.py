"""Versioned guitar-to-DSP preset contract and canonical JSON encoding."""

from __future__ import annotations

import json
import re
from typing import Any

SCHEMA_ID = "guitar-dsp.preset"
SCHEMA_VERSION = 1
PRESET_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_PRESET_LENGTH = 64

TOP_LEVEL_FIELDS = frozenset(
    {"schema", "version", "preset", "tempo_bpm", "parameters"}
)
PARAMETER_IDS = frozenset(
    {
        "delay.feedback_milli",
        "delay.free_ms",
        "delay.mix_milli",
        "delay.subdivision",
    }
)
DELAY_SUBDIVISIONS = frozenset(
    {
        "free",
        "quarter",
        "dotted-eighth",
        "eighth",
        "eighth-triplet",
        "sixteenth",
    }
)


class DspPresetError(ValueError):
    """A DSP preset document violates the versioned wire contract."""


def _integer(
    value: Any,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise DspPresetError(
            f"{name} must be an integer between {minimum} and {maximum}"
        )
    return value


def _preset_id(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise DspPresetError("preset must be a non-empty lowercase slug")
    if len(value) > MAX_PRESET_LENGTH:
        raise DspPresetError(
            f"preset must be at most {MAX_PRESET_LENGTH} characters"
        )
    if not PRESET_PATTERN.fullmatch(value):
        raise DspPresetError("preset must be a lowercase slug")
    return value


def validate(document: Any) -> None:
    if not isinstance(document, dict):
        raise DspPresetError("DSP preset must be a JSON object")

    if any(not isinstance(key, str) for key in document):
        raise DspPresetError("DSP preset object keys must be strings")
    fields = set(document)
    missing = TOP_LEVEL_FIELDS - fields
    unknown = fields - TOP_LEVEL_FIELDS
    if missing:
        raise DspPresetError(
            f"DSP preset is missing required fields: {sorted(missing)}"
        )
    if unknown:
        raise DspPresetError(
            f"DSP preset has unsupported fields: {sorted(unknown)}"
        )

    if document["schema"] != SCHEMA_ID:
        raise DspPresetError(f"schema must be {SCHEMA_ID!r}")
    if (
        isinstance(document["version"], bool)
        or not isinstance(document["version"], int)
        or document["version"] != SCHEMA_VERSION
    ):
        raise DspPresetError(
            f"version must be exactly {SCHEMA_VERSION}"
        )

    _preset_id(document["preset"])
    _integer(
        document["tempo_bpm"],
        "tempo_bpm",
        minimum=20,
        maximum=300,
    )

    parameters = document["parameters"]
    if not isinstance(parameters, dict):
        raise DspPresetError("parameters must be an object")

    if any(not isinstance(key, str) for key in parameters):
        raise DspPresetError("parameter IDs must be strings")
    parameter_ids = set(parameters)
    missing_parameters = PARAMETER_IDS - parameter_ids
    unknown_parameters = parameter_ids - PARAMETER_IDS
    if missing_parameters:
        raise DspPresetError(
            "parameters is missing required IDs: "
            f"{sorted(missing_parameters)}"
        )
    if unknown_parameters:
        raise DspPresetError(
            "parameters has unsupported IDs: "
            f"{sorted(unknown_parameters)}"
        )

    _integer(
        parameters["delay.feedback_milli"],
        "parameters.delay.feedback_milli",
        minimum=0,
        maximum=950,
    )
    _integer(
        parameters["delay.free_ms"],
        "parameters.delay.free_ms",
        minimum=1,
        maximum=2000,
    )
    _integer(
        parameters["delay.mix_milli"],
        "parameters.delay.mix_milli",
        minimum=0,
        maximum=1000,
    )

    subdivision = parameters["delay.subdivision"]
    if (
        not isinstance(subdivision, str)
        or subdivision not in DELAY_SUBDIVISIONS
    ):
        raise DspPresetError(
            "parameters.delay.subdivision must be one of "
            f"{sorted(DELAY_SUBDIVISIONS)}"
        )


def dumps(document: dict[str, Any]) -> str:
    """Validate and encode one byte-stable canonical JSON document."""

    validate(document)
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"


def _reject_constant(value: str) -> Any:
    raise DspPresetError(
        f"non-finite JSON number is unsupported: {value}"
    )


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DspPresetError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def loads(text: str) -> dict[str, Any]:
    """Decode JSON with duplicate-key rejection, then validate v1."""

    if not isinstance(text, str):
        raise DspPresetError("DSP preset input must be text")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_object,
            parse_constant=_reject_constant,
        )
    except DspPresetError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise DspPresetError(f"invalid DSP preset JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DspPresetError("DSP preset must be a JSON object")
    validate(value)
    return value


def canonicalize(text: str) -> str:
    """Decode, strictly validate, and return canonical JSON."""

    return dumps(loads(text))
