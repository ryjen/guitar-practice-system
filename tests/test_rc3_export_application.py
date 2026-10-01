from __future__ import annotations

import unittest
import wave
from io import BytesIO
from typing import Any, Mapping

from guitar_practice.application.ports import AudioRenderProfile, RenderedAudio
from guitar_practice.application.rc3_export import ExportBossRc3Drums
from guitar_practice.domain import midi, score


class MemoryDocuments:
    def __init__(self, values: Mapping[str, Mapping[str, Any]]) -> None:
        self.values = dict(values)
        self.writes: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.writes[path] = document


class MemoryArtifacts:
    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.writes[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.writes[path] = data


def _wav(frames: int) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(44_100)
        audio.writeframes(b"\x01" * frames * 4)
    return output.getvalue()


class FakeRenderer:
    def __init__(self) -> None:
        self.seen: list[tuple[bytes, AudioRenderProfile]] = []

    def render(self, data: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        self.seen.append((data, profile))
        return RenderedAudio(_wav(300_000), "fake", "1", "fixture.sf2")


def _document() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "fixture",
        "metadata": {"title": "Fixture"},
        "bars": [{"number": 1}, {"number": 2}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [{"location": {"bar": 1, "beat": [1, 1]}, "bpm": 120, "beat_unit": [1, 4]}],
        "sections": [
            {"id": "intro", "label": "Intro", "start_bar": 1, "end_bar": 1},
            {"id": "chorus", "label": "Chorus A/B", "start_bar": 2, "end_bar": 2},
        ],
        "parts": [
            {
                "id": "guitar",
                "name": "Guitar",
                "role": "guitar",
                "instrument": {"name": "Electric Guitar", "family": "guitar"},
                "events": [],
                "provenance": {"kind": "imported", "source": "track-role:instrument"},
            },
            {
                "id": "drums",
                "name": "Drums",
                "role": "drums",
                "instrument": {"name": "Drum Kit", "family": "drums", "midi": {"channel": 10, "percussion": True}},
                "events": [
                    {"kind": "note", "location": {"bar": 1, "beat": [1, 1]}, "duration": [1, 4], "voice": 1, "pitch": {"step": "C", "alter": 0, "octave": 5}},
                    {"kind": "note", "location": {"bar": 2, "beat": [1, 1]}, "duration": [1, 4], "voice": 1, "pitch": {"step": "D", "alter": 0, "octave": 5}},
                ],
            },
        ],
    }
    score.validate(document)
    return document


class Rc3ExportApplicationTests(unittest.TestCase):
    def test_exports_score_derived_drums_and_exact_wav_duration(self) -> None:
        documents = MemoryDocuments({"scores/fixture.json": _document()})
        artifacts = MemoryArtifacts()
        renderer = FakeRenderer()

        metadata = ExportBossRc3Drums(documents, artifacts, renderer).execute(
            "scores/fixture.json",
            "renders/fixture.wav",
            tempo_factor=0.5,
        )

        report = midi.inspect(artifacts["renders/fixture.mid"] if False else artifacts.writes["renders/fixture.mid"])
        self.assertEqual(["Conductor", "Drums"], report["track_names"])
        with wave.open(BytesIO(artifacts.writes["renders/fixture.wav"]), "rb") as audio:
            self.assertEqual(352_800, audio.getnframes())
        self.assertEqual(["drums"], metadata["selected_part_ids"])
        self.assertEqual("boss-rc3", metadata["target"])
        self.assertEqual(metadata, documents.writes["renders/fixture.wav.json"])

    def test_full_song_expands_repeat_form_before_audio_duration(self) -> None:
        document = _document()
        document["bars"][0]["repeat_start"] = True
        document["bars"][1]["repeat_end"] = 2
        score.validate(document)
        documents = MemoryDocuments({"scores/fixture.json": document})
        artifacts = MemoryArtifacts()

        metadata = ExportBossRc3Drums(documents, artifacts, FakeRenderer()).execute(
            "scores/fixture.json",
            "renders/repeated.wav",
            tempo_factor=1.0,
        )

        self.assertEqual(8.0, metadata["duration_seconds"])
        with wave.open(BytesIO(artifacts.writes["renders/repeated.wav"]), "rb") as audio:
            self.assertEqual(352_800, audio.getnframes())

    def test_named_section_uses_safe_default_filename(self) -> None:
        documents = MemoryDocuments({"scores/fixture.json": _document()})
        artifacts = MemoryArtifacts()
        metadata = ExportBossRc3Drums(documents, artifacts, FakeRenderer()).execute(
            "scores/fixture.json",
            None,
            tempo_factor=1.0,
            section_name="chorus a/b",
        )
        self.assertEqual(
            "generated/rc3/fixture-drums-100pct-section-Chorus-A-B-chorus-bars2-2.wav",
            metadata["artifact"],
        )
        self.assertEqual([2, 2], metadata["bar_range"])

    def test_distinct_section_labels_do_not_collide_after_sanitization(self) -> None:
        document = _document()
        document["sections"] = [
            {"id": "first", "label": "A/B", "start_bar": 1, "end_bar": 1},
            {"id": "second", "label": "A B", "start_bar": 1, "end_bar": 1},
        ]
        score.validate(document)
        first = ExportBossRc3Drums(
            MemoryDocuments({"score.json": document}), MemoryArtifacts(), FakeRenderer()
        ).execute("score.json", None, tempo_factor=1.0, section_name="A/B")
        second = ExportBossRc3Drums(
            MemoryDocuments({"score.json": document}), MemoryArtifacts(), FakeRenderer()
        ).execute("score.json", None, tempo_factor=1.0, section_name="A B")
        self.assertNotEqual(first["artifact"], second["artifact"])


if __name__ == "__main__":
    unittest.main()
