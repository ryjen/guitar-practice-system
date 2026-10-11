"""Pure guitar-dsp preset v1 validation and canonical serialization."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

SCHEMA_ID = "guitar-dsp.preset"
SCHEMA_VERSION = 1
MAX_WIRE_BYTES = 256

_PRESET_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SUBDIVISIONS = frozenset(
    {
        "free",
        "quarter",
        "dotted-eighth",
        "eighth",
        "eighth-triplet",
        "sixteenth",
    }
)
_TOP_LEVEL = frozenset({"schema", "version", "preset", "tempo_bpm", "parameters"})
_PARAMETER_KEYS = frozenset(
    {
        "delay.feedback_milli",
        "delay.free_ms",
        "delay.mix_milli",
        "delay.subdivision",
    }
)


class DspPresetError(ValueError):
    """Raised when a guitar-dsp preset violates the frozen v1 contract."""


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DspPresetError(f"{name} must be an object")
    return value


def _exact_fields(value: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise DspPresetError(f"{name} missing required fields: {missing}")
    if unknown:
        raise DspPresetError(f"{name} has unsupported fields: {unknown}")


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DspPresetError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise DspPresetError(f"{name} must be between {minimum} and {maximum}")
    return value


def validate(document: Mapping[str, Any]) -> None:
    root = _object(document, "preset")
    _exact_fields(root, _TOP_LEVEL, "preset")

    if root["schema"] != SCHEMA_ID:
        raise DspPresetError(f"schema must be {SCHEMA_ID!r}")
    if isinstance(root["version"], bool) or root["version"] != SCHEMA_VERSION:
        raise DspPresetError(f"version must be integer {SCHEMA_VERSION}")

    preset = root["preset"]
    if (
        not isinstance(preset, str)
        or not 1 <= len(preset) <= 32
        or _PRESET_PATTERN.fullmatch(preset) is None
    ):
        raise DspPresetError("preset must be a 1..32 character lowercase slug")

    _bounded_int(root["tempo_bpm"], "tempo_bpm", 20, 300)

    parameters = _object(root["parameters"], "parameters")
    _exact_fields(parameters, _PARAMETER_KEYS, "parameters")
    _bounded_int(
        parameters["delay.feedback_milli"],
        "delay.feedback_milli",
        0,
        950,
    )
    _bounded_int(parameters["delay.free_ms"], "delay.free_ms", 1, 2000)
    _bounded_int(parameters["delay.mix_milli"], "delay.mix_milli", 0, 1000)

    subdivision = parameters["delay.subdivision"]
    if not isinstance(subdivision, str) or subdivision not in _SUBDIVISIONS:
        raise DspPresetError(
            "delay.subdivision must be one of "
            + ", ".join(sorted(_SUBDIVISIONS))
        )


def dumps(document: Mapping[str, Any]) -> str:
    validate(document)
    parameters = document["parameters"]
    assert isinstance(parameters, Mapping)

    encoded = (
        '{"schema":"guitar-dsp.preset","version":1,"preset":"'
        + str(document["preset"])
        + '","tempo_bpm":'
        + str(document["tempo_bpm"])
        + ',"parameters":{"delay.feedback_milli":'
        + str(parameters["delay.feedback_milli"])
        + ',"delay.free_ms":'
        + str(parameters["delay.free_ms"])
        + ',"delay.mix_milli":'
        + str(parameters["delay.mix_milli"])
        + ',"delay.subdivision":"'
        + str(parameters["delay.subdivision"])
        + '"}}'
    )
    if len(encoded.encode("ascii")) > MAX_WIRE_BYTES:
        raise DspPresetError("canonical preset exceeds 256 bytes")
    return encoded


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DspPresetError(f"duplicate field: {key}")
        result[key] = value
    return result


def loads(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except DspPresetError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise DspPresetError(f"invalid JSON: {exc}") from exc

    root = _object(value, "preset")
    document = dict(root)
    validate(document)
    return document
