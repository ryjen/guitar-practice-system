from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "adaptive_session.py"
SPEC = importlib.util.spec_from_file_location("adaptive_session_capacity", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
session = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = session
SPEC.loader.exec_module(session)


class AdaptiveSessionCapacityTests(unittest.TestCase):
    def test_full_capacity_skips_new_priority(self) -> None:
        request = {
            "duration_minutes": 30,
            "priorities": ["country-picking"],
            "active_techniques": ["slide-foundations", "wah-rhythm"],
            "max_active_techniques": 2,
            "evidence": {},
        }
        result = session.recommend(request)
        self.assertEqual("slide-foundations", result["focus_technique"])
        self.assertTrue(any("capacity is full" in warning for warning in result["warnings"]))

    def test_maintenance_can_run_at_full_capacity(self) -> None:
        request = {
            "duration_minutes": 30,
            "priorities": ["country-picking"],
            "active_techniques": ["slide-foundations", "wah-rhythm"],
            "maintenance_due": ["ebow-foundations"],
            "max_active_techniques": 2,
            "evidence": {},
        }
        result = session.recommend(request)
        self.assertEqual("ebow-foundations", result["focus_technique"])

    def test_fallback_is_complete_and_preserves_evidence(self) -> None:
        request = {
            "duration_minutes": 60,
            "priorities": ["slide-foundations"],
            "active_techniques": ["slide-foundations"],
            "evidence": {},
        }
        result = session.recommend(request)
        fallback = result["fallback"]
        self.assertEqual(30, fallback["duration_minutes"])
        self.assertEqual(30, sum(block["minutes"] for block in fallback["blocks"]))
        evidence = next(block for block in fallback["blocks"] if block["type"] == "evidence")
        self.assertTrue(evidence["evidence_required"])

    def test_quiet_and_no_computer_do_not_require_backing_track(self) -> None:
        for environment in ("quiet", "no-computer"):
            request = {
                "duration_minutes": 15,
                "environment": environment,
                "priorities": ["slide-foundations"],
                "available_backing_tracks": ["slide-slow-blues-a-60"],
                "evidence": {},
            }
            result = session.recommend(request)
            application = next(block for block in result["blocks"] if block["type"] == "application")
            self.assertNotIn("slide-slow-blues-a-60", application["title"])


if __name__ == "__main__":
    unittest.main()
