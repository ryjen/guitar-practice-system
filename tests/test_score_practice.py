from __future__ import annotations

import unittest

from guitar_practice.domain import score
from guitar_practice.domain.score_practice import (
    ScoreTransformError,
    resolve_section,
    scale_tempo,
    select_backing_parts,
    select_drum_parts,
    slice_bars,
    slice_section,
)


def practice_score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "practice-score",
        "metadata": {"title": "Practice Score"},
        "bars": [
            {"number": 1},
            {"number": 2},
            {"number": 3},
            {"number": 4},
        ],
        "meter_map": [
            {"bar": 1, "beats": 4, "beat_unit": 4},
            {"bar": 3, "beats": 3, "beat_unit": 4},
        ],
        "tempo_map": [
            {"location": {"bar": 1, "beat": [1, 1]}, "bpm": 120, "beat_unit": [1, 4]},
            {"location": {"bar": 2, "beat": [3, 1]}, "bpm": 100, "beat_unit": [1, 4]},
            {"location": {"bar": 3, "beat": [1, 1]}, "bpm": 90, "beat_unit": [1, 4]},
        ],
        "key_map": [
            {"bar": 1, "fifths": 0, "mode": "major"},
            {"bar": 4, "fifths": 1, "mode": "major"},
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
            {"location": {"bar": 2, "beat": [1, 1]}, "symbol": "C7"},
            {"location": {"bar": 3, "beat": [1, 1]}, "symbol": "F7"},
        ],
        "parts": [
            {
                "id": "guitar",
                "name": "Guitar",
                "role": "guitar",
                "instrument": {"name": "Electric Guitar", "family": "guitar"},
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 2, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "C", "alter": 0, "octave": 4},
                    }
                ],
                "provenance": {"kind": "imported", "source": "track-role:instrument"},
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
                "events": [],
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
                "events": [],
            },
        ],
    }
    score.validate(document)
    return document


class ScorePracticeTransformTests(unittest.TestCase):
    def test_scale_tempo_is_pure_and_preserves_shape(self) -> None:
        document = practice_score()

        realized = scale_tempo(document, 0.75)

        self.assertEqual([90.0, 75.0, 67.5], [item["bpm"] for item in realized["tempo_map"]])
        self.assertEqual([120, 100, 90], [item["bpm"] for item in document["tempo_map"]])
        self.assertTrue(
            all(item["provenance"]["kind"] == "generated" for item in realized["tempo_map"])
        )
        score.validate(realized)

    def test_slice_bars_reestablishes_effective_maps_at_new_bar_one(self) -> None:
        sliced = slice_bars(practice_score(), 2, 3)

        self.assertEqual([1, 2], [bar["number"] for bar in sliced["bars"]])
        self.assertEqual(
            [(1, 4, 4), (2, 3, 4)],
            [
                (item["bar"], item["beats"], item["beat_unit"])
                for item in sliced["meter_map"]
            ],
        )
        self.assertEqual(
            [
                ({"bar": 1, "beat": [1, 1]}, 120),
                ({"bar": 1, "beat": [3, 1]}, 100),
                ({"bar": 2, "beat": [1, 1]}, 90),
            ],
            [(item["location"], item["bpm"]) for item in sliced["tempo_map"]],
        )
        self.assertEqual([{"bar": 1, "fifths": 0, "mode": "major"}], sliced["key_map"])
        self.assertEqual(
            {"bar": 1, "beat": [1, 1]},
            sliced["parts"][0]["events"][0]["location"],
        )
        self.assertEqual(
            [
                ("intro", 1, 1),
                ("chorus", 2, 2),
            ],
            [
                (section["id"], section["start_bar"], section["end_bar"])
                for section in sliced["sections"]
            ],
        )
        self.assertEqual(
            [{"location": {"bar": 2, "beat": [1, 1]}, "label": "Chorus"}],
            sliced["rehearsal_marks"],
        )
        score.validate(sliced)

    def test_section_resolution_and_slice_are_case_insensitive_and_unique(self) -> None:
        document = practice_score()

        section = resolve_section(document, " chorus ")
        sliced = slice_section(document, "CHORUS")

        self.assertEqual("chorus", section["id"])
        self.assertEqual([1, 2], [bar["number"] for bar in sliced["bars"]])
        self.assertEqual("chorus", sliced["sections"][0]["id"])
        self.assertEqual((1, 2), (
            sliced["sections"][0]["start_bar"],
            sliced["sections"][0]["end_bar"],
        ))

    def test_backing_selection_excludes_only_strong_guitar_by_default(self) -> None:
        document = practice_score()

        selected = select_backing_parts(document)
        self.assertEqual(
            ["maybe-guitar", "bass", "drums"],
            [part["id"] for part in selected],
        )

        selected = select_backing_parts(document, include_part_ids=("guitar",))
        self.assertEqual(
            ["guitar", "maybe-guitar", "bass", "drums"],
            [part["id"] for part in selected],
        )

    def test_drum_selection_and_explicit_overrides_are_bounded(self) -> None:
        document = practice_score()

        self.assertEqual(
            ["drums"],
            [part["id"] for part in select_drum_parts(document)],
        )
        self.assertEqual(
            ["bass", "drums"],
            [
                part["id"]
                for part in select_drum_parts(document, include_part_ids=("bass",))
            ],
        )
        with self.assertRaisesRegex(ScoreTransformError, "unknown part"):
            select_drum_parts(document, include_part_ids=("missing",))
        with self.assertRaisesRegex(ScoreTransformError, "both included and excluded"):
            select_drum_parts(
                document,
                include_part_ids=("drums",),
                exclude_part_ids=("drums",),
            )

    def test_slice_fails_closed_on_canonical_repeat_notation(self) -> None:
        document = practice_score()
        document["bars"][1]["repeat_start"] = True
        score.validate(document)

        with self.assertRaisesRegex(ScoreTransformError, "expand playback form"):
            slice_bars(document, 2, 3)


if __name__ == "__main__":
    unittest.main()
