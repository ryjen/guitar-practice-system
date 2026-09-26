from __future__ import annotations

import unittest
import wave
from io import BytesIO

from guitar_practice.domain import score
from guitar_practice.domain.audio_profiles import (
    BossRc3ProfileError,
    boss_rc3_filename,
    normalize_boss_rc3_wav,
    score_duration_seconds,
)


def _score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "fixture",
        "metadata": {"title": "Fixture"},
        "bars": [{"number": 1}, {"number": 2}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [
            {"location": {"bar": 1, "beat": [1, 1]}, "bpm": 120, "beat_unit": [1, 4]},
            {"location": {"bar": 2, "beat": [1, 1]}, "bpm": 60, "beat_unit": [1, 4]},
        ],
        "parts": [],
    }
    score.validate(document)
    return document


def _wav(*, rate: int = 44_100, channels: int = 2, width: int = 2, frames: int = 1000) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(width)
        audio.setframerate(rate)
        audio.writeframes(b"\x01" * frames * channels * width)
    return output.getvalue()


class BossRc3ProfileTests(unittest.TestCase):
    def test_score_duration_integrates_realized_tempo_map(self) -> None:
        self.assertEqual(6.0, score_duration_seconds(_score()))

    def test_normalizer_crops_and_pads_to_exact_duration(self) -> None:
        for frames in (100, 1000):
            normalized = normalize_boss_rc3_wav(_wav(frames=frames), duration_seconds=0.01)
            with wave.open(BytesIO(normalized), "rb") as audio:
                self.assertEqual(441, audio.getnframes())
                self.assertEqual(2, audio.getnchannels())
                self.assertEqual(2, audio.getsampwidth())
                self.assertEqual(44_100, audio.getframerate())

    def test_rejects_non_rc3_pcm_shape(self) -> None:
        for kwargs in ({"rate": 48_000}, {"channels": 1}, {"width": 3}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(BossRc3ProfileError):
                    normalize_boss_rc3_wav(_wav(**kwargs), duration_seconds=0.01)

    def test_filename_is_deterministic(self) -> None:
        self.assertEqual("fixture-drums-75pct.wav", boss_rc3_filename("fixture", tempo_factor=0.75))


if __name__ == "__main__":
    unittest.main()
