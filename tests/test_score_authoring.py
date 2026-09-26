from __future__ import annotations

import copy
import unittest

from guitar_practice.domain import score, score_authoring
from tests.test_score_ir import minimal_score, timeline_score


class ScoreAuthoringDomainTests(unittest.TestCase):
    def test_replace_form_builds_contiguous_sections_without_mutating_source(self) -> None:
        source = minimal_score()
        original = copy.deepcopy(source)

        result = score_authoring.replace_form(
            source,
            [
                score_authoring.FormSection("intro", "Intro", 2),
                score_authoring.FormSection("verse", "Verse", 4),
                score_authoring.FormSection("verse-2", "Verse 2", 4),
                score_authoring.FormSection("outro", "Outro", 1),
            ],
        )

        self.assertEqual(original, source)
        self.assertEqual(11, len(result["bars"]))
        self.assertEqual(
            [
                {"id": "intro", "label": "Intro", "start_bar": 1, "end_bar": 2},
                {"id": "verse", "label": "Verse", "start_bar": 3, "end_bar": 6},
                {"id": "verse-2", "label": "Verse 2", "start_bar": 7, "end_bar": 10},
                {"id": "outro", "label": "Outro", "start_bar": 11, "end_bar": 11},
            ],
            result["sections"],
        )
        score.validate(result)

    def test_replace_form_rejects_draft_with_positioned_musical_content(self) -> None:
        source = timeline_score()

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "empty draft"):
            score_authoring.replace_form(
                source,
                [score_authoring.FormSection("verse", "Verse", 4)],
            )

    def test_replace_harmony_targets_range_and_uses_active_meter(self) -> None:
        source = minimal_score()
        source = score_authoring.replace_form(
            source,
            [
                score_authoring.FormSection("intro", "Intro", 1),
                score_authoring.FormSection("verse", "Verse", 2),
            ],
        )
        source["meter_map"].append({"bar": 3, "beats": 6, "beat_unit": 8})
        score.validate(source)
        original = copy.deepcopy(source)

        result = score_authoring.replace_harmony(
            source,
            start_bar=2,
            end_bar=3,
            bars=[("Cmaj7",), ("Dm7", "G7")],
        )

        self.assertEqual(original, source)
        self.assertEqual(
            [
                {
                    "location": {"bar": 2, "beat": [1, 1]},
                    "symbol": "Cmaj7",
                    "provenance": {"kind": "user", "source": "score-authoring:chords"},
                },
                {
                    "location": {"bar": 3, "beat": [1, 1]},
                    "symbol": "Dm7",
                    "provenance": {"kind": "user", "source": "score-authoring:chords"},
                },
                {
                    "location": {"bar": 3, "beat": [4, 1]},
                    "symbol": "G7",
                    "provenance": {"kind": "user", "source": "score-authoring:chords"},
                },
            ],
            result["harmony"],
        )
        score.validate(result)

    def test_replace_harmony_requires_exact_bar_count(self) -> None:
        source = minimal_score()
        source = score_authoring.replace_form(
            source,
            [score_authoring.FormSection("verse", "Verse", 2)],
        )

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "2 bar cells"):
            score_authoring.replace_harmony(
                source,
                start_bar=1,
                end_bar=2,
                bars=[("C",)],
            )


if __name__ == "__main__":
    unittest.main()
