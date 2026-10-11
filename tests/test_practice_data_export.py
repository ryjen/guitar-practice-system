import copy
import json
import unittest
from pathlib import Path

from guitar_practice.adapters.json_values import JsonValueFileReader
from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_data_export import PracticeDataExport
from guitar_practice.domain.practice_data import CatalogError, validate_catalog

ROOT = Path(__file__).resolve().parents[1]


class PracticeDataExportTests(unittest.TestCase):
    def setUp(self):
        self.catalog = PracticeDataExport(
            values=JsonValueFileReader(ROOT),
            tree=WorkspaceFileTree(ROOT),
        ).catalog()

    def test_generated_export_matches_canonical_catalog(self):
        output = ROOT / "docs" / "data" / "practice-data.json"
        with output.open(encoding="utf-8") as handle:
            exported = json.load(handle)
        self.assertEqual(exported, self.catalog)

    def test_session_ids_are_unique(self):
        ids = [session["id"] for session in self.catalog["sessions"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_tempo_ladders_are_strictly_increasing(self):
        for session in self.catalog["sessions"]:
            tempo = session["tempo"]
            self.assertLess(tempo["slow"], tempo["medium"], session["id"])
            self.assertLess(tempo["medium"], tempo["fast"], session["id"])

    def test_duplicate_ids_are_rejected(self):
        invalid = copy.deepcopy(self.catalog)
        invalid["sessions"][1]["id"] = invalid["sessions"][0]["id"]
        with self.assertRaises(CatalogError):
            validate_catalog(invalid)

    def test_invalid_tempo_progression_is_rejected(self):
        invalid = copy.deepcopy(self.catalog)
        invalid["sessions"][0]["tempo"]["medium"] = invalid["sessions"][0]["tempo"]["slow"]
        with self.assertRaises(CatalogError):
            validate_catalog(invalid)


if __name__ == "__main__":
    unittest.main()
