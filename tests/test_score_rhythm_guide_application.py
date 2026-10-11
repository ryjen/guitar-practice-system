from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any, Mapping

from guitar_practice.application.groove import GrooveCatalog
from guitar_practice.application.score_rhythm_guide import ScoreRhythmGuide
from tests.test_score_ir import minimal_score

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)


class MemoryDocuments:
    def __init__(self, values: dict[str, Mapping[str, Any]]) -> None:
        self.values = copy.deepcopy(values)

    def read(self, path: str) -> Mapping[str, Any]:
        return copy.deepcopy(self.values[path])

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        self.values[path] = copy.deepcopy(dict(document))


class ScoreRhythmGuideApplicationTests(unittest.TestCase):
    def test_service_resolves_existing_catalog_without_score_mutation(self) -> None:
        source = minimal_score()
        store = MemoryDocuments(
            {
                "catalog.json": CATALOG,
            }
        )
        service = ScoreRhythmGuide(GrooveCatalog(store, "catalog.json"))

        guide = service.build(source, "jazz-swing", bar=1)

        self.assertEqual("jazz-swing", guide["preset"]["id"])
        self.assertEqual(source, minimal_score())
        self.assertEqual(8, guide["grid"]["steps_per_bar"])


if __name__ == "__main__":
    unittest.main()
