from __future__ import annotations

import copy
import hashlib
import unittest
from typing import Any, Mapping

from guitar_practice.application.ports import PlaybackResult
from guitar_practice.application.score_playback import PlayScoreMidi, RenderScoreMidi
from guitar_practice.domain import midi, score
from tests.test_score_realization import realization_score


class MemoryDocuments:
    def __init__(self, values: Mapping[str, Mapping[str, Any]]) -> None:
        self.values = {key: copy.deepcopy(dict(value)) for key, value in values.items()}
        self.writes: dict[str, Mapping[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return copy.deepcopy(self.values[path])

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.writes[path] = copy.deepcopy(dict(document))


class MemoryArtifacts:
    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.writes[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.writes[path] = bytes(data)


class FakePlayer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list[bytes] = []

    def play(self, data: bytes) -> PlaybackResult:
        self.seen.append(data)
        if self.fail:
            raise RuntimeError("audio device unavailable")
        return PlaybackResult("fake-player", "1.0", "fixture.sf2")


class ScorePlaybackApplicationTests(unittest.TestCase):
    def test_render_whole_score_writes_midi_and_content_addressed_provenance(self) -> None:
        source = realization_score()
        documents = MemoryDocuments({"source.score.json": source})
        artifacts = MemoryArtifacts()

        metadata = RenderScoreMidi(documents, artifacts).execute(
            "source.score.json",
            "generated/source.mid",
            tempo_factor=1.0,
        )

        self.assertEqual(source, documents.values["source.score.json"])
        report = midi.inspect(artifacts.writes["generated/source.mid"])
        self.assertEqual("MThd", artifacts.writes["generated/source.mid"][:4].decode())
        self.assertGreaterEqual(report["tracks"], 1)
        self.assertEqual("score-midi-v1", metadata["render_path"])
        self.assertEqual(score.SCHEMA_VERSION, metadata["source_score_schema_version"])
        self.assertEqual(
            hashlib.sha256(score.dumps(source).encode("utf-8")).hexdigest(),
            metadata["source_score_sha256"],
        )
        self.assertEqual("practice-song", metadata["source_score_id"])
        self.assertEqual("practice-song", metadata["realization_id"])
        self.assertEqual(1.0, metadata["tempo_factor"])
        self.assertIsNone(metadata["bar_range"])
        self.assertIsNone(metadata["section"])
        self.assertEqual(
            metadata,
            documents.writes["generated/source.mid.json"],
        )

    def test_render_section_and_scaled_tempo_are_explicit_derived_realization(self) -> None:
        source = realization_score()
        documents = MemoryDocuments({"source.score.json": source})
        artifacts = MemoryArtifacts()

        metadata = RenderScoreMidi(documents, artifacts).execute(
            "source.score.json",
            "generated/verse.mid",
            tempo_factor=0.75,
            section_name="Chorus",
        )

        self.assertEqual([3, 4], metadata["bar_range"])
        self.assertEqual("Chorus", metadata["section"])
        self.assertEqual(0.75, metadata["tempo_factor"])
        self.assertNotEqual(metadata["source_score_id"], metadata["realization_id"])
        self.assertTrue(metadata["realization_id"].endswith("tempo-75"))
        report = midi.inspect(artifacts.writes["generated/verse.mid"])
        self.assertGreaterEqual(report["tracks"], 1)

    def test_render_rejects_simultaneous_bar_and_section_selection(self) -> None:
        service = RenderScoreMidi(
            MemoryDocuments({"source.score.json": realization_score()}),
            MemoryArtifacts(),
        )

        with self.assertRaisesRegex(ValueError, "either a bar range or a section"):
            service.execute(
                "source.score.json",
                "generated/source.mid",
                tempo_factor=1.0,
                bar_range=(1, 2),
                section_name="Chorus",
            )

    def test_player_failure_occurs_only_after_midi_and_metadata_are_persisted(self) -> None:
        documents = MemoryDocuments({"source.score.json": realization_score()})
        artifacts = MemoryArtifacts()
        renderer = RenderScoreMidi(documents, artifacts)
        player = FakePlayer(fail=True)
        service = PlayScoreMidi(renderer, artifacts, player)

        with self.assertRaisesRegex(RuntimeError, "audio device unavailable"):
            service.execute(
                "source.score.json",
                "generated/audition.mid",
                tempo_factor=1.0,
            )

        self.assertIn("generated/audition.mid", artifacts.writes)
        self.assertIn("generated/audition.mid.json", documents.writes)
        self.assertEqual(artifacts.writes["generated/audition.mid"], player.seen[0])

    def test_successful_playback_returns_artifact_metadata_and_player_provenance(self) -> None:
        documents = MemoryDocuments({"source.score.json": realization_score()})
        artifacts = MemoryArtifacts()
        player = FakePlayer()

        metadata, playback = PlayScoreMidi(
            RenderScoreMidi(documents, artifacts),
            artifacts,
            player,
        ).execute(
            "source.score.json",
            "generated/audition.mid",
            tempo_factor=1.0,
            bar_range=(1, 2),
        )

        self.assertEqual([1, 2], metadata["bar_range"])
        self.assertEqual("fake-player", playback.player)
        self.assertEqual("1.0", playback.player_version)
        self.assertEqual("fixture.sf2", playback.soundfont)


if __name__ == "__main__":
    unittest.main()
