from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "adaptive_session.py"
SPEC = importlib.util.spec_from_file_location("adaptive_session", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
session = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = session
SPEC.loader.exec_module(session)


class AdaptiveSessionTests(unittest.TestCase):
    def request(self, duration: int = 30) -> dict:
        return {
            "duration_minutes": duration,
            "environment": "headphones",
            "priorities": ["slide-foundations", "wah-rhythm"],
            "active_techniques": ["slide-foundations", "wah-rhythm"],
            "max_active_techniques": 3,
            "available_gear": ["guitar-fender-strat-white", "headphones"],
            "available_backing_tracks": ["slide-slow-blues-a-60"],
            "desired_genres": ["blues"],
            "theory_focus": ["chord tones"],
            "evidence": {
                "slide-foundations": {
                    "largest_audible_defect": "pitch drifts during slow movement"
                }
            },
        }

    def test_supported_durations_sum_exactly(self) -> None:
        for duration in (15, 30, 45, 60):
            result = session.recommend(self.request(duration))
            self.assertEqual(duration, sum(block["minutes"] for block in result["blocks"]))

    def test_evidence_selects_focus_and_explains_it(self) -> None:
        result = session.recommend(self.request())
        self.assertEqual("slide-foundations", result["focus_technique"])
        technique = next(block for block in result["blocks"] if block["type"] == "technique")
        self.assertIn("explicit evidence", technique["why"])
        self.assertIn("pitch drifts", technique["why"])

    def test_missing_evidence_does_not_claim_weakness(self) -> None:
        request = self.request()
        request["evidence"] = {}
        result = session.recommend(request)
        self.assertTrue(any("does not claim a weakness" in warning for warning in result["warnings"]))

    def test_maintenance_precedes_priority_without_evidence(self) -> None:
        request = self.request()
        request["evidence"] = {}
        request["maintenance_due"] = ["ebow-foundations"]
        result = session.recommend(request)
        self.assertEqual("ebow-foundations", result["focus_technique"])

    def test_active_work_limit_is_enforced(self) -> None:
        request = self.request()
        request["max_active_techniques"] = 1
        with self.assertRaises(session.SessionError):
            session.validate_request(request)

    def test_headphone_variant_requires_conservative_direct_monitoring(self) -> None:
        result = session.recommend(self.request())
        self.assertIn("conservative headphone level", " ".join(result["environment_guidance"]))
        application = next(block for block in result["blocks"] if block["type"] == "application")
        self.assertIn("headphones", application["gear"])

    def test_acoustic_variant_warns_for_electric_only_focus(self) -> None:
        request = self.request(15)
        request["environment"] = "acoustic-only"
        request["priorities"] = ["wah-rhythm"]
        request["active_techniques"] = ["wah-rhythm"]
        request["evidence"] = {}
        result = session.recommend(request)
        self.assertTrue(any("electric capability" in warning for warning in result["warnings"]))
        self.assertNotIn("slide-slow-blues-a-60", next(block for block in result["blocks"] if block["type"] == "application")["title"])

    def test_recommendation_is_advisory_and_prohibits_mutation(self) -> None:
        result = session.recommend(self.request())
        self.assertTrue(result["advisory"])
        self.assertTrue(result["requires_approval"])
        self.assertIn("progress", result["prohibited_mutations"])
        self.assertTrue(next(block for block in result["blocks"] if block["type"] == "evidence")["evidence_required"])

    def test_invalid_duration_and_boolean_are_rejected(self) -> None:
        for duration in (20, True):
            request = self.request()
            request["duration_minutes"] = duration
            with self.assertRaises(session.SessionError):
                session.validate_request(request)


if __name__ == "__main__":
    unittest.main()
