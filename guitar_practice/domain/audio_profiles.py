"""Pure hardware audio profiles for deterministic looper exports."""

from __future__ import annotations

import math
import re
import wave
from fractions import Fraction
from io import BytesIO
from typing import Any, Mapping

from guitar_practice.domain import score

_RC3_SAMPLE_RATE = 44_100
_RC3_CHANNELS = 2
_RC3_SAMPLE_WIDTH = 2
_SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class BossRc3ProfileError(ValueError):
    """Raised when audio cannot satisfy the BOSS RC-3 WAV contract."""


def _fraction(value: list[int]) -> Fraction:
    return Fraction(value[0], value[1])


def _meter_for_bar(document: Mapping[str, Any], bar: int) -> Mapping[str, Any]:
    active = document["meter_map"][0]
    for item in document["meter_map"][1:]:
        if item["bar"] > bar:
            break
        active = item
    return active


def _bar_starts_quarters(document: Mapping[str, Any]) -> tuple[Fraction, ...]:
    starts = [Fraction(0)]
    for bar in range(1, len(document["bars"]) + 1):
        meter = _meter_for_bar(document, bar)
        starts.append(
            starts[-1] + Fraction(int(meter["beats"]) * 4, int(meter["beat_unit"]))
        )
    return tuple(starts)


def _location_quarters(
    document: Mapping[str, Any],
    starts: tuple[Fraction, ...],
    location: Mapping[str, Any],
) -> Fraction:
    bar = int(location["bar"])
    beat = _fraction(location["beat"])
    meter = _meter_for_bar(document, bar)
    return starts[bar - 1] + (beat - 1) * Fraction(4, int(meter["beat_unit"]))


def score_duration_seconds(document: Mapping[str, Any]) -> float:
    canonical = dict(document)
    score.validate(canonical)
    starts = _bar_starts_quarters(canonical)
    end = starts[-1]
    position = Fraction(0)
    quarter_bpm = 120.0
    seconds = 0.0

    for point in canonical["tempo_map"]:
        point_position = _location_quarters(canonical, starts, point["location"])
        if point_position > end:
            break
        if point_position > position:
            seconds += float(point_position - position) * 60.0 / quarter_bpm
            position = point_position
        unit = _fraction(point["beat_unit"])
        quarter_bpm = float(point["bpm"]) * 4.0 * float(unit)
        if not math.isfinite(quarter_bpm) or quarter_bpm <= 0:
            raise BossRc3ProfileError("tempo must resolve to positive quarter-note BPM")

    seconds += float(end - position) * 60.0 / quarter_bpm
    return seconds


def normalize_boss_rc3_wav(wav_bytes: bytes, *, duration_seconds: float) -> bytes:
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise BossRc3ProfileError("RC-3 duration must be positive and finite")

    try:
        source = wave.open(BytesIO(wav_bytes), "rb")
    except (wave.Error, EOFError) as exc:
        raise BossRc3ProfileError("audio must be a readable WAV file") from exc

    with source:
        if source.getnchannels() != _RC3_CHANNELS:
            raise BossRc3ProfileError("RC-3 WAV must be stereo")
        if source.getsampwidth() != _RC3_SAMPLE_WIDTH:
            raise BossRc3ProfileError("RC-3 WAV must use 16-bit PCM")
        if source.getframerate() != _RC3_SAMPLE_RATE:
            raise BossRc3ProfileError("RC-3 WAV must use a 44.1 kHz sample rate")
        if source.getcomptype() != "NONE":
            raise BossRc3ProfileError("RC-3 WAV must use linear PCM")
        frames = source.readframes(source.getnframes())

    target_frames = max(1, round(duration_seconds * _RC3_SAMPLE_RATE))
    frame_size = _RC3_CHANNELS * _RC3_SAMPLE_WIDTH
    target_bytes = target_frames * frame_size
    normalized_frames = frames[:target_bytes].ljust(target_bytes, b"\x00")

    output = BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(_RC3_CHANNELS)
        target.setsampwidth(_RC3_SAMPLE_WIDTH)
        target.setframerate(_RC3_SAMPLE_RATE)
        target.writeframes(normalized_frames)
    return output.getvalue()


def boss_rc3_filename(source_id: str, *, tempo_factor: float) -> str:
    if _SAFE_ID.fullmatch(source_id) is None:
        raise BossRc3ProfileError("source id is not safe for an RC-3 filename")
    if not math.isfinite(tempo_factor) or tempo_factor <= 0:
        raise BossRc3ProfileError("tempo factor must be positive and finite")

    percent = tempo_factor * 100.0
    if math.isclose(percent, round(percent), rel_tol=0.0, abs_tol=1e-9):
        tempo = str(int(round(percent)))
    else:
        tempo = f"{percent:.3f}".rstrip("0").rstrip(".").replace(".", "p")
    return f"{source_id}-drums-{tempo}pct.wav"
