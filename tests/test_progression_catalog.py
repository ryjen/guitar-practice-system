from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain import progression

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalogs" / "progressions" / "catalog.json"

# End-to-end rendering remains in the generation subsystem until #99.
sys.path.insert(0, str(ROOT / "scripts"))
import backing_track_engine  # noqa: E402
import midi_workflow  # noqa: E402
import resolve_backing_track_request  # noqa: E402


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_preset(preset_id: str) -> dict:
    return progression.get_preset(load_catalog(), preset_id)


def resolve_progression(
    preset_id: str,
    key_signature: str,
    *,
    tonal_center: str | None = None,
) -> list[str]:
    return progression.resolve_progression(
        load_catalog(),
        preset_id,
        key_signature,
        tonal_center=tonal_center,
    )


def resolve_circle_of_fourths(
    preset_id: str,
    *,
    start_key: str = "C",
    count: int = 12,
) -> list[dict]:
    return progression.resolve_circle_of_fourths(
        load_catalog(),
        preset_id,
        start_key=start_key,
        count=count,
    )


class ProgressionCatalogTests(unittest.TestCase):
    def test_catalog_validates_and_contains_expected_presets(self) -> None:
        catalog = load_catalog()
        progression.validate_catalog(catalog)
        ids = [preset["id"] for preset in catalog["presets"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("jazz-blues-12", ids)
        self.assertIn("progression-jazz-major-ii-v-i", ids)
        self.assertIn("progression-major-i-iv-v", ids)

        twelve_bar_blues = [
            preset
            for preset in catalog["presets"]
            if preset["family"] == "twelve-bar-blues"
        ]
        self.assertTrue(twelve_bar_blues)
        self.assertTrue(all(preset["bars"] == 12 for preset in twelve_bar_blues))
        self.assertEqual(4, get_preset("progression-jazz-major-ii-v-i")["bars"])
        self.assertEqual(8, get_preset("progression-major-i-iv-v")["bars"])

    def test_jazz_blues_opening_and_ending_are_fixed(self) -> None:
        preset = get_preset("jazz-blues-12")
        self.assertEqual(["I7", "I7", "IV7", "IV7"], preset["changes"][:4])
        self.assertEqual(["VI7", "II7", "V7", "I7"], preset["changes"][-4:])
        self.assertEqual(preset["changes"][:4], preset["invariants"]["opening"])
        self.assertEqual(preset["changes"][-4:], preset["invariants"]["ending"])

    def test_jazz_blues_resolves_in_c_and_a(self) -> None:
        self.assertEqual(
            [
                "C7",
                "C7",
                "F7",
                "F7",
                "C7",
                "C7",
                "G7",
                "C7",
                "A7",
                "D7",
                "G7",
                "C7",
            ],
            resolve_progression("jazz-blues-12", "C"),
        )
        self.assertEqual(
            [
                "A7",
                "A7",
                "D7",
                "D7",
                "A7",
                "A7",
                "E7",
                "A7",
                "F#7",
                "B7",
                "E7",
                "A7",
            ],
            resolve_progression("jazz-blues-12", "A"),
        )

    def test_major_ii_v_i_resolves_in_c_and_f(self) -> None:
        preset_id = "progression-jazz-major-ii-v-i"
        self.assertEqual(
            ["Dm7", "G7", "Cmaj7", "Cmaj7"],
            resolve_progression(preset_id, "C"),
        )
        self.assertEqual(
            ["Gm7", "C7", "Fmaj7", "Fmaj7"],
            resolve_progression(preset_id, "F"),
        )

    def test_major_i_iv_v_resolves_in_g_and_a(self) -> None:
        preset_id = "progression-major-i-iv-v"
        self.assertEqual(
            ["G", "G", "C", "C", "G", "D", "G", "D"],
            resolve_progression(preset_id, "G"),
        )
        self.assertEqual(
            ["A", "A", "D", "D", "A", "E", "A", "E"],
            resolve_progression(preset_id, "A"),
        )

    def test_circle_of_fourths_is_deterministic_and_bounded(self) -> None:
        preset_id = "progression-jazz-major-ii-v-i"
        full = resolve_circle_of_fourths(preset_id)
        self.assertEqual(
            list(progression.CIRCLE_OF_FOURTHS_MAJOR),
            [position["key_signature"] for position in full],
        )
        self.assertEqual(12, len({position["key_signature"] for position in full}))
        self.assertEqual(["Dm7", "G7", "Cmaj7", "Cmaj7"], full[0]["chords"])

        bounded = resolve_circle_of_fourths(preset_id, start_key="A", count=4)
        self.assertEqual(
            ["A", "D", "G", "C"],
            [position["key_signature"] for position in bounded],
        )

        enharmonic = resolve_circle_of_fourths(preset_id, start_key="F#", count=2)
        self.assertEqual(
            ["Gb", "B"],
            [position["key_signature"] for position in enharmonic],
        )

    def test_circle_of_fourths_rejects_invalid_bounds(self) -> None:
        preset_id = "progression-jazz-major-ii-v-i"
        for count in (0, 13, True):
            with self.subTest(count=count):
                with self.assertRaisesRegex(
                    progression.ProgressionError,
                    "count must be an integer between 1 and 12",
                ):
                    resolve_circle_of_fourths(preset_id, count=count)

        with self.assertRaisesRegex(
            progression.ProgressionError,
            "start_key must be one of",
        ):
            resolve_circle_of_fourths(preset_id, start_key="H", count=1)

    def test_minor_key_is_rejected_for_major_key_preset_resolution(self) -> None:
        with self.assertRaisesRegex(
            progression.ProgressionError,
            "require a major key signature",
        ):
            resolve_progression("jazz-blues-12", "Amin")

    def test_unsupported_enharmonic_major_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            progression.ProgressionError,
            "unsupported progression key",
        ):
            resolve_progression("jazz-blues-12", "D#")

    def test_committed_jazz_blues_artifacts_match_catalog_and_render(self) -> None:
        expected = resolve_progression("jazz-blues-12", "C")

        request_path = ROOT / "examples" / "backing-tracks" / "jazz-blues-12-request.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        self.assertEqual("jazz-blues-12", request["form"]["progression_preset"])
        self.assertNotIn("progression", request["form"])

        backing_manifest_path = ROOT / "backing-tracks" / "jazz-blues-12" / "manifest.json"
        backing_manifest = json.loads(backing_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(expected, backing_manifest["sections"][0]["chords"])
        self.assertEqual("walking", backing_manifest["tracks"][1]["bass"]["style"])
        backing_track_engine.validate_manifest(backing_manifest)

        spec = resolve_backing_track_request.resolve_request(request)
        self.assertEqual(12, spec["sections"][0]["bars"])
        self.assertEqual(expected, spec["sections"][0]["chords"])
        self.assertEqual("jazz-blues-12", spec["provenance"]["progression_preset"])
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

    def test_committed_ii_v_i_request_uses_catalog_and_renders(self) -> None:
        preset_id = "progression-jazz-major-ii-v-i"
        expected = resolve_progression(preset_id, "C")
        request_path = ROOT / "examples" / "backing-tracks" / "ii-v-i-c-request.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        self.assertEqual(preset_id, request["form"]["progression_preset"])
        self.assertNotIn("progression", request["form"])

        spec = resolve_backing_track_request.resolve_request(request)
        self.assertEqual(expected, spec["sections"][0]["chords"])
        self.assertEqual(preset_id, spec["provenance"]["progression_preset"])
        self.assertEqual("walking", spec["tracks"][1]["bass"]["style"])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "ii-v-i.mid"
            manifest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            backing_track_engine.generate(manifest, output)
            report = midi_workflow.validate_output(manifest, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(
            ["Conductor", "Drums", "Bass", "Keys"],
            report["track_names"],
        )
        self.assertEqual(["COUNT-IN", "II-V-I", "END"], report["markers"])

    def test_committed_i_iv_v_material_uses_catalog_and_renders(self) -> None:
        preset_id = "progression-major-i-iv-v"
        expected = resolve_progression(preset_id, "G")

        existing_manifest_path = ROOT / "backing-tracks" / "country-i-iv-v" / "manifest.json"
        existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(expected, existing_manifest["sections"][0]["chords"])

        request_path = ROOT / "examples" / "backing-tracks" / "i-iv-v-g-request.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        self.assertEqual(preset_id, request["form"]["progression_preset"])
        self.assertNotIn("progression", request["form"])

        spec = resolve_backing_track_request.resolve_request(request)
        self.assertEqual(expected, spec["sections"][0]["chords"])
        self.assertEqual(preset_id, spec["provenance"]["progression_preset"])
        self.assertEqual("kick-root-fifth", spec["tracks"][1]["bass"]["style"])
        self.assertEqual(
            ["drums", "bass", "keys"],
            [track["role"] for track in spec["tracks"]],
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "i-iv-v.mid"
            manifest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            backing_track_engine.generate(manifest, output)
            report = midi_workflow.validate_output(manifest, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(
            ["Conductor", "Drums", "Bass", "Keys"],
            report["track_names"],
        )
        self.assertEqual(["COUNT-IN", "I-IV-V", "END"], report["markers"])

    def test_invariant_mismatch_fails_catalog_validation(self) -> None:
        catalog = load_catalog()
        for preset in catalog["presets"]:
            if preset["id"] == "jazz-blues-12":
                preset["changes"][0] = "IV7"
                break
        with self.assertRaisesRegex(progression.ProgressionError, "opening invariant"):
            progression.validate_catalog(catalog)


if __name__ == "__main__":
    unittest.main()
