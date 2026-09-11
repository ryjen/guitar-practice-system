from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import midi

ROOT = Path(__file__).resolve().parents[1]


class MidiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = ROOT / "backing-tracks" / "slide-slow-blues" / "manifest.json"

    def test_all_catalog_manifests_render_valid_type_one_midi(self) -> None:
        manifests = sorted((ROOT / "backing-tracks").glob("*/manifest.json"))
        self.assertGreaterEqual(len(manifests), 5)

        for manifest_path in manifests:
            with self.subTest(manifest=manifest_path.parent.name):
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                first = midi.render(manifest)
                second = midi.render(json.loads(json.dumps(manifest)))
                self.assertEqual(first, second)

                report = midi.validate_rendered(manifest, first)
                expected_names = [
                    "Conductor",
                    *[track["name"] for track in manifest["tracks"]],
                ]
                expected_markers = [
                    "COUNT-IN",
                    *[section["name"] for section in manifest["sections"]],
                    "END",
                ]

                self.assertEqual(1, report["format"])
                self.assertEqual(len(expected_names), report["tracks"])
                self.assertEqual(expected_names, report["track_names"])
                self.assertEqual(expected_markers, report["markers"])
                self.assertEqual(1, report["tempo_events"])
                self.assertEqual(1, report["meter_events"])
                self.assertEqual(1, report["key_events"])
                self.assertEqual(
                    f"generated/backing-tracks/{manifest['id']}.mid",
                    manifest["outputs"]["midi"],
                )

    def test_rejects_duplicate_track_names(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["tracks"][1]["name"] = manifest["tracks"][0]["name"]
        with self.assertRaises(midi.ManifestError):
            midi.validate_manifest(manifest)

    def test_rejects_section_bar_chord_mismatch(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["sections"][0]["bars"] += 1
        with self.assertRaises(midi.ManifestError):
            midi.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
