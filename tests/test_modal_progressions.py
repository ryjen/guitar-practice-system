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


class ModalProgressionTests(unittest.TestCase):
    def test_catalog_contains_bounded_modal_contexts(self) -> None:
        catalog = progression_catalog.load_catalog()
        progression_catalog.validate_catalog(catalog)
        dorian = progression_catalog.get_preset("progression-modal-dorian-i-iv")
        mixolydian = progression_catalog.get_preset(
            "progression-modal-mixolydian-i-bvii"
        )
        self.assertEqual({"mode": "dorian"}, dorian["modal_context"])
        self.assertEqual({"mode": "mixolydian"}, mixolydian["modal_context"])
        self.assertEqual(["Im", "Im", "IV", "IV"], dorian["changes"])
        self.assertEqual(["I", "I", "bVII", "bVII"], mixolydian["changes"])

    def test_d_dorian_resolves_from_tonal_center_with_c_key_signature(self) -> None:
        self.assertEqual(
            ["Dm", "Dm", "G", "G"],
            progression_catalog.resolve_progression(
                "progression-modal-dorian-i-iv",
                "C",
                tonal_center="D",
            ),
        )
        self.assertEqual("C", progression_catalog.expected_parent_major_key("dorian", "D"))

    def test_g_mixolydian_resolves_from_tonal_center_with_c_key_signature(self) -> None:
        self.assertEqual(
            ["G", "G", "F", "F"],
            progression_catalog.resolve_progression(
                "progression-modal-mixolydian-i-bvii",
                "C",
                tonal_center="G",
            ),
        )
        self.assertEqual(
            "C",
            progression_catalog.expected_parent_major_key("mixolydian", "G"),
        )

    def test_modal_resolution_fails_closed_on_missing_or_wrong_context(self) -> None:
        with self.assertRaisesRegex(
            progression_catalog.ProgressionError,
            "requires tonal_center",
        ):
            progression_catalog.resolve_progression(
                "progression-modal-dorian-i-iv",
                "C",
            )

        with self.assertRaisesRegex(
            progression_catalog.ProgressionError,
            "requires parent-major key signature C",
        ):
            progression_catalog.resolve_progression(
                "progression-modal-dorian-i-iv",
                "D",
                tonal_center="D",
            )

        with self.assertRaisesRegex(
            progression_catalog.ProgressionError,
            "tonal_center must be one of",
        ):
            progression_catalog.resolve_progression(
                "progression-modal-dorian-i-iv",
                "C",
                tonal_center="F#",
            )

        with self.assertRaisesRegex(
            progression_catalog.ProgressionError,
            "only supported for modal progression presets",
        ):
            progression_catalog.resolve_progression(
                "progression-major-i-iv-v",
                "G",
                tonal_center="G",
            )

    def test_modal_examples_resolve_deterministically_and_render_type_one_midi(self) -> None:
        cases = (
            (
                "d-dorian-request.json",
                ["Dm", "Dm", "G", "G"],
                "dorian",
                "D",
                "D-DORIAN",
            ),
            (
                "g-mixolydian-request.json",
                ["G", "G", "F", "F"],
                "mixolydian",
                "G",
                "G-MIXOLYDIAN",
            ),
        )
        for filename, chords, mode, tonal_center, marker in cases:
            with self.subTest(filename=filename):
                path = ROOT / "examples" / "backing-tracks" / filename
                request = json.loads(path.read_text(encoding="utf-8"))
                first = resolve_backing_track_request.resolve_request(request)
                second = resolve_backing_track_request.resolve_request(
                    json.loads(json.dumps(request))
                )
                self.assertEqual(first, second)
                self.assertEqual("C", first["key_signature"])
                self.assertEqual(chords, first["sections"][0]["chords"])
                self.assertEqual(mode, first["provenance"]["mode"])
                self.assertEqual(tonal_center, first["provenance"]["tonal_center"])
                self.assertEqual("C", first["provenance"]["key_signature"])
                backing_track_engine.validate_manifest(first)

                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = root / "manifest.json"
                    output = root / "modal.mid"
                    manifest.write_text(json.dumps(first, indent=2), encoding="utf-8")
                    backing_track_engine.generate(manifest, output)
                    report = midi_workflow.validate_output(manifest, output)

                self.assertEqual(1, report["format"])
                self.assertEqual(
                    ["Conductor", "Drums", "Bass", "Keys"],
                    report["track_names"],
                )
                self.assertEqual(["COUNT-IN", marker, "END"], report["markers"])

    def test_request_rejects_modal_context_mismatches(self) -> None:
        path = ROOT / "examples" / "backing-tracks" / "d-dorian-request.json"
        request = json.loads(path.read_text(encoding="utf-8"))

        missing = json.loads(json.dumps(request))
        del missing["tonal_center"]
        with self.assertRaisesRegex(midi_workflow.ManifestError, "requires tonal_center"):
            resolve_backing_track_request.resolve_request(missing)

        wrong_key = json.loads(json.dumps(request))
        wrong_key["key_signature"] = "D"
        with self.assertRaisesRegex(
            midi_workflow.ManifestError,
            "requires parent-major key signature C",
        ):
            resolve_backing_track_request.resolve_request(wrong_key)

        accidental = json.loads(json.dumps(request))
        accidental["tonal_center"] = "D#"
        with self.assertRaisesRegex(midi_workflow.ManifestError, "tonal_center must be one of"):
            resolve_backing_track_request.resolve_request(accidental)

        non_modal = json.loads(json.dumps(request))
        non_modal["form"] = {
            "bars": 8,
            "progression_preset": "progression-major-i-iv-v",
            "section_name": "I-IV-V",
        }
        non_modal["key_signature"] = "G"
        with self.assertRaisesRegex(
            midi_workflow.ManifestError,
            "only supported for modal progression presets",
        ):
            resolve_backing_track_request.resolve_request(non_modal)


if __name__ == "__main__":
    unittest.main()
