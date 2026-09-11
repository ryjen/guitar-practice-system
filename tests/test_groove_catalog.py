from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import groove, midi

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalogs" / "grooves" / "catalog.json"


class GrooveCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        groove.validate_catalog(self.catalog)

    def test_catalog_contains_expected_practice_presets(self) -> None:
        ids = {preset["id"] for preset in self.catalog["presets"]}
        self.assertEqual(
            {
                "blues-shuffle",
                "country-train",
                "funk-wah-16",
                "jazz-swing",
                "alt-rock",
                "80s-rock",
                "odd-7-8",
                "call-response-2x2",
            },
            ids,
        )

    def test_every_preset_parses_and_renders_deterministically(self) -> None:
        for preset in self.catalog["presets"]:
            with self.subTest(preset=preset["id"]):
                spec = groove.parse_groove(preset["groove"], meter=preset["meter"])
                numerator, denominator = preset["meter"]
                beat_ticks = midi.TPQN * 4 // denominator
                bar_ticks = numerator * beat_ticks
                kwargs = {
                    "bar_index": 0,
                    "meter": preset["meter"],
                    "bar_ticks": bar_ticks,
                    "tempo_bpm": preset["default_tempo_bpm"],
                }
                self.assertEqual(groove.render_bar(spec, **kwargs), groove.render_bar(spec, **kwargs))

    def test_odd_meter_preset_uses_fourteen_sixteenth_steps(self) -> None:
        preset = groove.get_preset(self.catalog, "odd-7-8")
        spec = groove.parse_groove(preset["groove"], meter=preset["meter"])
        self.assertEqual(16, spec.subdivision)
        self.assertEqual(14, groove.steps_per_bar(preset["meter"], 16))

    def test_call_response_preset_mutes_two_bars_of_four(self) -> None:
        preset = groove.get_preset(self.catalog, "call-response-2x2")
        spec = groove.parse_groove(preset["groove"], meter=preset["meter"])
        bar_ticks = midi.TPQN * 4

        def render(bar: int):
            return groove.render_bar(
                spec,
                bar_index=bar,
                meter=preset["meter"],
                bar_ticks=bar_ticks,
                tempo_bpm=preset["default_tempo_bpm"],
            )

        self.assertTrue(render(0))
        self.assertTrue(render(1))
        self.assertEqual([], render(2))
        self.assertEqual([], render(3))
        self.assertTrue(render(4))

    def test_resolved_groove_is_an_isolated_copy(self) -> None:
        first = groove.resolved_groove(self.catalog, "blues-shuffle")
        first["seed"] = 999
        second = groove.resolved_groove(self.catalog, "blues-shuffle")
        self.assertNotEqual(first["seed"], second["seed"])

    def test_rejects_duplicate_preset_ids(self) -> None:
        invalid = json.loads(json.dumps(self.catalog))
        invalid["presets"].append(json.loads(json.dumps(invalid["presets"][0])))
        with self.assertRaises(midi.ManifestError):
            groove.validate_catalog(invalid)


if __name__ == "__main__":
    unittest.main()
