from __future__ import annotations

import unittest
from typing import Any, Mapping

from guitar_practice.application.score_authoring import (
    ScoreAuthoring,
    parse_chord_grid,
    parse_form_spec,
)
from guitar_practice.domain import score
from tests.test_score_ir import minimal_score, timeline_score


class MemoryDocuments:
    def __init__(self, values: dict[str, dict[str, Any]]) -> None:
        self.values = values

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = dict(document)


class ScoreAuthoringApplicationTests(unittest.TestCase):
    def test_form_parser_assigns_unique_ids_and_labels_to_repeated_sections(self) -> None:
        sections = parse_form_spec("intro:2 verse:4 verse:4 outro:1")

        self.assertEqual(
            [
                ("intro", "Intro", 2),
                ("verse", "Verse", 4),
                ("verse-2", "Verse 2", 4),
                ("outro", "Outro", 1),
            ],
            [(item.id, item.label, item.bars) for item in sections],
        )

    def test_chord_grid_preserves_explicit_empty_bar_cells(self) -> None:
        self.assertEqual(
            (("Cmaj7",), (), ("Dm7", "G7")),
            parse_chord_grid("| Cmaj7 |   | Dm7 G7 |"),
        )

    def test_note_input_document_drives_explicit_part_replacement(self) -> None:
        source = timeline_score()
        note_input = {
            "notes": [
                {
                    "location": {"bar": 1, "beat": [1, 1]},
                    "duration": [1, 8],
                    "voice": 1,
                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                }
            ]
        }
        store = MemoryDocuments(
            {
                "source.json": source,
                "notes.json": note_input,
            }
        )
        service = ScoreAuthoring(store, inputs=store)

        result = service.replace_notes(
            "source.json",
            part_id="guitar-1",
            input_path="notes.json",
            output="written.json",
        )

        self.assertEqual(source, store.values["source.json"])
        self.assertEqual(note_input, store.values["notes.json"])
        self.assertEqual(result, store.values["written.json"])
        self.assertEqual(
            ["note", "rest"],
            [event["kind"] for event in result["parts"][0]["events"]],
        )
        score.validate(result)

    def test_note_input_document_rejects_unknown_top_level_fields(self) -> None:
        store = MemoryDocuments(
            {
                "source.json": timeline_score(),
                "notes.json": {"notes": [], "ambient_current_score": "no"},
            }
        )
        service = ScoreAuthoring(store, inputs=store)

        with self.assertRaisesRegex(ValueError, "contain only notes"):
            service.replace_notes(
                "source.json",
                part_id="guitar-1",
                input_path="notes.json",
                output="written.json",
            )
        self.assertNotIn("written.json", store.values)

    def test_voicing_input_applies_exact_selector_to_explicit_part(self) -> None:
        source = timeline_score()
        voicing_input = {
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
        }
        store = MemoryDocuments(
            {
                "source.json": source,
                "voicing.json": voicing_input,
            }
        )
        service = ScoreAuthoring(store, inputs=store)

        result = service.apply_voicing(
            "source.json",
            part_id="guitar-1",
            input_path="voicing.json",
            output="written.json",
        )

        self.assertEqual(source, store.values["source.json"])
        self.assertEqual(voicing_input, store.values["voicing.json"])
        self.assertEqual(
            {"string": 2, "fret": 5},
            result["parts"][0]["events"][0]["position"],
        )
        self.assertEqual(result, store.values["written.json"])
        score.validate(result)

    def test_rhythm_input_updates_selected_note_without_mutating_inputs(self) -> None:
        source = timeline_score()
        source["parts"][0]["events"][2].pop("tuplet")
        score.validate(source)
        rhythm_input = {
            "rhythm": [
                {
                    "selector": {
                        "location": {"bar": 2, "beat": [1, 1]},
                        "voice": 2,
                        "pitch": {"step": "G", "alter": 0, "octave": 4},
                    },
                    "location": {"bar": 2, "beat": [2, 1]},
                    "duration": [1, 8],
                    "voice": 1,
                }
            ]
        }
        store = MemoryDocuments(
            {
                "source.json": source,
                "rhythm.json": rhythm_input,
            }
        )
        service = ScoreAuthoring(store, inputs=store)

        result = service.apply_rhythm(
            "source.json",
            part_id="guitar-1",
            input_path="rhythm.json",
            output="written.json",
        )

        self.assertEqual(source, store.values["source.json"])
        self.assertEqual(rhythm_input, store.values["rhythm.json"])
        moved = [
            event
            for event in result["parts"][0]["events"]
            if event.get("pitch") == {"step": "G", "alter": 0, "octave": 4}
        ][0]
        self.assertEqual({"bar": 2, "beat": [2, 1]}, moved["location"])
        self.assertEqual([1, 8], moved["duration"])
        self.assertEqual(result, store.values["written.json"])

    def test_form_then_section_chords_writes_new_documents_without_mutating_sources(self) -> None:
        initial = minimal_score()
        store = MemoryDocuments({"draft.json": initial})
        service = ScoreAuthoring(store)

        formed = service.replace_form(
            "draft.json",
            "intro:1 verse:2 outro:1",
            "formed.json",
        )
        harmonized = service.replace_chords(
            "formed.json",
            "Cmaj7 | Dm7 G7",
            "harmonized.json",
            section="Verse",
        )

        self.assertEqual(initial, store.values["draft.json"])
        self.assertEqual(4, len(formed["bars"]))
        self.assertNotIn("harmony", store.values["formed.json"])
        self.assertEqual([2, 3, 3], [event["location"]["bar"] for event in harmonized["harmony"]])
        self.assertEqual([[1, 1], [1, 1], [3, 1]], [event["location"]["beat"] for event in harmonized["harmony"]])
        score.validate(harmonized)


if __name__ == "__main__":
    unittest.main()
