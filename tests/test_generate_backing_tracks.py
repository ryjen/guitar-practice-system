from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonFileStore
from guitar_practice.application.generation import (
    GenerateBackingCatalog,
    manifest_output_path,
)
from guitar_practice.domain import midi

ROOT = Path(__file__).resolve().parents[1]


class GenerateBackingTracksTests(unittest.TestCase):
    def test_generate_all_uses_manifest_output_paths_and_validates_outputs(self) -> None:
        documents = JsonFileStore(ROOT)
        manifests = documents.glob("backing-tracks/*/manifest.json")
        self.assertGreaterEqual(len(manifests), 5)

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            results = GenerateBackingCatalog(
                documents=documents,
                locator=documents,
                artifacts=BinaryFileStore(repo_root),
            ).execute()

            self.assertEqual(len(manifests), len(results))
            for result in results:
                output = repo_root / result["output"]
                self.assertTrue(output.is_file())
                self.assertEqual(".mid", output.suffix)
                self.assertGreaterEqual(result["tracks"], 2)
                self.assertEqual("COUNT-IN", result["markers"][0])
                self.assertEqual("END", result["markers"][-1])

    def test_manifest_output_path_rejects_repository_escape(self) -> None:
        with self.assertRaises(midi.ManifestError):
            manifest_output_path(
                {
                    "id": "bad",
                    "outputs": {"midi": "../outside.mid"},
                }
            )

    def test_manifest_output_filename_must_match_id(self) -> None:
        with self.assertRaises(midi.ManifestError):
            manifest_output_path(
                {
                    "id": "expected-name",
                    "outputs": {"midi": "generated/backing-tracks/wrong-name.mid"},
                }
            )

    def test_manifest_output_path_matches_committed_manifest_contract(self) -> None:
        manifest = json.loads(
            (ROOT / "backing-tracks" / "slide-slow-blues" / "manifest.json").read_text()
        )
        self.assertEqual(
            "generated/backing-tracks/slide-slow-blues-a-60.mid",
            manifest_output_path(manifest),
        )


if __name__ == "__main__":
    unittest.main()
