from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import evidence_feedback as feedback

ROOT = Path(__file__).resolve().parents[1]


class EvidenceV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / "templates" / "evidence.json").read_text())
        self.record.update({
            "id": "evidence-2026-08-08-slide",
            "date": "2026-08-08",
            "target_id": "slide-foundations",
            "evidence_type": "isolated-check",
            "largest_audible_defect": "Upward arrival remains slightly sharp.",
            "next_action": "Repeat two-fret arrivals at the same realization.",
        })
        self.record["context"]["timing"]["attempted"].update({
            "bpm": 60,
            "beat_unit": "quarter",
            "subdivision": "eighth",
            "notes_per_beat": 2,
            "click_mode": "normal",
            "click_pulse_unit": "quarter",
        })

    def test_version_2_template_shape_is_accepted(self) -> None:
        feedback.validate_record(self.record)

    def test_version_2_boolean_timing_verification_is_enforced(self) -> None:
        self.record["context"]["timing"]["later_session_verified"] = "yes"
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(self.record)

    def test_version_2_attempted_bpm_rejects_boolean(self) -> None:
        self.record["context"]["timing"]["attempted"]["bpm"] = True
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(self.record)


if __name__ == "__main__":
    unittest.main()
