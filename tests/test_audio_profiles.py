from __future__ import annotations

import unittest
import wave
from io import BytesIO

from guitar_practice.domain.audio_profiles import (
    BossRc3ProfileError,
    boss_rc3_filename,
    normalize_boss_rc3_wav,
    song_duration_seconds,
)
from guitar_practice.domain.song import Song, TempoPoint


def _wav(*, rate: int = 44_100, channels: int = 2, width: int = 2, frames: int = 1000) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(width)
        audio.setframerate(rate)
        audio.writeframes(b"\x01" * frames * channels * width)
    return output.getvalue()


class BossRc3ProfileTests(unittest.TestCase):
    def test_song_duration_integrates_tempo_map(self) -> None:
        song = Song(
            source_id="fixture",
            title="Fixture",
            duration_quarters=8.0,
            tempo_map=(
                TempoPoint(position=0.0, bpm=120.0),
                TempoPoint(position=4.0, bpm=60.0),
            ),
        )
        self.assertEqual(6.0, song_duration_seconds(song))

    def test_normalizer_crops_renderer_tail_to_exact_duration(self) -> None:
        normalized = normalize_boss_rc3_wav(_wav(frames=1000), duration_seconds=0.01)
        with wave.open(BytesIO(normalized), "rb") as audio:
            self.assertEqual(2, audio.getnchannels())
            self.assertEqual(2, audio.getsampwidth())
            self.assertEqual(44_100, audio.getframerate())
            self.assertEqual(441, audio.getnframes())

    def test_normalizer_zero_pads_short_audio_to_exact_duration(self) -> None:
        normalized = normalize_boss_rc3_wav(_wav(frames=100), duration_seconds=0.01)
        with wave.open(BytesIO(normalized), "rb") as audio:
            frames = audio.readframes(audio.getnframes())
            self.assertEqual(441, audio.getnframes())
            self.assertTrue(frames.endswith(b"\x00" * 32))

    def test_rejects_non_rc3_pcm_shape(self) -> None:
        for kwargs in (
            {"rate": 48_000},
            {"channels": 1},
            {"width": 3},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(BossRc3ProfileError):
                    normalize_boss_rc3_wav(_wav(**kwargs), duration_seconds=0.01)

    def test_filename_is_deterministic_and_safe(self) -> None:
        self.assertEqual(
            "fixture-drums-75pct.wav",
            boss_rc3_filename("fixture", tempo_factor=0.75),
        )


if __name__ == "__main__":
    unittest.main()
