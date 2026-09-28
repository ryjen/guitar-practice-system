from __future__ import annotations

import unittest
from typing import Any, Mapping
from unittest import mock

from guitar_practice.application.score_backing import RenderScoreBacking
from guitar_practice.domain import score


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

    def write_bytes(self, path: str, data: bytes) -> None:
        self.writes[path] = data


def _repeated_score() -> dict[str, Any]:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "repeat-score",
        "metadata": {"title": "Repeat Score"},
        "bars": [
            {"number": 1, "repeat_start": True},
            {"number": 2, "repeat_end": 2},
        ],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 120,
                "beat_unit": [1, 4],
            }
        ],
        "parts": [
            {
                "id": "bass",
                "name": "Bass",
                "role": "bass",
                "instrument": {"name": "Bass", "family": "bass"},
                "events": [],
            }
        ],
    }
    score.validate(document)
    return document


class ScoreBackingApplicationTests(unittest.TestCase):
    def test_full_song_expands_repeat_form_before_midi_rendering(self) -> None:
        documents = MemoryDocuments({"score.json": _repeated_score()})
        artifacts = MemoryArtifacts()
        captured: list[Mapping[str, Any]] = []

        def render(document: Mapping[str, Any]) -> bytes:
            captured.append(document)
            return b"midi"

        with mock.patch(
            "guitar_practice.application.score_backing.render_score_midi",
            side_effect=render,
        ):
            RenderScoreBacking(documents, artifacts).execute(
                "score.json",
                "generated/backing.mid",
                tempo_factor=1.0,
            )

        self.assertEqual(1, len(captured))
        realized = captured[0]
        self.assertEqual([1, 2, 3, 4], [bar["number"] for bar in realized["bars"]])
        self.assertTrue(
            all(
                not (set(bar) & {"repeat_start", "repeat_end", "ending_numbers"})
                for bar in realized["bars"]
            )
        )
        score.validate(dict(realized))


if __name__ == "__main__":
    unittest.main()
