from __future__ import annotations

import copy
import unittest

from guitar_practice.domain import score
from guitar_practice.domain.score_realization import (
    ScoreRealizationError,
    resolve_section,
    scale_tempo,
    select_backing_parts,
    select_drum_parts,
    slice_bars,
    slice_section,
)


def realization_score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "practice-song",
        "metadata": {"title": "Practice Song"},
        "bars": [
            {"number": 1},
            {"number": 2, "repeat_start": True},
            {"number": 3},
            {"number": 4, "repeat_end": 2},
        ],
        "meter_map": [
            {"bar": 1, "beats": 4, "beat_unit": 4},
            {"bar": 3, "beats": 3, "beat_unit": 4},
        ],
        "tempo_map": [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 120,
                "beat_unit": [1, 4],
            },
            {
                "location": {"bar": 2, "beat": [3, 1]},
                "bpm": 90,
                "beat_unit": [1, 4],
            },
        ],
        "key_map": [
            {"bar": 1, "fifths": 0, "mode": "major"},
            {"bar": 3, "fifths": 1, "mode": "major"},
        ],
        "sections": [
            {"id": "intro", "label": "Intro", "start_bar": 1, "end_bar": 2},
            {"id": "chorus", "label": "Chorus", "start_bar": 3, "end_bar": 4},
        ],
        "rehearsal_marks": [
            {"location": {"bar": 1, "beat": [1, 1]}, "label": "Intro"},
            {"location": {"bar": 3, "beat": [1, 1]}, "label": "Chorus"},
        ],
        "harmony": [
            {"location": {"bar": 2, "beat": [1, 1]}, "symbol": "C"},
            {"location": {"bar": 3, "beat": [1, 1]}, "symbol": "G"},
        ],
        "parts": [
            {
                "id": "lead-guitar",
                "name": "Lead Guitar",
                "role": "guitar",
                "instrument": {"name": "Electric Guitar", "family": "guitar"},
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    },
                    {
                        "kind": "note",
                        "location": {"bar": 3, "beat": [2, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "G", "alter": 0, "octave": 4},
                    },
                ],
                "provenance": {
                    "kind": "imported",
                    "source": "track-role:instrument",
                },
            },
            {
                "id": "maybe-guitar",
                "name": "Mystery",
                "role": "guitar",
                "instrument": {"name": "Unknown", "family": "other"},
                "events": [],
                "provenance": {
                    "kind": "inferred",
                    "source": "track-role:name-heuristic",
                    "confidence": 0.5,
                },
            },
            {
                "id": "bass",
                "name": "Bass",
                "role": "bass",
                "instrument": {"name": "Electric Bass", "family": "bass"},
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 2, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "C", "alter": 0, "octave": 3},
                    }
                ],
            },
            {
                "id": "drums",
                "name": "Drums",
                "role": "drums",
                "instrument": {
                    "name": "Drum Kit",
                    "family": "drums",
                    "midi": {"channel": 10, "percussion": True},
                },
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 4, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "C", "alter": 0, "octave": 5},
                    }
                ],
            },
        ],
    }
    score.validate(document)
    return document


class ScoreRealizationTests(unittest.TestCase):
    def test_tempo_scaling_is_immutable_and_proportional(self) -> None:
        original = realization_score()
        snapshot = copy.deepcopy(original)

        realized = scale_tempo(original, 0.5)

        self.assertEqual([60.0, 45.0], [point["bpm"] for point in realized["tempo_map"]])
        self.assertEqual(snapshot, original)
        self.assertNotEqual(original["id"], realized["id"])
        self.assertEqual("generated", realized["provenance"]["kind"])
        score.validate(realized)

    def test_tempo_scaling_rejects_invalid_factor(self) -> None:
        for factor in (0, -1, float("inf"), True):
            with self.subTest(factor=factor):
                with self.assertRaises(ScoreRealizationError):
                    scale_tempo(realization_score(), factor)

    def test_backing_selection_is_conservative_and_overrideable(self) -> None:
        original = realization_score()

        realized = select_backing_parts(original)

        self.assertEqual(
            ["maybe-guitar", "bass", "drums"],
            [part["id"] for part in realized["parts"]],
        )
        included = select_backing_parts(
            original,
            include_part_ids=("lead-guitar",),
            exclude_part_ids=("bass",),
        )
        self.assertEqual(
            ["lead-guitar", "maybe-guitar", "drums"],
            [part["id"] for part in included["parts"]],
        )
        self.assertEqual(4, len(original["parts"]))

    def test_drum_selection_and_id_validation(self) -> None:
        document = realization_score()

        drums = select_drum_parts(document)
        self.assertEqual(["drums"], [part["id"] for part in drums["parts"]])

        with_guitar = select_drum_parts(
            document,
            include_part_ids=("maybe-guitar",),
        )
        self.assertEqual(
            ["maybe-guitar", "drums"],
            [part["id"] for part in with_guitar["parts"]],
        )

        with self.assertRaisesRegex(ScoreRealizationError, "unknown part"):
            select_drum_parts(document, include_part_ids=("missing",))
        with self.assertRaisesRegex(ScoreRealizationError, "both included and excluded"):
            select_drum_parts(
                document,
                include_part_ids=("drums",),
                exclude_part_ids=("drums",),
            )

    def test_bar_slice_rebases_structural_state_and_events(self) -> None:
        original = realization_score()
        snapshot = copy.deepcopy(original)

        realized = slice_bars(original, 2, 3)

        self.assertEqual([1, 2], [bar["number"] for bar in realized["bars"]])
        self.assertNotIn("repeat_start", realized["bars"][0])
        self.assertEqual(
            [(1, 4, 4), (2, 3, 4)],
            [
                (item["bar"], item["beats"], item["beat_unit"])
                for item in realized["meter_map"]
            ],
        )
        self.assertEqual(
            [
                ({"bar": 1, "beat": [1, 1]}, 120),
                ({"bar": 1, "beat": [3, 1]}, 90),
            ],
            [(item["location"], item["bpm"]) for item in realized["tempo_map"]],
        )
        self.assertEqual(
            [(1, 0), (2, 1)],
            [(item["bar"], item["fifths"]) for item in realized["key_map"]],
        )
        self.assertEqual(
            [("intro", 1, 1), ("chorus", 2, 2)],
            [
                (section["id"], section["start_bar"], section["end_bar"])
                for section in realized["sections"]
            ],
        )
        self.assertEqual(
            [{"bar": 2, "beat": [1, 1]}],
            [item["location"] for item in realized["rehearsal_marks"]],
        )
        self.assertEqual(
            [
                {"bar": 1, "beat": [1, 1]},
                {"bar": 2, "beat": [1, 1]},
            ],
            [item["location"] for item in realized["harmony"]],
        )
        self.assertEqual(
            [{"bar": 2, "beat": [2, 1]}],
            [
                event["location"]
                for event in realized["parts"][0]["events"]
            ],
        )
        self.assertEqual(
            [{"bar": 1, "beat": [1, 1]}],
            [
                event["location"]
                for event in realized["parts"][2]["events"]
            ],
        )
        self.assertEqual([], realized["parts"][3]["events"])
        self.assertEqual(snapshot, original)
        score.validate(realized)

    def test_section_resolution_and_slice_fail_closed_on_ambiguity(self) -> None:
        document = realization_score()

        section = resolve_section(document, "chorus")
        self.assertEqual((3, 4), (section["start_bar"], section["end_bar"]))

        realized = slice_section(document, "CHORUS")
        self.assertEqual(2, len(realized["bars"]))
        self.assertEqual(3, realized["meter_map"][0]["beats"])
        self.assertEqual(90, realized["tempo_map"][0]["bpm"])

        ambiguous = realization_score()
        ambiguous["sections"].append(
            {
                "id": "chorus-two",
                "label": "Chorus",
                "start_bar": 4,
                "end_bar": 4,
            }
        )
        score.validate(ambiguous)
        with self.assertRaisesRegex(ScoreRealizationError, "ambiguous section"):
            resolve_section(ambiguous, "chorus")


if __name__ == "__main__":
    unittest.main()
