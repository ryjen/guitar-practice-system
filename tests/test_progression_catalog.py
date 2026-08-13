from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import backing_track_engine  # noqa: E402
import midi_workflow  # noqa: E402
import progression_catalog  # noqa: E402
import resolve_backing_track_request  # noqa: E402


class ProgressionCatalogTests(unittest.TestCase):
    def test_catalog_validates_and_contains_unique_twelve_bar_presets(self) -> None:
        catalog = progression_catalog.load_catalog()
        progression_catalog.validate_catalog(catalog)
        ids = [preset["id"] for preset in catalog["presets"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("jazz-blues-12", ids)
        self.assertTrue(all(preset["bars"] == 12 for preset in catalog["presets"]))

    def test_jazz_blues_opening_and_ending_are_fixed(self) -> None:
        preset = progression_catalog.get_preset("jazz-blues-12")
        self.assertEqual(
            ["I7", "I7", "IV7", "IV7"],
            preset["changes"][:4],
        )
        self.assertEqual(
            ["VI7", "II7", "V7", "I7"],
            preset["changes"][-4:],
        )
        self.assertEqual(preset["changes"][:4], preset["invariants"]["opening"])
        self.assertEqual(preset["changes"][-4:], preset["invariants"]["ending"])

    def test_jazz_blues_resolves_in_c_and_a(self) -> None:
        self.assertEqual(
            [
                "C7", "C7", "F7", "F7",
                "C7", "C7", "G7", "C7",
                "A7", "D7", "G7", "C7",
            ],
            progression_catalog.resolve_progression("jazz-blues-12", "C"),
        )
        self.assertEqual(
            [
                "A7", "A7", "D7", "D7",
                "A7", "A7", "E7", "A7",
                "F#7", "B7", "E7", "A7",
            ],
            progression_catalog.resolve_progression("jazz-blues-12", "A"),
        )

    def test_minor_key_is_rejected_for_major_key_preset_resolution(self) -> None:
        with self.assertRaisesRegex(
            midi_workflow.ManifestError,
            "require a major key signature",
        ):
            progression_catalog.resolve_progression("jazz-blues-12", "Amin")

    def test_committed_jazz_blues_artifacts_match_catalog_and_render(self) -> None:
        expected = progression_catalog.resolve_progression("jazz-blues-12", "C")

        request_path = ROOT / "examples" / "backing-tracks" / "jazz-blues-12-request.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        self.assertEqual(expected, request["form"]["progression"])

        backing_manifest_path = ROOT / "backing-tracks" / "jazz-blues-12" / "manifest.json"
        backing_manifest = json.loads(backing_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(expected, backing_manifest["sections"][0]["chords"])
        self.assertEqual("walking", backing_manifest["tracks"][1]["bass"]["style"])
        backing_track_engine.validate_manifest(backing_manifest)

        spec = resolve_backing_track_request.resolve_request(request)
        self.assertEqual(12, spec["sections"][0]["bars"])
        self.assertEqual(expected, spec["sections"][0]["chords"])
        self.assertEqual(
            ["drums", "bass", "keys"],
            [track["role"] for track in spec["tracks"]],
        )
        self.assertEqual("walking", spec["tracks"][1]["bass"]["style"])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "jazz-blues.mid"
            manifest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            backing_track_engine.generate(manifest, output)
            report = midi_workflow.validate_output(manifest, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(
            ["Conductor", "Drums", "Bass", "Keys"],
            report["track_names"],
        )
        self.assertEqual(["COUNT-IN", "JAZZ-BLUES-12", "END"], report["markers"])

    def test_invariant_mismatch_fails_catalog_validation(self) -> None:
        catalog = progression_catalog.load_catalog()
        for preset in catalog["presets"]:
            if preset["id"] == "jazz-blues-12":
                preset["changes"][0] = "IV7"
                break
        with self.assertRaisesRegex(progression_catalog.ProgressionError, "opening invariant"):
            progression_catalog.validate_catalog(catalog)


if __name__ == "__main__":
    unittest.main()
