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
import resolve_backing_track_request  # noqa: E402


class BackingTrackRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request_path = ROOT / "examples" / "backing-tracks" / "funk-wah-request.json"
        self.request = json.loads(self.request_path.read_text(encoding="utf-8"))

    def test_example_resolves_to_valid_backing_track_spec(self) -> None:
        spec = resolve_backing_track_request.resolve_request(self.request)
        backing_track_engine.validate_manifest(spec)

        self.assertEqual("funk-wah-pocket-em-96", spec["id"])
        self.assertEqual([4, 4], spec["meter"])
        self.assertEqual(96, spec["tempo_bpm"])
        self.assertEqual(8, spec["sections"][0]["bars"])
        self.assertEqual(
            ["Em7", "A7", "Em7", "A7", "Em7", "A7", "Em7", "A7"],
            spec["sections"][0]["chords"],
        )
        self.assertEqual(["drums", "bass"], [track["role"] for track in spec["tracks"]])
        self.assertEqual("funk-wah-16", spec["tracks"][0]["groove_preset"])
        self.assertEqual(
            "generated/backing-tracks/funk-wah-pocket-em-96.mid",
            spec["outputs"]["midi"],
        )

    def test_resolution_is_deterministic_and_canonicalizes_instrument_order(self) -> None:
        first = resolve_backing_track_request.resolve_request(self.request)
        reordered = json.loads(json.dumps(self.request))
        reordered["instrumentation"] = ["bass", "drums"]
        second = resolve_backing_track_request.resolve_request(reordered)
        self.assertEqual(first, second)

    def test_rejects_unknown_request_field(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["free_form_instruction"] = "make it better"
        with self.assertRaises(midi_workflow.ManifestError):
            resolve_backing_track_request.resolve_request(request)

    def test_rejects_preset_meter_mismatch(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["meter"] = [7, 8]
        with self.assertRaisesRegex(midi_workflow.ManifestError, "uses meter"):
            resolve_backing_track_request.resolve_request(request)

    def test_rejects_tempo_outside_preset_range(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["tempo_bpm"] = 150
        with self.assertRaisesRegex(midi_workflow.ManifestError, "outside groove preset"):
            resolve_backing_track_request.resolve_request(request)

    def test_rejects_unsafe_id(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["id"] = "../outside"
        with self.assertRaisesRegex(midi_workflow.ManifestError, "kebab-case"):
            resolve_backing_track_request.resolve_request(request)

    def test_rejects_unknown_instrumentation_and_requires_drums(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["instrumentation"] = ["drums", "guitar"]
        with self.assertRaisesRegex(midi_workflow.ManifestError, "unsupported instrumentation"):
            resolve_backing_track_request.resolve_request(request)

        request["instrumentation"] = ["bass"]
        with self.assertRaisesRegex(midi_workflow.ManifestError, "must include drums"):
            resolve_backing_track_request.resolve_request(request)

    def test_rejects_unsupported_chord_before_rendering(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["form"]["progression"] = ["Em9"]
        with self.assertRaises(midi_workflow.ManifestError):
            resolve_backing_track_request.resolve_request(request)

    def test_resolved_spec_generates_valid_type_one_midi(self) -> None:
        spec = resolve_backing_track_request.resolve_request(self.request)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "request.mid"
            manifest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            backing_track_engine.generate(manifest, output)
            report = midi_workflow.validate_output(manifest, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(["COUNT-IN", "POCKET", "END"], report["markers"])


if __name__ == "__main__":
    unittest.main()
