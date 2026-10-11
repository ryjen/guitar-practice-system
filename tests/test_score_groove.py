from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from guitar_practice.domain import groove, score, score_groove
from tests.test_score_ir import minimal_score

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)


class ScoreGrooveGuideTests(unittest.TestCase):
    def test_jazz_swing_guide_uses_exact_written_grid_and_transient_feel(self) -> None:
        source = minimal_score()
        original = copy.deepcopy(source)
        preset = groove.get_preset(CATALOG, "jazz-swing")
        preset_original = copy.deepcopy(preset)

        guide = score_groove.rhythm_guide(source, preset, bar=1)

        self.assertEqual([4, 4], guide["meter"])
        self.assertEqual(8, guide["grid"]["subdivision"])
        self.assertEqual(8, guide["grid"]["steps_per_bar"])
        self.assertEqual([1, 1], guide["grid"]["locations"][0]["beat"])
        self.assertEqual([3, 2], guide["grid"]["locations"][1]["beat"])
        self.assertFalse(guide["grid"]["locations"][0]["swung"])
        self.assertTrue(guide["grid"]["locations"][1]["swung"])
        self.assertEqual(0.333, guide["feel"]["swing"])
        self.assertEqual(8, guide["feel"]["humanize_ms"])
        self.assertEqual(original, source)
        self.assertEqual(preset_original, preset)

    def test_odd_meter_guide_has_fourteen_exact_sixteenth_steps(self) -> None:
        source = minimal_score()
        source["meter_map"] = [{"bar": 1, "beats": 7, "beat_unit": 8}]
        score.validate(source)
        preset = groove.get_preset(CATALOG, "odd-7-8")

        guide = score_groove.rhythm_guide(source, preset, bar=1)

        self.assertEqual([7, 8], guide["meter"])
        self.assertEqual(16, guide["grid"]["subdivision"])
        self.assertEqual(14, guide["grid"]["steps_per_bar"])
        self.assertEqual([15, 2], guide["grid"]["locations"][-1]["beat"])

    def test_meter_mismatch_fails_closed(self) -> None:
        source = minimal_score()
        source["meter_map"] = [{"bar": 1, "beats": 7, "beat_unit": 8}]
        score.validate(source)
        preset = groove.get_preset(CATALOG, "jazz-swing")

        with self.assertRaisesRegex(score_groove.ScoreGrooveError, "does not match"):
            score_groove.rhythm_guide(source, preset, bar=1)

    def test_parsed_instrument_pattern_and_variation_are_exposed(self) -> None:
        guide = score_groove.rhythm_guide(
            minimal_score(),
            groove.get_preset(CATALOG, "blues-shuffle"),
            bar=1,
        )

        instruments = {item["name"]: item for item in guide["instruments"]}
        self.assertEqual([0, 3, 4, 6], instruments["kick"]["steps"])
        self.assertEqual([0, 4], instruments["kick"]["accent_steps"])
        self.assertEqual(
            {"every_bars": 4, "steps": [7]},
            instruments["open_hat"]["variation"],
        )


if __name__ == "__main__":
    unittest.main()
