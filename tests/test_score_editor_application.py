from __future__ import annotations

import copy
import unittest
from typing import Any, Mapping

from guitar_practice.application.ports import ExportedScore, PlayedMidi
from guitar_practice.application.score_editor import (
    EditProposal,
    ScoreEditConflictError,
    ScoreEditError,
    ScoreEditSession,
)
from guitar_practice.domain import score
from guitar_practice.domain.score_midi import render_score_midi
from tests.test_score_ir import minimal_score, timeline_score


class MemoryDocuments:
    def __init__(self, values: dict[str, dict[str, Any]]) -> None:
        self.values = copy.deepcopy(values)
        self.writes: list[str] = []

    def read(self, path: str) -> Mapping[str, Any]:
        return copy.deepcopy(self.values[path])

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = copy.deepcopy(dict(document))
        self.writes.append(path)


class MemoryArtifacts:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.values[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.values[path] = data


class FakeExporter:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    def export(self, document: Mapping[str, Any]) -> ExportedScore:
        self.documents.append(copy.deepcopy(dict(document)))
        return ExportedScore(data=b"<score-partwise/>\n")


class FakePlayer:
    def __init__(self) -> None:
        self.seen: list[bytes] = []

    def play(self, data: bytes) -> PlayedMidi:
        self.seen.append(data)
        return PlayedMidi("fake-player", "1", "fixture.sf2")


class ScoreEditSessionTests(unittest.TestCase):
    def test_form_and_harmony_remain_in_memory_until_explicit_save(self) -> None:
        source = minimal_score()
        store = MemoryDocuments({"score.json": source})
        session = ScoreEditSession("score.json", store)

        session.replace_form("intro:1 verse:1")
        session.replace_chords("Cmaj7 | G7")

        self.assertEqual(source, store.values["score.json"])
        self.assertEqual([], store.writes)
        working = session.snapshot()
        self.assertEqual(2, len(working["bars"]))
        self.assertEqual(["Cmaj7", "G7"], [item["symbol"] for item in working["harmony"]])
        self.assertTrue(session.validate()["valid"])

        saved = session.save()
        self.assertEqual(["score.json"], store.writes)
        self.assertEqual(saved, store.values["score.json"])
        score.validate(saved)

    def test_save_fails_closed_when_source_changes_outside_session(self) -> None:
        store = MemoryDocuments({"score.json": minimal_score()})
        session = ScoreEditSession("score.json", store)
        session.replace_form("verse:2")

        store.values["score.json"]["metadata"]["title"] = "Changed elsewhere"

        with self.assertRaisesRegex(ScoreEditConflictError, "changed during edit session"):
            session.save()
        self.assertEqual("Changed elsewhere", store.values["score.json"]["metadata"]["title"])
        self.assertEqual([], store.writes)

    def test_part_authoring_reuses_application_operation_in_memory(self) -> None:
        source = minimal_score()
        store = MemoryDocuments({"score.json": source})
        session = ScoreEditSession("score.json", store)

        result = session.add_part(
            {
                "part": {
                    "id": "guitar-1",
                    "name": "Guitar",
                    "role": "guitar",
                    "instrument": {
                        "name": "Electric Guitar",
                        "family": "guitar",
                    },
                    "guitar": {"tuning": "standard"},
                }
            }
        )

        self.assertEqual(source, store.values["score.json"])
        self.assertEqual([], store.writes)
        self.assertEqual("guitar-1", result["parts"][0]["id"])
        self.assertEqual(6, len(result["parts"][0]["guitar"]["tuning"]))
        score.validate(result)

    def test_structured_actions_delegate_to_existing_authoring_contracts(self) -> None:
        base = timeline_score()

        cases = [
            (
                "notes",
                {
                    "notes": [
                        {
                            "location": {"bar": 1, "beat": [1, 1]},
                            "duration": [1, 8],
                            "voice": 1,
                            "pitch": {"step": "E", "alter": 0, "octave": 4},
                        }
                    ]
                },
            ),
            (
                "voicing",
                {
                    "positions": [
                        {
                            "selector": {
                                "location": {"bar": 1, "beat": [1, 1]},
                                "voice": 1,
                                "pitch": {"step": "E", "alter": 0, "octave": 4},
                            },
                            "position": {"string": 2, "fret": 5},
                        }
                    ]
                },
            ),
            (
                "rhythm",
                {
                    "rhythm": [
                        {
                            "selector": {
                                "location": {"bar": 2, "beat": [1, 1]},
                                "voice": 2,
                                "pitch": {"step": "G", "alter": 0, "octave": 4},
                            },
                            "voice": 3,
                        }
                    ]
                },
            ),
            (
                "technique",
                {
                    "technique": [
                        {
                            "selector": {
                                "location": {"bar": 1, "beat": [1, 1]},
                                "voice": 1,
                                "pitch": {"step": "E", "alter": 0, "octave": 4},
                            },
                            "articulations": ["accent", "tenuto"],
                            "dynamics": "ff",
                        }
                    ]
                },
            ),
        ]

        for action, input_document in cases:
            with self.subTest(action=action):
                store = MemoryDocuments({"score.json": base})
                session = ScoreEditSession("score.json", store)
                result = session.apply_structured(
                    action,
                    part_id="guitar-1",
                    input_document=input_document,
                )
                self.assertEqual(base, store.values["score.json"])
                score.validate(result)


    def test_export_reads_unsaved_working_copy_through_export_application(self) -> None:
        source = minimal_score()
        store = MemoryDocuments({"score.json": source})
        session = ScoreEditSession("score.json", store)
        session.replace_form("intro:1 verse:1")
        session.replace_chords("Cmaj7 | G7")
        artifacts = MemoryArtifacts()
        exporter = FakeExporter()

        result = session.export_musicxml(
            artifacts=artifacts,
            exporter=exporter,
            output="generated/preview.musicxml",
        )

        self.assertEqual(b"<score-partwise/>\n", result.data)
        self.assertEqual(2, len(exporter.documents[0]["bars"]))
        self.assertEqual(["Cmaj7", "G7"], [
            item["symbol"] for item in exporter.documents[0]["harmony"]
        ])
        self.assertEqual(source, store.values["score.json"])
        self.assertEqual(
            b"<score-partwise/>\n",
            artifacts.values["generated/preview.musicxml"],
        )

    def test_play_reads_unsaved_working_copy_and_preserves_source(self) -> None:
        source = timeline_score()
        source["parts"][0]["events"][0].pop("tie")
        score.validate(source)
        store = MemoryDocuments({"score.json": source})
        session = ScoreEditSession("score.json", store)
        session.apply_structured(
            "notes",
            part_id="guitar-1",
            input_document={
                "notes": [
                    {
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 8],
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    }
                ]
            },
        )
        artifacts = MemoryArtifacts()
        metadata = MemoryDocuments({})
        player = FakePlayer()

        payload = session.play(
            artifacts=artifacts,
            metadata=metadata,
            player=player,
            output="generated/preview.mid",
        )

        self.assertEqual(source, store.values["score.json"])
        self.assertNotEqual(render_score_midi(source), player.seen[0])
        self.assertEqual(player.seen[0], artifacts.values["generated/preview.mid"])
        self.assertEqual("score.json", payload["score"])
        self.assertEqual("fake-player", payload["playback"]["player"])
        self.assertEqual(payload, metadata.values["generated/preview.mid.json"])

    def test_edit_proposal_is_transient_validated_metadata(self) -> None:
        proposal = EditProposal(
            action="chords",
            value="G7#9",
            confidence=0.71,
            alternatives=("G7", "G7b9"),
            source="chord-specialist",
        )

        self.assertEqual(
            {
                "action": "chords",
                "value": "G7#9",
                "confidence": 0.71,
                "alternatives": ["G7", "G7b9"],
                "source": "chord-specialist",
            },
            proposal.as_dict(),
        )
        with self.assertRaisesRegex(ScoreEditError, "confidence"):
            EditProposal(action="chords", value="G7", confidence=1.1)

if __name__ == "__main__":
    unittest.main()
