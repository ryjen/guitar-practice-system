from __future__ import annotations

import unittest

from guitar_practice.domain import score


def minimal_score() -> dict:
    return {
        "schema": "guitar-practice.score",
        "version": 1,
        "id": "blue-thing",
        "metadata": {"title": "Blue Thing"},
        "bars": [{"number": 1}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [],
        "parts": [],
    }


class ScoreIrContractTests(unittest.TestCase):
    def test_minimal_score_validates(self) -> None:
        score.validate(minimal_score())

    def test_canonical_json_round_trip_is_deterministic(self) -> None:
        document = minimal_score()

        encoded = score.dumps(document)

        self.assertTrue(encoded.endswith("\n"))
        self.assertFalse(encoded.endswith("\n\n"))
        self.assertEqual(document, score.loads(encoded))
        self.assertEqual(encoded, score.dumps(score.loads(encoded)))
        self.assertTrue(encoded.startswith('{"bars":'))
        self.assertNotIn(": ", encoded)

    def test_unsupported_schema_and_version_are_rejected(self) -> None:
        invalid_schema = minimal_score()
        invalid_schema["schema"] = "example.score"
        with self.assertRaisesRegex(score.ScoreError, "schema must be"):
            score.validate(invalid_schema)

        invalid_version = minimal_score()
        invalid_version["version"] = 2
        with self.assertRaisesRegex(score.ScoreError, "version must be 1"):
            score.validate(invalid_version)

    def test_slug_identifiers_reject_surrounding_whitespace(self) -> None:
        document = minimal_score()
        document["id"] = " blue-thing "

        with self.assertRaisesRegex(score.ScoreError, "lowercase slug"):
            score.validate(document)

    def test_unknown_top_level_fields_are_rejected(self) -> None:
        document = minimal_score()
        document["musescore"] = {"style": "default"}

        with self.assertRaisesRegex(score.ScoreError, "unsupported fields"):
            score.validate(document)

    def test_present_optional_collections_cannot_be_null(self) -> None:
        for field in ("key_map", "sections", "rehearsal_marks", "harmony"):
            with self.subTest(field=field):
                document = minimal_score()
                document[field] = None
                with self.assertRaisesRegex(score.ScoreError, "must be"):
                    score.validate(document)

    def test_duplicate_json_object_keys_are_rejected(self) -> None:
        payload = (
            '{"schema":"guitar-practice.score","version":1,'
            '"id":"one","id":"two","metadata":{"title":"Duplicate"},'
            '"bars":[{"number":1}],'
            '"meter_map":[{"bar":1,"beats":4,"beat_unit":4}],'
            '"tempo_map":[],"parts":[]}'
        )

        with self.assertRaisesRegex(score.ScoreError, "duplicate JSON key: id"):
            score.loads(payload)

    def test_required_top_level_fields_are_enforced(self) -> None:
        for field in (
            "schema",
            "version",
            "id",
            "metadata",
            "bars",
            "meter_map",
            "tempo_map",
            "parts",
        ):
            with self.subTest(field=field):
                document = minimal_score()
                del document[field]
                with self.assertRaisesRegex(score.ScoreError, "missing required fields"):
                    score.validate(document)

    def test_bars_are_contiguous_and_meter_starts_at_bar_one(self) -> None:
        skipped_bar = minimal_score()
        skipped_bar["bars"] = [{"number": 1}, {"number": 3}]
        with self.assertRaisesRegex(score.ScoreError, "bars must be contiguous"):
            score.validate(skipped_bar)

        late_meter = minimal_score()
        late_meter["bars"] = [{"number": 1}, {"number": 2}]
        late_meter["meter_map"] = [{"bar": 2, "beats": 4, "beat_unit": 4}]
        with self.assertRaisesRegex(score.ScoreError, "meter_map must start at bar 1"):
            score.validate(late_meter)


def standard_tuning() -> list[dict]:
    return [
        {"string": 6, "pitch": {"step": "E", "alter": 0, "octave": 2}},
        {"string": 5, "pitch": {"step": "A", "alter": 0, "octave": 2}},
        {"string": 4, "pitch": {"step": "D", "alter": 0, "octave": 3}},
        {"string": 3, "pitch": {"step": "G", "alter": 0, "octave": 3}},
        {"string": 2, "pitch": {"step": "B", "alter": 0, "octave": 3}},
        {"string": 1, "pitch": {"step": "E", "alter": 0, "octave": 4}},
    ]


def timeline_score() -> dict:
    document = minimal_score()
    document["bars"] = [{"number": 1}, {"number": 2}]
    document["meter_map"] = [
        {"bar": 1, "beats": 4, "beat_unit": 4},
        {"bar": 2, "beats": 6, "beat_unit": 8},
    ]
    document["tempo_map"] = [
        {
            "location": {"bar": 1, "beat": [1, 1]},
            "bpm": 120,
            "beat_unit": [1, 4],
        },
        {
            "location": {"bar": 1, "beat": [3, 1]},
            "bpm": 96,
            "beat_unit": [1, 4],
        },
    ]
    document["key_map"] = [
        {"bar": 1, "fifths": 0, "mode": "major"},
        {"bar": 2, "fifths": 1, "mode": "major"},
    ]
    document["parts"] = [
        {
            "id": "guitar-1",
            "name": "Guitar",
            "role": "guitar",
            "instrument": {"name": "Electric Guitar", "family": "guitar"},
            "guitar": {"tuning": standard_tuning()},
            "events": [
                {
                    "kind": "note",
                    "location": {"bar": 1, "beat": [1, 1]},
                    "duration": [1, 4],
                    "voice": 1,
                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                    "position": {"string": 1, "fret": 0},
                    "articulations": ["accent"],
                    "techniques": [{"name": "vibrato"}],
                    "dynamics": "mf",
                    "tie": "start",
                },
                {
                    "kind": "rest",
                    "location": {"bar": 1, "beat": [2, 1]},
                    "duration": [1, 4],
                    "voice": 1,
                },
                {
                    "kind": "note",
                    "location": {"bar": 2, "beat": [1, 1]},
                    "duration": [1, 12],
                    "voice": 2,
                    "pitch": {"step": "G", "alter": 0, "octave": 4},
                    "position": {"string": 1, "fret": 3},
                    "tuplet": {
                        "id": "triplet-1",
                        "actual": 3,
                        "normal": 2,
                        "base": [1, 8],
                    },
                },
            ],
        }
    ]
    return document


class ScoreIrTimelineTests(unittest.TestCase):
    def test_multi_meter_multi_tempo_parts_and_events_validate(self) -> None:
        score.validate(timeline_score())

    def test_non_reduced_and_zero_denominator_rationals_are_rejected(self) -> None:
        non_reduced = timeline_score()
        non_reduced["tempo_map"][0]["location"]["beat"] = [2, 2]
        with self.assertRaisesRegex(score.ScoreError, "lowest terms"):
            score.validate(non_reduced)

        zero_denominator = timeline_score()
        zero_denominator["parts"][0]["events"][0]["duration"] = [1, 0]
        with self.assertRaisesRegex(score.ScoreError, "denominator must be positive"):
            score.validate(zero_denominator)

    def test_location_must_be_inside_active_bar(self) -> None:
        document = timeline_score()
        document["parts"][0]["events"][0]["location"]["beat"] = [5, 1]

        with self.assertRaisesRegex(score.ScoreError, "beat must be inside bar"):
            score.validate(document)

    def test_event_duration_must_not_cross_bar_boundary(self) -> None:
        document = timeline_score()
        event = document["parts"][0]["events"][0]
        event["location"]["beat"] = [4, 1]
        event["duration"] = [1, 2]

        with self.assertRaisesRegex(score.ScoreError, "crosses bar boundary"):
            score.validate(document)

    def test_malformed_note_enum_values_raise_score_error(self) -> None:
        malformed_step = timeline_score()
        malformed_step["parts"][0]["events"][0]["pitch"]["step"] = []
        with self.assertRaisesRegex(score.ScoreError, "pitch.step"):
            score.validate(malformed_step)

        malformed_tie = timeline_score()
        malformed_tie["parts"][0]["events"][0]["tie"] = []
        with self.assertRaisesRegex(score.ScoreError, "tie must"):
            score.validate(malformed_tie)

    def test_note_and_rest_fields_are_distinct(self) -> None:
        rest_with_pitch = timeline_score()
        rest_with_pitch["parts"][0]["events"][1]["pitch"] = {
            "step": "C",
            "alter": 0,
            "octave": 4,
        }
        with self.assertRaisesRegex(score.ScoreError, "rest has unsupported fields"):
            score.validate(rest_with_pitch)

        note_without_pitch = timeline_score()
        del note_without_pitch["parts"][0]["events"][0]["pitch"]
        with self.assertRaisesRegex(score.ScoreError, "note.pitch"):
            score.validate(note_without_pitch)

    def test_part_ids_must_be_unique(self) -> None:
        document = timeline_score()
        duplicate = dict(document["parts"][0])
        duplicate["events"] = []
        document["parts"].append(duplicate)

        with self.assertRaisesRegex(score.ScoreError, "duplicate part id"):
            score.validate(document)

    def test_guitar_position_requires_declared_string_and_matching_pitch(self) -> None:
        missing_string = timeline_score()
        missing_string["parts"][0]["events"][0]["position"]["string"] = 7
        with self.assertRaisesRegex(score.ScoreError, "not present in tuning"):
            score.validate(missing_string)

        mismatched_pitch = timeline_score()
        mismatched_pitch["parts"][0]["events"][0]["pitch"] = {
            "step": "F",
            "alter": 0,
            "octave": 4,
        }
        with self.assertRaisesRegex(score.ScoreError, "does not match guitar position"):
            score.validate(mismatched_pitch)

    def test_tuplet_duration_and_definition_must_be_consistent(self) -> None:
        wrong_duration = timeline_score()
        wrong_duration["parts"][0]["events"][2]["duration"] = [1, 8]
        with self.assertRaisesRegex(score.ScoreError, "tuplet duration"):
            score.validate(wrong_duration)

        inconsistent = timeline_score()
        second = {
            "kind": "note",
            "location": {"bar": 2, "beat": [2, 1]},
            "duration": [1, 8],
            "voice": 2,
            "pitch": {"step": "A", "alter": 0, "octave": 4},
            "position": {"string": 1, "fret": 5},
            "tuplet": {
                "id": "triplet-1",
                "actual": 2,
                "normal": 2,
                "base": [1, 8],
            },
        }
        inconsistent["parts"][0]["events"].append(second)
        with self.assertRaisesRegex(score.ScoreError, "inconsistent tuplet definition"):
            score.validate(inconsistent)


def structured_score() -> dict:
    document = timeline_score()
    document["metadata"]["source"] = {
        "kind": "user",
        "id": "manual-transcription",
    }
    document["bars"][0]["repeat_start"] = True
    document["bars"][0]["ending_numbers"] = [1]
    document["bars"][1]["repeat_end"] = 2
    document["bars"][1]["ending_numbers"] = [2]
    document["sections"] = [
        {
            "id": "verse",
            "label": "Verse",
            "start_bar": 1,
            "end_bar": 2,
        }
    ]
    document["rehearsal_marks"] = [
        {
            "location": {"bar": 1, "beat": [1, 1]},
            "label": "A",
        }
    ]
    document["harmony"] = [
        {
            "location": {"bar": 1, "beat": [1, 1]},
            "symbol": "G7#9",
            "provenance": {
                "kind": "inferred",
                "source": "chord-specialist",
                "confidence": 0.71,
                "alternatives": ["G7", "G7b9"],
            },
        },
        {
            "location": {"bar": 2, "beat": [1, 1]},
            "symbol": "Cmaj7",
            "provenance": {
                "kind": "imported",
                "source": "source-score",
            },
        },
    ]
    document["parts"][0]["provenance"] = {
        "kind": "imported",
        "source": "source-score",
    }
    document["provenance"] = {
        "kind": "user",
        "source": "score-builder",
    }
    return document


class ScoreIrStructureTests(unittest.TestCase):
    def test_form_harmony_repeats_and_provenance_validate(self) -> None:
        score.validate(structured_score())

    def test_section_ids_and_ranges_are_validated(self) -> None:
        duplicate = structured_score()
        duplicate["sections"].append(
            {"id": "verse", "label": "Verse 2", "start_bar": 2, "end_bar": 2}
        )
        with self.assertRaisesRegex(score.ScoreError, "duplicate section id"):
            score.validate(duplicate)

        invalid_range = structured_score()
        invalid_range["sections"][0]["start_bar"] = 2
        invalid_range["sections"][0]["end_bar"] = 1
        with self.assertRaisesRegex(score.ScoreError, "section range"):
            score.validate(invalid_range)

    def test_repeat_and_ending_invariants_are_validated(self) -> None:
        invalid_repeat = structured_score()
        invalid_repeat["bars"][1]["repeat_end"] = 1
        with self.assertRaisesRegex(score.ScoreError, "repeat_end must be at least 2"):
            score.validate(invalid_repeat)

        invalid_ending = structured_score()
        invalid_ending["bars"][0]["ending_numbers"] = [1, 1]
        with self.assertRaisesRegex(score.ScoreError, "ending_numbers must be unique"):
            score.validate(invalid_ending)

    def test_inference_confidence_is_bounded(self) -> None:
        document = structured_score()
        document["harmony"][0]["provenance"]["confidence"] = 1.01

        with self.assertRaisesRegex(score.ScoreError, "confidence must be between 0 and 1"):
            score.validate(document)

    def test_confidence_and_alternatives_are_inference_only(self) -> None:
        confidence = structured_score()
        confidence["parts"][0]["provenance"]["confidence"] = 0.9
        with self.assertRaisesRegex(score.ScoreError, "only valid for inferred"):
            score.validate(confidence)

        alternatives = structured_score()
        alternatives["parts"][0]["provenance"]["alternatives"] = ["other"]
        with self.assertRaisesRegex(score.ScoreError, "only valid for inferred"):
            score.validate(alternatives)

    def test_unknown_structural_and_provenance_fields_are_rejected(self) -> None:
        structural = structured_score()
        structural["sections"][0]["musescore_layout"] = "page"
        with self.assertRaisesRegex(score.ScoreError, r"sections\[0\] has unsupported fields"):
            score.validate(structural)

        provenance = structured_score()
        provenance["harmony"][0]["provenance"]["command"] = "run-me"
        with self.assertRaisesRegex(score.ScoreError, "provenance has unsupported fields"):
            score.validate(provenance)


if __name__ == "__main__":
    unittest.main()
