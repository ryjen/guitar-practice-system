from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "midi_workflow.py"
SPEC = importlib.util.spec_from_file_location("midi_workflow", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
midi_workflow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = midi_workflow
SPEC.loader.exec_module(midi_workflow)


class MidiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = ROOT / "backing-tracks" / "slide-slow-blues" / "manifest.json"

    def test_all_catalog_manifests_generate_valid_type_one_midi(self) -> None:
        manifests = sorted((ROOT / "backing-tracks").glob("*/manifest.json"))
        self.assertGreaterEqual(len(manifests), 5)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            for manifest_path in manifests:
                with self.subTest(manifest=manifest_path.parent.name):
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    output = output_dir / f"{manifest['id']}.mid"
                    midi_workflow.generate(manifest_path, output)
                    report = midi_workflow.validate_output(manifest_path, output)

                    expected_names = ["Conductor", *[track["name"] for track in manifest["tracks"]]]
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
        with self.assertRaises(midi_workflow.ManifestError):
            midi_workflow.validate_manifest(manifest)

    def test_rejects_section_bar_chord_mismatch(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["sections"][0]["bars"] += 1
        with self.assertRaises(midi_workflow.ManifestError):
            midi_workflow.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
