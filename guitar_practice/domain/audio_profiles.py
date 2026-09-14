"""Pure hardware audio profiles for deterministic looper exports."""

from __future__ import annotations

import math
import re
import wave
from io import BytesIO

from guitar_practice.domain.song import Song

_RC3_SAMPLE_RATE = 44_100
_RC3_CHANNELS = 2
_RC3_SAMPLE_WIDTH = 2
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class BossRc3ProfileError(ValueError):
    """Raised when audio cannot satisfy the BOSS RC-3 WAV contract."""


def song_duration_seconds(song: Song) -> float:
    if song.duration_quarters is None:
        raise BossRc3ProfileError("song has no structural duration")

    end = song.duration_quarters
    position = 0.0
    bpm = 120.0
    seconds = 0.0
    for point in song.tempo_map:
        if point.position >= end:
            break
        if point.position > position:
            seconds += (point.position - position) * 60.0 / bpm
            position = point.position
        bpm = point.bpm
    seconds += (end - position) * 60.0 / bpm
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
