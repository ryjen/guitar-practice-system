from __future__ import annotations

import copy
import unittest
from typing import Any, Mapping

from guitar_practice.application.score_editor import (
    ScoreEditConflictError,
    ScoreEditSession,
)
from guitar_practice.domain import score
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


if __name__ == "__main__":
    unittest.main()
