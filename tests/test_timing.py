from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "timing.py"
SPEC = importlib.util.spec_from_file_location("timing", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
timing = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = timing
SPEC.loader.exec_module(timing)


class TimingTests(unittest.TestCase):
    def straight(self) -> dict:
        return {
            "meter": "4/4",
            "start": {"bpm": 60, "beat_unit": "quarter"},
            "target": {"bpm": 90, "beat_unit": "quarter"},
            "subdivision": {"value": "eighth", "notes_per_beat": 2},
            "click": {"mode": "every-beat", "pulse_unit": "quarter"},
            "strategy": "ladder",
            "increment_bpm": 3,
            "decrement_bpm": 5,
            "clean_repetitions": 3,
            "max_failed_attempts": 2,
            "stop_condition": "accumulating tension",
            "final_check": "sparse click then musical context",
            "source": "session",
        }

    def test_straight_realization_is_valid(self) -> None:
        timing.validate_timing(self.straight())

    def test_odd_meter_requires_grouping(self) -> None:
        value = self.straight()
        value["meter"] = "7/8"
        value["start"]["beat_unit"] = "eighth"
        value["target"]["beat_unit"] = "eighth"
        value["click"]["pulse_unit"] = "eighth"
        with self.assertRaises(timing.TimingError):
            timing.validate_timing(value)
        value["grouping"] = [2, 2, 3]
        timing.validate_timing(value)

    def test_grouping_must_sum_to_numerator(self) -> None:
        value = self.straight()
        value["meter"] = "7/8"
        value["grouping"] = [3, 3]
        value["start"]["beat_unit"] = "eighth"
        value["target"]["beat_unit"] = "eighth"
        value["click"]["pulse_unit"] = "eighth"
        with self.assertRaises(timing.TimingError):
            timing.validate_timing(value)

    def test_compound_meter_requires_explicit_beat_unit(self) -> None:
        value = self.straight()
        value["meter"] = "6/8"
        del value["target"]["beat_unit"]
        with self.assertRaises(timing.TimingError):
            timing.validate_timing(value)
        value["target"]["beat_unit"] = "dotted-quarter"
        value["start"]["beat_unit"] = "dotted-quarter"
        value["click"]["pulse_unit"] = "dotted-quarter"
        timing.validate_timing(value)

    def test_bpm_without_subdivision_is_rejected(self) -> None:
        value = self.straight()
        del value["subdivision"]
        with self.assertRaises(timing.TimingError):
            timing.validate_timing(value)

    def test_effective_event_rate_includes_subdivision(self) -> None:
        self.assertEqual(180, timing.effective_event_rate(90, 2))
        self.assertEqual(360, timing.effective_event_rate(90, 4))


if __name__ == "__main__":
    unittest.main()
