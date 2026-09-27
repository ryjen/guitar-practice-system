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

    def test_replace_part_notes_is_immutable_and_preserves_rests(self) -> None:
        source = timeline_score()
        original = copy.deepcopy(source)

        result = score_authoring.replace_part_notes(
            source,
            part_id="guitar-1",
            notes=[
                {
                    "location": {"bar": 1, "beat": [1, 1]},
                    "duration": [1, 8],
                    "voice": 1,
                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                },
                {
                    "location": {"bar": 2, "beat": [2, 1]},
                    "duration": [1, 8],
                    "voice": 1,
                    "pitch": {"step": "A", "alter": 0, "octave": 4},
                    "dynamics": "f",
                },
            ],
        )

        self.assertEqual(original, source)
        events = result["parts"][0]["events"]
        self.assertEqual(
            ["note", "rest", "note"],
            [event["kind"] for event in events],
        )
        self.assertEqual(
            {"bar": 1, "beat": [2, 1]},
            events[1]["location"],
        )
        self.assertEqual(
            {"kind": "user", "source": "score-authoring:notes"},
            events[0]["provenance"],
        )
        self.assertEqual("f", events[2]["dynamics"])
        score.validate(result)

    def test_replace_part_notes_rejects_unknown_part_and_non_note_kind(self) -> None:
        source = timeline_score()

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "unknown part"):
            score_authoring.replace_part_notes(
                source,
                part_id="missing",
                notes=[],
            )

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "kind must be note"):
            score_authoring.replace_part_notes(
                source,
                part_id="guitar-1",
                notes=[
                    {
                        "kind": "rest",
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                    }
                ],
            )

    def test_apply_note_positions_uses_exact_selector_and_validates_tuning(self) -> None:
        source = timeline_score()
        original = copy.deepcopy(source)
        selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }

        result = score_authoring.apply_note_positions(
            source,
            part_id="guitar-1",
            positions=[
                {
                    "selector": selector,
                    "position": {"string": 2, "fret": 5},
                }
            ],
        )

        self.assertEqual(original, source)
        self.assertEqual(
            {"string": 2, "fret": 5},
            result["parts"][0]["events"][0]["position"],
        )
        score.validate(result)

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "pitch"):
            score_authoring.apply_note_positions(
                source,
                part_id="guitar-1",
                positions=[
                    {
                        "selector": selector,
                        "position": {"string": 1, "fret": 1},
                    }
                ],
            )

    def test_apply_note_positions_fails_closed_on_missing_or_ambiguous_selector(self) -> None:
        source = timeline_score()
        selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }

        missing = copy.deepcopy(selector)
        missing["pitch"] = {"step": "F", "alter": 0, "octave": 4}
        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "matched no note"):
            score_authoring.apply_note_positions(
                source,
                part_id="guitar-1",
                positions=[
                    {
                        "selector": missing,
                        "position": {"string": 1, "fret": 1},
                    }
                ],
            )

        ambiguous = copy.deepcopy(source)
        ambiguous["parts"][0]["events"].append(
            copy.deepcopy(ambiguous["parts"][0]["events"][0])
        )
        score.validate(ambiguous)
        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "multiple notes"):
            score_authoring.apply_note_positions(
                ambiguous,
                part_id="guitar-1",
                positions=[
                    {
                        "selector": selector,
                        "position": {"string": 2, "fret": 5},
                    }
                ],
            )

    def test_apply_note_rhythm_uses_pre_edit_selector_and_resorts_events(self) -> None:
        source = timeline_score()
        source["parts"][0]["events"][2].pop("tuplet")
        score.validate(source)
        original = copy.deepcopy(source)
        selector = {
            "location": {"bar": 2, "beat": [1, 1]},
            "voice": 2,
            "pitch": {"step": "G", "alter": 0, "octave": 4},
        }

        result = score_authoring.apply_note_rhythm(
            source,
            part_id="guitar-1",
            patches=[
                {
                    "selector": selector,
                    "location": {"bar": 1, "beat": [3, 1]},
                    "duration": [1, 8],
                    "voice": 1,
                }
            ],
        )

        self.assertEqual(original, source)
        moved = [
            event
            for event in result["parts"][0]["events"]
            if event.get("pitch") == {"step": "G", "alter": 0, "octave": 4}
        ][0]
        self.assertEqual({"bar": 1, "beat": [3, 1]}, moved["location"])
        self.assertEqual([1, 8], moved["duration"])
        self.assertEqual(1, moved["voice"])
        score.validate(result)

    def test_apply_note_rhythm_rejects_ties_and_duplicate_targets(self) -> None:
        source = timeline_score()
        tied_selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }
        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "tied note"):
            score_authoring.apply_note_rhythm(
                source,
                part_id="guitar-1",
                patches=[
                    {
                        "selector": tied_selector,
                        "duration": [1, 8],
                    }
                ],
            )

        untied_selector = {
            "location": {"bar": 2, "beat": [1, 1]},
            "voice": 2,
            "pitch": {"step": "G", "alter": 0, "octave": 4},
        }
        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "already selected"):
            score_authoring.apply_note_rhythm(
                source,
                part_id="guitar-1",
                patches=[
                    {"selector": untied_selector, "location": {"bar": 2, "beat": [2, 1]}},
                    {"selector": untied_selector, "voice": 3},
                ],
            )

    def test_apply_note_technique_patches_expression_fields_immutably(self) -> None:
        source = timeline_score()
        original = copy.deepcopy(source)
        selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }

        result = score_authoring.apply_note_technique(
            source,
            part_id="guitar-1",
            patches=[
                {
                    "selector": selector,
                    "articulations": ["staccato", "accent"],
                    "techniques": [
                        {"name": "bend", "amount": [1, 1]},
                        {"name": "vibrato"},
                    ],
                    "dynamics": "f",
                }
            ],
        )

        self.assertEqual(original, source)
        note = result["parts"][0]["events"][0]
        self.assertEqual(["staccato", "accent"], note["articulations"])
        self.assertEqual(
            [{"name": "bend", "amount": [1, 1]}, {"name": "vibrato"}],
            note["techniques"],
        )
        self.assertEqual("f", note["dynamics"])
        score.validate(result)

    def test_apply_note_technique_can_clear_expression_fields_explicitly(self) -> None:
        source = timeline_score()
        selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }

        result = score_authoring.apply_note_technique(
            source,
            part_id="guitar-1",
            patches=[
                {
                    "selector": selector,
                    "articulations": [],
                    "techniques": [],
                    "dynamics": None,
                }
            ],
        )

        note = result["parts"][0]["events"][0]
        self.assertNotIn("articulations", note)
        self.assertNotIn("techniques", note)
        self.assertNotIn("dynamics", note)
        score.validate(result)

    def test_apply_note_technique_fails_closed_on_duplicate_or_empty_patch(self) -> None:
        source = timeline_score()
        selector = {
            "location": {"bar": 1, "beat": [1, 1]},
            "voice": 1,
            "pitch": {"step": "E", "alter": 0, "octave": 4},
        }

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "must change"):
            score_authoring.apply_note_technique(
                source,
                part_id="guitar-1",
                patches=[{"selector": selector}],
            )

        with self.assertRaisesRegex(score_authoring.ScoreAuthoringError, "already selected"):
            score_authoring.apply_note_technique(
                source,
                part_id="guitar-1",
                patches=[
                    {"selector": selector, "dynamics": "p"},
                    {"selector": selector, "articulations": ["accent"]},
                ],
            )

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
