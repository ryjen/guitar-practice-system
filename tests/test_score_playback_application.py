from __future__ import annotations

import copy
import unittest
from typing import Any, Mapping

from guitar_practice.application.ports import PlayedMidi
from guitar_practice.application.score_playback import PlayScoreMidi, RenderScoreMidi
from guitar_practice.domain import midi, score
from tests.test_score_ir import timeline_score


class MemoryDocuments:
    def __init__(self, values: dict[str, Mapping[str, Any]]) -> None:
        self.values = dict(values)

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = copy.deepcopy(dict(document))


class MemoryArtifacts:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.values[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.values[path] = data


class FakePlayer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list[bytes] = []

    def play(self, data: bytes) -> PlayedMidi:
        self.seen.append(data)
        if self.fail:
            raise RuntimeError("player failed")
        return PlayedMidi("fake-player", "1.0", "fixture.sf2")


def playback_score() -> dict[str, Any]:
    document = timeline_score()
    document["parts"][0]["events"][0].pop("tie")
    document["sections"] = [
        {"id": "intro", "label": "Intro", "start_bar": 1, "end_bar": 1},
        {"id": "verse", "label": "Verse", "start_bar": 2, "end_bar": 2},
    ]
    score.validate(document)
    return document


class ScorePlaybackApplicationTests(unittest.TestCase):
    def test_render_writes_deterministic_midi_and_provenance(self) -> None:
        source = playback_score()
        documents = MemoryDocuments({"score.json": source})
        artifacts = MemoryArtifacts()
        metadata = MemoryDocuments({})
        service = RenderScoreMidi(documents, artifacts, metadata)

        result = service.execute("score.json", "generated/score.mid")

        self.assertEqual(source, documents.values["score.json"])
        self.assertEqual("midi", result["format"])
        self.assertEqual("score-ir-midi-v1", result["render_path"])
        self.assertEqual(source["id"], result["source_score_id"])
        self.assertEqual(score.SCHEMA_VERSION, result["source_score_version"])
        report = midi.inspect(artifacts.values["generated/score.mid"])
        self.assertEqual(["Conductor", "Guitar"], report["track_names"])
        self.assertEqual(
            result,
            metadata.values["generated/score.mid.json"],
        )

    def test_section_render_records_exact_structural_selection(self) -> None:
        source = playback_score()
        documents = MemoryDocuments({"score.json": source})
        artifacts = MemoryArtifacts()
        metadata = MemoryDocuments({})

        result = RenderScoreMidi(documents, artifacts, metadata).execute(
            "score.json",
            "generated/verse.mid",
            section_name="verse",
        )

        self.assertEqual([2, 2], result["bar_range"])
        self.assertEqual("Verse", result["section"])
        self.assertNotEqual(source["id"], result["realization_id"])
        self.assertEqual(
            "generated",
            result["realization_provenance"]["kind"],
        )

    def test_play_writes_artifact_before_player_and_records_success(self) -> None:
        source = playback_score()
        documents = MemoryDocuments({"score.json": source})
        artifacts = MemoryArtifacts()
        metadata = MemoryDocuments({})
        renderer = RenderScoreMidi(documents, artifacts, metadata)
        player = FakePlayer()

        result = PlayScoreMidi(renderer, artifacts, metadata, player).execute(
            "score.json",
            section_name="Verse",
        )

        path = "generated/playback/blue-thing-section-Verse.mid"
        self.assertIn(path, artifacts.values)
        self.assertEqual([artifacts.values[path]], player.seen)
        self.assertEqual("fake-player", result["playback"]["player"])
        self.assertEqual(result, metadata.values[f"{path}.json"])

    def test_player_failure_preserves_midi_and_preplayback_sidecar(self) -> None:
        source = playback_score()
        documents = MemoryDocuments({"score.json": source})
        artifacts = MemoryArtifacts()
        metadata = MemoryDocuments({})
        renderer = RenderScoreMidi(documents, artifacts, metadata)

        with self.assertRaisesRegex(RuntimeError, "player failed"):
            PlayScoreMidi(
                renderer,
                artifacts,
                metadata,
                FakePlayer(fail=True),
            ).execute("score.json")

        path = "generated/playback/blue-thing.mid"
        self.assertIn(path, artifacts.values)
        self.assertIn(f"{path}.json", metadata.values)
        self.assertNotIn("playback", metadata.values[f"{path}.json"])


if __name__ == "__main__":
    unittest.main()
