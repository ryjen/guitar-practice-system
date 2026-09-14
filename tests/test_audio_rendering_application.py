from __future__ import annotations

import unittest
from typing import Any, Mapping

from guitar_practice.application.audio import RenderAudioArtifact
from guitar_practice.application.ports import AudioRenderProfile, RenderedAudio


class MemoryDocuments:
    def __init__(self) -> None:
        self.writes: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.writes[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.writes[path] = document


class MemoryArtifacts:
    def __init__(self, values: Mapping[str, bytes]) -> None:
        self.values = dict(values)
        self.writes: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.values[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.writes[path] = data


class FakeRenderer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list[tuple[bytes, AudioRenderProfile]] = []

    def render(self, midi: bytes, profile: AudioRenderProfile) -> RenderedAudio:
        self.seen.append((midi, profile))
        if self.fail:
            raise RuntimeError("render failed")
        return RenderedAudio(
            wav=b"RIFF-rendered-wave",
            renderer="fake-synth",
            renderer_version="1.2.3",
            soundfont="fixture.sf2",
        )


class AudioRenderingApplicationTests(unittest.TestCase):
    def test_writes_wav_and_provenance_after_successful_render(self) -> None:
        artifacts = MemoryArtifacts({"renders/backing.mid": b"MThd-midi"})
        documents = MemoryDocuments()
        renderer = FakeRenderer()
        profile = AudioRenderProfile(sample_rate=44_100, channels=2, sample_format="s16")

        metadata = RenderAudioArtifact(
            artifacts=artifacts,
            documents=documents,
            renderer=renderer,
        ).execute("renders/backing.mid", "renders/backing.wav", profile=profile)

        self.assertEqual([(b"MThd-midi", profile)], renderer.seen)
        self.assertEqual(b"RIFF-rendered-wave", artifacts.writes["renders/backing.wav"])
        self.assertEqual("fake-synth", metadata["renderer"])
        self.assertEqual("1.2.3", metadata["renderer_version"])
        self.assertEqual("fixture.sf2", metadata["soundfont"])
        self.assertEqual(44_100, metadata["profile"]["sample_rate"])
        self.assertEqual(2, metadata["profile"]["channels"])
        self.assertEqual("s16", metadata["profile"]["sample_format"])
        self.assertEqual(
            metadata,
            documents.writes["renders/backing.wav.json"],
        )

    def test_renderer_failure_preserves_source_and_writes_no_outputs(self) -> None:
        artifacts = MemoryArtifacts({"renders/drums.mid": b"MThd-original"})
        documents = MemoryDocuments()
        renderer = FakeRenderer(fail=True)

        with self.assertRaises(RuntimeError):
            RenderAudioArtifact(
                artifacts=artifacts,
                documents=documents,
                renderer=renderer,
            ).execute(
                "renders/drums.mid",
                "renders/drums.wav",
                profile=AudioRenderProfile(),
            )

        self.assertEqual(b"MThd-original", artifacts.values["renders/drums.mid"])
        self.assertEqual({}, artifacts.writes)
        self.assertEqual({}, documents.writes)


if __name__ == "__main__":
    unittest.main()
