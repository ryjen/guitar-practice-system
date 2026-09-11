from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import backing, backing_request, groove, midi, progression

ROOT = Path(__file__).resolve().parents[1]
GROOVE_CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)
PROGRESSION_CATALOG = json.loads(
    (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(encoding="utf-8")
)


def resolve(request: dict) -> dict:
    return backing_request.resolve_request(request, GROOVE_CATALOG, PROGRESSION_CATALOG)


class BackingTrackRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request_path = ROOT / "examples" / "backing-tracks" / "funk-wah-request.json"
        self.request = json.loads(self.request_path.read_text(encoding="utf-8"))

    def test_example_resolves_to_valid_backing_track_spec(self) -> None:
        spec = resolve(self.request)
        backing.validate_manifest(spec, GROOVE_CATALOG)

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
        self.assertEqual("kick-root-octave", spec["tracks"][1]["bass"]["style"])
        self.assertNotIn("progression_preset", spec["provenance"])
        self.assertEqual(
            "generated/backing-tracks/funk-wah-pocket-em-96.mid",
            spec["outputs"]["midi"],
        )

    def test_progression_preset_resolves_catalog_form_and_provenance(self) -> None:
        path = ROOT / "examples" / "backing-tracks" / "jazz-blues-12-request.json"
        request = json.loads(path.read_text(encoding="utf-8"))
        spec = resolve(request)
        expected = progression.resolve_progression(
            PROGRESSION_CATALOG,
            "jazz-blues-12",
            "C",
        )

        self.assertEqual("jazz-blues-12", request["form"]["progression_preset"])
        self.assertNotIn("progression", request["form"])
        self.assertEqual(expected, spec["sections"][0]["chords"])
        self.assertEqual("jazz-blues-12", spec["provenance"]["progression_preset"])
        self.assertEqual(["C7", "C7", "F7", "F7"], spec["sections"][0]["chords"][:4])
        self.assertEqual(["A7", "D7", "G7", "C7"], spec["sections"][0]["chords"][-4:])

    def test_progression_form_requires_exactly_one_source(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["form"]["progression_preset"] = "jazz-blues-12"
        with self.assertRaisesRegex(midi.ManifestError, "exactly one"):
            resolve(request)

        request = json.loads(json.dumps(self.request))
        del request["form"]["progression"]
        with self.assertRaisesRegex(midi.ManifestError, "exactly one"):
            resolve(request)

    def test_progression_preset_rejects_unknown_id_and_bar_mismatch(self) -> None:
        path = ROOT / "examples" / "backing-tracks" / "jazz-blues-12-request.json"
        request = json.loads(path.read_text(encoding="utf-8"))
        request["form"]["progression_preset"] = "does-not-exist"
        with self.assertRaisesRegex(midi.ManifestError, "unknown progression preset"):
            resolve(request)

        request = json.loads(path.read_text(encoding="utf-8"))
        request["form"]["bars"] = 16
        with self.assertRaisesRegex(midi.ManifestError, "does not match progression preset"):
            resolve(request)

    def test_progression_preset_meter_must_match_request(self) -> None:
        path = ROOT / "examples" / "backing-tracks" / "jazz-blues-12-request.json"
        request = json.loads(path.read_text(encoding="utf-8"))
        request["meter"] = [7, 8]
        request["groove_preset"] = "odd-7-8"
        request["tempo_bpm"] = 92
        with self.assertRaisesRegex(midi.ManifestError, "progression preset.*uses meter"):
            resolve(request)

    def test_resolution_is_deterministic_and_canonicalizes_instrument_order(self) -> None:
        first = resolve(self.request)
        reordered = json.loads(json.dumps(self.request))
        reordered["instrumentation"] = ["bass", "drums"]
        second = resolve(reordered)
        self.assertEqual(first, second)

    def test_auto_bass_style_is_preset_specific(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["groove_preset"] = "jazz-swing"
        request["tempo_bpm"] = 120
        request["bass_style"] = "auto"
        spec = resolve(request)
        self.assertEqual("walking", spec["tracks"][1]["bass"]["style"])

    def test_every_groove_preset_has_an_auto_bass_style(self) -> None:
        groove.validate_catalog(GROOVE_CATALOG)
        catalog_ids = {preset["id"] for preset in GROOVE_CATALOG["presets"]}
        self.assertEqual(catalog_ids, set(backing_request.AUTO_BASS_STYLE_BY_PRESET))

    def test_explicit_bass_style_requires_bass_instrumentation(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["instrumentation"] = ["drums"]
        request["bass_style"] = "walking"
        with self.assertRaisesRegex(midi.ManifestError, "requires bass"):
            resolve(request)

    def test_trims_bounded_metadata_and_rejects_oversize_text(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["title"] = "  Funk/Wah Pocket Practice  "
        request["purpose"] = "  Practice the pocket.  "
        request["key_signature"] = " Emin "
        request["groove_preset"] = " funk-wah-16 "
        request["form"]["section_name"] = " POCKET "
        spec = resolve(request)

        self.assertEqual("Funk/Wah Pocket Practice", spec["title"])
        self.assertEqual("Practice the pocket.", spec["purpose"])
        self.assertEqual("Emin", spec["key_signature"])
        self.assertEqual("POCKET", spec["sections"][0]["name"])
        self.assertEqual("funk-wah-16", spec["tracks"][0]["groove_preset"])

        request = json.loads(json.dumps(self.request))
        request["purpose"] = "x" * 501
        with self.assertRaisesRegex(midi.ManifestError, "at most 500"):
            resolve(request)

    def test_rejects_unknown_request_field(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["free_form_instruction"] = "make it better"
        with self.assertRaises(midi.ManifestError):
            resolve(request)

    def test_rejects_preset_meter_mismatch(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["meter"] = [7, 8]
        with self.assertRaisesRegex(midi.ManifestError, "uses meter"):
            resolve(request)

    def test_rejects_tempo_outside_preset_range(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["tempo_bpm"] = 150
        with self.assertRaisesRegex(midi.ManifestError, "outside groove preset"):
            resolve(request)

    def test_rejects_unsafe_id(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["id"] = "../outside"
        with self.assertRaisesRegex(midi.ManifestError, "kebab-case"):
            resolve(request)

    def test_rejects_unknown_instrumentation_and_requires_drums(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["instrumentation"] = ["drums", "guitar"]
        with self.assertRaisesRegex(midi.ManifestError, "unsupported instrumentation"):
            resolve(request)

        request["instrumentation"] = ["bass"]
        with self.assertRaisesRegex(midi.ManifestError, "must include drums"):
            resolve(request)

    def test_rejects_unsupported_chord_before_rendering(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["form"]["progression"] = ["Em9"]
        with self.assertRaises(midi.ManifestError):
            resolve(request)

    def test_resolved_spec_generates_valid_type_one_midi(self) -> None:
        spec = resolve(self.request)
        data = backing.render(spec, GROOVE_CATALOG)
        report = midi.validate_rendered(spec, data)

        self.assertEqual(1, report["format"])
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(["COUNT-IN", "POCKET", "END"], report["markers"])


if __name__ == "__main__":
    unittest.main()
