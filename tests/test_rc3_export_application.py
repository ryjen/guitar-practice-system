from __future__ import annotations

import unittest
import wave
from io import BytesIO
from typing import Any, Mapping

from guitar_practice.application.ports import AudioRenderProfile, RenderedAudio
from guitar_practice.application.rc3_export import ExportBossRc3Drums
from guitar_practice.domain import midi
from guitar_practice.domain.song import (
    ClassificationSource,
    NoteEvent,
    Song,
    SongTrack,
    TempoPoint,
    TrackClassification,
    TrackRole,
    song_to_dict,
)


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
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list[tuple[bytes, AudioRenderProfile]] = []

    def render(self, data: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        self.seen.append((data, profile))
        if self.fail:
            raise RuntimeError("synth failed")
        return RenderedAudio(_wav(300_000), "fake", "1", "fixture.sf2")


def _song_document() -> Mapping[str, Any]:
    song = Song(
        source_id="fixture",
        title="Fixture",
        duration_quarters=4.0,
        bar_boundaries=(0.0, 2.0, 4.0),
        tempo_map=(TempoPoint(position=0.0, bpm=120.0),),
        tracks=(
            SongTrack(
                id="guitar",
                name="Guitar",
                classification=TrackClassification(TrackRole.GUITAR, ClassificationSource.MIDI),
                notes=(NoteEvent(position=0.0, duration=4.0, midi_note=64),),
            ),
            SongTrack(
                id="drums",
                name="Drums",
                classification=TrackClassification(TrackRole.DRUMS, ClassificationSource.PERCUSSION),
                midi_channel=10,
                is_percussion=True,
                notes=(
                    NoteEvent(position=0.0, duration=1.0, midi_note=36),
                    NoteEvent(position=2.0, duration=1.0, midi_note=38),
                ),
            ),
        ),
    )
    return {"schema_version": 1, "song": song_to_dict(song), "import": {"source": "fixture.gp5"}}


class Rc3ExportApplicationTests(unittest.TestCase):
    def test_exports_full_song_drums_with_exact_score_duration(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": _song_document()})
        artifacts = MemoryArtifacts()
        renderer = FakeRenderer()
        metadata = ExportBossRc3Drums(documents, artifacts, renderer).execute(
            "songs/fixture.json",
            "renders/fixture-drums.wav",
            tempo_factor=0.5,
        )

        self.assertIn("renders/fixture-drums.mid", artifacts.writes)
        report = midi.inspect(artifacts.writes["renders/fixture-drums.mid"])
        self.assertEqual(["Conductor", "Drums"], report["track_names"])
        with wave.open(BytesIO(artifacts.writes["renders/fixture-drums.wav"]), "rb") as audio:
            self.assertEqual(176_400, audio.getnframes())
        self.assertEqual("boss-rc3", metadata["target"])
        self.assertEqual(4.0, metadata["duration_seconds"])
        self.assertEqual(["drums"], metadata["selected_track_ids"])
        self.assertEqual("renders/fixture-drums.mid", metadata["source_midi"])
        self.assertEqual(metadata, documents.writes["renders/fixture-drums.wav.json"])

    def test_default_output_path_is_deterministic_and_safe(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": _song_document()})
        artifacts = MemoryArtifacts()
        metadata = ExportBossRc3Drums(documents, artifacts, FakeRenderer()).execute(
            "songs/fixture.json",
            None,
            tempo_factor=0.75,
        )
        self.assertEqual(
            "generated/rc3/fixture-drums-75pct.wav",
            metadata["artifact"],
        )

    def test_exports_selected_bar_range_and_records_provenance(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": _song_document()})
        artifacts = MemoryArtifacts()
        metadata = ExportBossRc3Drums(documents, artifacts, FakeRenderer()).execute(
            "songs/fixture.json",
            None,
            tempo_factor=1.0,
            bar_range=(2, 2),
        )

        self.assertEqual("generated/rc3/fixture-drums-100pct-bars2-2.wav", metadata["artifact"])
        self.assertEqual([2, 2], metadata["bar_range"])
        self.assertEqual(1.0, metadata["duration_seconds"])
        with wave.open(BytesIO(artifacts.writes[metadata["artifact"]]), "rb") as audio:
            self.assertEqual(44_100, audio.getnframes())

    def test_rejects_non_wav_output_before_rendering(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": _song_document()})
        artifacts = MemoryArtifacts()
        renderer = FakeRenderer()
        with self.assertRaisesRegex(ValueError, "\\.wav"):
            ExportBossRc3Drums(documents, artifacts, renderer).execute(
                "songs/fixture.json",
                "renders/fixture-drums.mp3",
                tempo_factor=1.0,
            )
        self.assertEqual([], renderer.seen)
        self.assertEqual({}, artifacts.writes)

    def test_renderer_failure_preserves_generated_drum_midi(self) -> None:
        documents = MemoryDocuments({"songs/fixture.json": _song_document()})
        artifacts = MemoryArtifacts()
        with self.assertRaisesRegex(RuntimeError, "synth failed"):
            ExportBossRc3Drums(documents, artifacts, FakeRenderer(fail=True)).execute(
                "songs/fixture.json",
                "renders/fixture-drums.wav",
                tempo_factor=1.0,
            )

        self.assertIn("renders/fixture-drums.mid", artifacts.writes)
        self.assertNotIn("renders/fixture-drums.wav", artifacts.writes)
        self.assertEqual({}, documents.writes)


if __name__ == "__main__":
    unittest.main()
