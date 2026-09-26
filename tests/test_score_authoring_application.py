from __future__ import annotations

import unittest
from typing import Any, Mapping

from guitar_practice.application.score_authoring import (
    ScoreAuthoring,
    parse_chord_grid,
    parse_form_spec,
)
from guitar_practice.domain import score
from tests.test_score_ir import minimal_score


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
