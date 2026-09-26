from __future__ import annotations

import unittest
from typing import Any, Mapping

from guitar_practice.application.score_documents import ScoreDocuments, new_score
from guitar_practice.domain import score


class MemoryDocuments:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def read(self, path: str) -> Mapping[str, Any]:
        return self.values[path]

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = dict(document)


class ScoreDocumentsApplicationTests(unittest.TestCase):
    def test_new_score_is_minimal_valid_score_ir(self) -> None:
        document = new_score(title="Blue Thing")

        score.validate(document)
        self.assertEqual("blue-thing", document["id"])
        self.assertEqual([{"number": 1}], document["bars"])
        self.assertEqual([{"bar": 1, "beats": 4, "beat_unit": 4}], document["meter_map"])
        self.assertEqual([], document["tempo_map"])
        self.assertEqual([], document["parts"])

    def test_create_write_load_and_validation_report_share_one_contract(self) -> None:
        store = MemoryDocuments()
        service = ScoreDocuments(store)

        created = service.create(
            title="Blue Thing",
            score_id="blue-thing-custom",
            output="scores/blue.score.json",
        )

        self.assertEqual(created, service.load("scores/blue.score.json"))
        self.assertEqual(
            {
                "valid": True,
                "schema": score.SCHEMA_ID,
                "version": score.SCHEMA_VERSION,
                "id": "blue-thing-custom",
            },
            service.validation_report("scores/blue.score.json"),
        )

    def test_invalid_explicit_id_is_rejected_by_score_ir_validation(self) -> None:
        with self.assertRaisesRegex(score.ScoreError, "lowercase slug"):
            new_score(title="Blue Thing", score_id="Blue Thing")


if __name__ == "__main__":
    unittest.main()
