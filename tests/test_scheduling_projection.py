from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "scheduling_projection.py"
SPEC = importlib.util.spec_from_file_location("scheduling_projection", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
projection = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = projection
SPEC.loader.exec_module(projection)


class SchedulingProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = json.loads((ROOT / "examples" / "scheduling" / "projection-snapshot.json").read_text())

    def clone(self):
        return json.loads(json.dumps(self.snapshot))

    def test_projection_is_deterministic(self) -> None:
        self.assertEqual(projection.project(self.snapshot), projection.project(self.snapshot))

    def test_projection_preserves_approved_state_provenance_and_realizations(self) -> None:
        result = projection.project(self.snapshot)
        slide = next(item for item in result["items"] if item["item_id"] == "slide-foundations")
        self.assertEqual("intonation", slide["dimension"])
        self.assertEqual("assessment-slide-v8", slide["approved_transition_proposal_id"])
        self.assertTrue(slide["plateau_observed"])
        self.assertEqual("slide-working-60", slide["target_realization"]["timing_realization_id"])
        self.assertEqual("slide-maintenance-72", slide["maintenance_realization"]["timing_realization_id"])

    def test_projection_exposes_due_blocked_paused_retired_and_missed_status(self) -> None:
        result = projection.project(self.snapshot)
        ebow = next(item for item in result["items"] if item["item_id"] == "ebow-foundations")
        blocked = next(item for item in result["items"] if item["item_id"] == "open-tuning-slide")
        self.assertEqual("due", ebow["due_state"])
        self.assertTrue(blocked["blocked"])
        self.assertTrue(blocked["missed"])
        self.assertFalse(blocked["paused"])
        self.assertFalse(blocked["retired"])

    def test_weekly_and_monthly_goal_projection(self) -> None:
        result = projection.project(self.snapshot)
        weekly = next(goal for goal in result["goals"] if goal["goal_id"] == "goal-slide-weekly")
        monthly = next(goal for goal in result["goals"] if goal["goal_id"] == "goal-ebow-monthly")
        self.assertEqual(1, weekly["remaining_sessions"])
        self.assertFalse(weekly["complete"])
        self.assertEqual(0, monthly["remaining_sessions"])
        self.assertTrue(monthly["complete"])

    def test_goal_cannot_reference_unknown_item(self) -> None:
        snapshot = self.clone()
        snapshot["goals"][0]["item_id"] = "missing"
        with self.assertRaises(projection.ProjectionError):
            projection.project(snapshot)

    def test_goal_completed_count_cannot_exceed_target(self) -> None:
        snapshot = self.clone()
        snapshot["goals"][0]["completed_sessions"] = 3
        with self.assertRaises(projection.ProjectionError):
            projection.project(snapshot)

    def test_extension_metadata_is_non_authoritative_for_schedule_selection(self) -> None:
        extended = projection.scheduling.propose(self.snapshot)
        baseline = self.clone()
        baseline.pop("goals", None)
        for item in baseline["items"]:
            for field in (
                "dimension",
                "approved_transition_proposal_id",
                "target_realization",
                "maintenance_realization",
                "plateau_observed",
            ):
                item.pop(field, None)
        plain = projection.scheduling.propose(baseline)
        self.assertEqual(extended["selected"], plain["selected"])
        self.assertEqual(extended["excluded"], plain["excluded"])
        self.assertEqual(extended["conflicts"], plain["conflicts"])


if __name__ == "__main__":
    unittest.main()
