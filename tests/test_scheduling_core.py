from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "scheduling_core.py"
SPEC = importlib.util.spec_from_file_location("scheduling_core", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
scheduling = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scheduling
SPEC.loader.exec_module(scheduling)


class SchedulingCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = json.loads((ROOT / "examples" / "scheduling" / "weekly-progression.json").read_text())

    def clone(self):
        return json.loads(json.dumps(self.snapshot))

    def test_fixture_prioritizes_due_missed_maintenance(self) -> None:
        result = scheduling.propose(self.snapshot)
        self.assertEqual("proposed", result["status"])
        self.assertEqual("slide-foundations", result["selected"][0]["target_id"])
        self.assertTrue(result["selected"][0]["maintenance_due"])
        self.assertTrue(result["selected"][0]["catch_up"])
        self.assertTrue(result["requires_approval"])

    def test_replay_is_deterministic(self) -> None:
        self.assertEqual(scheduling.propose(self.snapshot), scheduling.propose(self.snapshot))

    def test_paused_item_is_excluded_without_losing_history(self) -> None:
        result = scheduling.propose(self.snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "ebow-control")
        self.assertFalse(row["eligible"])
        self.assertIn("paused", row["reasons"])

    def test_resume_is_snapshot_state_not_inference(self) -> None:
        snapshot = self.clone()
        item = next(item for item in snapshot["items"] if item["id"] == "ebow-control")
        item["state"] = "developing"
        item["active"] = True
        snapshot["constraints"]["max_active_items"] = 4
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "ebow-control")
        self.assertTrue(row["eligible"])

    def test_dependency_blocks_until_approved_state_unlocks(self) -> None:
        snapshot = self.clone()
        parent = next(item for item in snapshot["items"] if item["id"] == "slide-foundations")
        parent["state"] = "reliable-isolation"
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "slide-open-tuning")
        self.assertFalse(row["eligible"])
        self.assertEqual(["slide-foundations"], row["blockers"])
        parent["state"] = "reliable-context"
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "slide-open-tuning")
        self.assertTrue(row["eligible"])

    def test_active_capacity_blocks_new_work_but_not_due_maintenance(self) -> None:
        snapshot = self.clone()
        snapshot["constraints"]["max_active_items"] = 2
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "slide-open-tuning")
        self.assertFalse(row["eligible"])
        self.assertIn("active-capacity-full", row["reasons"])
        due = next(item for item in result["projection"] if item["target_id"] == "slide-foundations")
        self.assertTrue(due["eligible"])

    def test_high_load_uses_explicit_longer_recovery(self) -> None:
        snapshot = self.clone()
        item = next(item for item in snapshot["items"] if item["id"] == "country-hybrid-picking")
        item["last_practice_date"] = "2026-08-07"
        item["self_reported_load"] = "high"
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == item["id"])
        self.assertFalse(row["eligible"])
        self.assertIn("recovery-window", row["reasons"])

    def test_weekly_budgets_can_produce_no_op(self) -> None:
        snapshot = self.clone()
        snapshot["constraints"]["weekly_session_budget"] = 1
        result = scheduling.propose(snapshot)
        self.assertEqual("no-op", result["status"])
        self.assertEqual([], result["selected"])

    def test_repeat_limit_blocks_target(self) -> None:
        snapshot = self.clone()
        snapshot["constraints"]["max_sessions_per_target_per_week"] = 1
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == "country-hybrid-picking")
        self.assertFalse(row["eligible"])
        self.assertIn("weekly-repeat-limit", row["reasons"])

    def test_missing_verification_is_unknown_not_overdue(self) -> None:
        snapshot = self.clone()
        item = next(item for item in snapshot["items"] if item["id"] == "country-hybrid-picking")
        item["last_verified_date"] = None
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == item["id"])
        self.assertFalse(row["maintenance_due"])
        self.assertIsNone(row["maintenance_due_date"])

    def test_missed_session_gets_catch_up_order_but_not_constraint_override(self) -> None:
        snapshot = self.clone()
        item = next(item for item in snapshot["items"] if item["id"] == "slide-foundations")
        item["last_practice_date"] = "2026-08-08"
        result = scheduling.propose(snapshot)
        row = next(item for item in result["projection"] if item["target_id"] == item["id"])
        self.assertTrue(row["catch_up"])
        self.assertFalse(row["eligible"])
        self.assertIn("recovery-window", row["reasons"])

    def test_application_status_detects_stale_and_idempotent(self) -> None:
        proposal = scheduling.propose(self.snapshot)
        self.assertEqual("applicable", scheduling.application_status(proposal, self.snapshot["snapshot_version"]))
        self.assertEqual("stale", scheduling.application_status(proposal, "practice-state:13"))
        self.assertEqual("already-applied", scheduling.application_status(proposal, self.snapshot["snapshot_version"], [proposal["application_key"]]))

    def test_future_dates_are_rejected(self) -> None:
        snapshot = self.clone()
        snapshot["items"][0]["last_practice_date"] = "2026-08-09"
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_unknown_dependency_is_rejected(self) -> None:
        snapshot = self.clone()
        snapshot["items"][0]["dependencies"] = [{"target_id": "missing", "required_states": ["maintained"]}]
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)


if __name__ == "__main__":
    unittest.main()
