from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MIDI_PATH = ROOT / "scripts" / "midi_workflow.py"
MIDI_SPEC = importlib.util.spec_from_file_location("midi_workflow", MIDI_PATH)
assert MIDI_SPEC is not None and MIDI_SPEC.loader is not None
midi_workflow = importlib.util.module_from_spec(MIDI_SPEC)
sys.modules[MIDI_SPEC.name] = midi_workflow
MIDI_SPEC.loader.exec_module(midi_workflow)

ENGINE_PATH = ROOT / "scripts" / "groove_engine.py"
ENGINE_SPEC = importlib.util.spec_from_file_location("groove_engine", ENGINE_PATH)
assert ENGINE_SPEC is not None and ENGINE_SPEC.loader is not None
groove_engine = importlib.util.module_from_spec(ENGINE_SPEC)
sys.modules[ENGINE_SPEC.name] = groove_engine
ENGINE_SPEC.loader.exec_module(groove_engine)

CATALOG_PATH = ROOT / "scripts" / "groove_catalog.py"
CATALOG_SPEC = importlib.util.spec_from_file_location("groove_catalog", CATALOG_PATH)
assert CATALOG_SPEC is not None and CATALOG_SPEC.loader is not None
groove_catalog = importlib.util.module_from_spec(CATALOG_SPEC)
sys.modules[CATALOG_SPEC.name] = groove_catalog
CATALOG_SPEC.loader.exec_module(groove_catalog)


class GrooveCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = groove_catalog.load_catalog()

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
                spec = groove_engine.parse_groove(
                    preset["groove"],
                    meter=preset["meter"],
                )
                numerator, denominator = preset["meter"]
                beat_ticks = midi_workflow.TPQN * 4 // denominator
                bar_ticks = numerator * beat_ticks
                kwargs = {
                    "bar_index": 0,
                    "meter": preset["meter"],
                    "bar_ticks": bar_ticks,
                    "tempo_bpm": preset["default_tempo_bpm"],
                }
                self.assertEqual(
                    groove_engine.render_bar(spec, **kwargs),
                    groove_engine.render_bar(spec, **kwargs),
                )

    def test_odd_meter_preset_uses_fourteen_sixteenth_steps(self) -> None:
        preset = groove_catalog.get_preset("odd-7-8", catalog=self.catalog)
        spec = groove_engine.parse_groove(preset["groove"], meter=preset["meter"])
        self.assertEqual(16, spec.subdivision)
        self.assertEqual(14, groove_engine.steps_per_bar(preset["meter"], 16))

    def test_call_response_preset_mutes_two_bars_of_four(self) -> None:
        preset = groove_catalog.get_preset("call-response-2x2", catalog=self.catalog)
        spec = groove_engine.parse_groove(preset["groove"], meter=preset["meter"])
        bar_ticks = midi_workflow.TPQN * 4

        def render(bar: int):
            return groove_engine.render_bar(
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
        first = groove_catalog.resolved_groove("blues-shuffle", catalog=self.catalog)
        first["seed"] = 999
        second = groove_catalog.resolved_groove("blues-shuffle", catalog=self.catalog)
        self.assertNotEqual(first["seed"], second["seed"])

    def test_rejects_duplicate_preset_ids(self) -> None:
        invalid = json.loads(json.dumps(self.catalog))
        invalid["presets"].append(json.loads(json.dumps(invalid["presets"][0])))
        with self.assertRaises(midi_workflow.ManifestError):
            groove_catalog.validate_catalog(invalid)


if __name__ == "__main__":
    unittest.main()
