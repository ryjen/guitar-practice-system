from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "midi_workflow.py"
SPEC = importlib.util.spec_from_file_location("midi_workflow", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
midi_workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(midi_workflow)


class MidiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = ROOT / "backing-tracks" / "slide-slow-blues" / "manifest.json"

    def test_example_manifest_generates_valid_type_one_midi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "slide.mid"
            midi_workflow.generate(self.manifest, output)
            report = midi_workflow.validate_output(self.manifest, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(4, report["tracks"])
        self.assertEqual(
            ["Conductor", "Drums", "Bass", "Keys"], report["track_names"]
        )
        self.assertEqual(
            ["COUNT-IN", "PRACTICE-A", "PRACTICE-B", "END"],
            report["markers"],
        )
        self.assertEqual(1, report["tempo_events"])
        self.assertEqual(1, report["meter_events"])
        self.assertEqual(1, report["key_events"])

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
