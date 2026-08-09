from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "scheduling.py"
SPEC = importlib.util.spec_from_file_location("scheduling", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
scheduling = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scheduling
SPEC.loader.exec_module(scheduling)

FIXTURES = json.loads((ROOT / "examples" / "scheduling" / "fixtures.json").read_text(encoding="utf-8"))["scenarios"]


class SchedulingTests(unittest.TestCase):
    def scenario(self, name: str) -> dict:
        return copy.deepcopy(next(entry for entry in FIXTURES if entry["name"] == name))

    def test_scenario_fixtures(self) -> None:
        for scenario in FIXTURES:
            with self.subTest(scenario=scenario["name"]):
                proposal = scheduling.propose(copy.deepcopy(scenario["snapshot"]))
                self.assertEqual(
                    scenario["expected_selected"],
                    [item["item_id"] for item in proposal["selected"]],
                )
                if "expected_first_reason" in scenario:
                    self.assertIn(scenario["expected_first_reason"], proposal["selected"][0]["reason_codes"])
                if "expected_overdue_days" in scenario:
                    self.assertEqual(scenario["expected_overdue_days"], proposal["selected"][0]["overdue_days"])
                if "expected_conflict" in scenario:
                    self.assertIn(scenario["expected_conflict"], proposal["conflicts"])
                for item_id, reason in scenario.get("expected_excluded", {}).items():
                    entry = next(item for item in proposal["excluded"] if item["item_id"] == item_id)
                    self.assertIn(reason, entry["reason_codes"])

    def test_same_snapshot_produces_same_proposal_id(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        first = scheduling.propose(copy.deepcopy(snapshot))
        second = scheduling.propose(copy.deepcopy(snapshot))
        self.assertEqual(first, second)
        self.assertTrue(first["proposal_id"].startswith("schedule-"))
        self.assertTrue(first["requires_approval"])

    def test_proposal_generation_does_not_mutate_snapshot(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        original = copy.deepcopy(snapshot)
        scheduling.propose(snapshot)
        self.assertEqual(original, snapshot)

    def test_state_revision_change_makes_proposal_stale(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        proposal = scheduling.propose(copy.deepcopy(snapshot))
        current = copy.deepcopy(snapshot)
        current["state_revision"] += 1
        status = scheduling.approval_status(proposal, current)
        self.assertEqual("stale", status["status"])
        self.assertIn("state-revision-changed", status["reasons"])

    def test_ruleset_change_makes_proposal_stale(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        proposal = scheduling.propose(copy.deepcopy(snapshot))
        current = copy.deepcopy(snapshot)
        current["ruleset_version"] = "scheduling-rules-v2"
        status = scheduling.approval_status(proposal, current)
        self.assertEqual("stale", status["status"])
        self.assertIn("ruleset-version-changed", status["reasons"])

    def test_unchanged_complete_proposal_is_approval_valid(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        proposal = scheduling.propose(copy.deepcopy(snapshot))
        self.assertEqual({"status": "valid", "reasons": []}, scheduling.approval_status(proposal, snapshot))

    def test_high_load_caps_session_duration(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["self_reported_load"] = "high"
        snapshot["high_load_max_minutes"] = 20
        proposal = scheduling.propose(snapshot)
        self.assertEqual(20, sum(item["minutes"] for item in proposal["selected"]))
        self.assertIn("partial-time-allocation", proposal["selected"][-1]["reason_codes"])

    def test_high_load_doubles_explicit_recovery_window(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["items"][0]["last_practiced_at"] = "2026-08-07T12:00:00-07:00"
        snapshot["items"][0]["min_recovery_hours"] = 24
        snapshot["self_reported_load"] = "high"
        proposal = scheduling.propose(snapshot)
        slide = next(item for item in proposal["excluded"] if item["item_id"] == "slide")
        self.assertIn("recovery-window", slide["reason_codes"])

    def test_weekly_repetition_cap_excludes_target(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["items"][0]["weekly_count"] = snapshot["weekly_budget"]["max_same_target"]
        proposal = scheduling.propose(snapshot)
        slide = next(item for item in proposal["excluded"] if item["item_id"] == "slide")
        self.assertIn("weekly-repetition-cap", slide["reason_codes"])
        self.assertEqual(["wah"], [item["item_id"] for item in proposal["selected"]])

    def test_candidate_selection_respects_active_capacity(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["max_active_items"] = 2
        snapshot["items"].append({
            "id": "country",
            "state": "candidate",
            "priority": 0,
            "target_minutes": 10,
            "prerequisites": [],
            "weekly_count": 0,
            "min_recovery_hours": 0,
        })
        proposal = scheduling.propose(snapshot)
        country = next(item for item in proposal["excluded"] if item["item_id"] == "country")
        self.assertIn("active-capacity-full", country["reason_codes"])

    def test_invalid_active_capacity_snapshot_fails_closed(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["max_active_items"] = 1
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_effective_date_must_match_declared_timezone(self) -> None:
        snapshot = self.scenario("normal active priorities")["snapshot"]
        snapshot["effective_date"] = "2026-08-09"
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_schema_document_is_valid_json_and_has_all_record_types(self) -> None:
        schema = json.loads((ROOT / "contracts" / "scheduling" / "v1" / "scheduling.schema.json").read_text(encoding="utf-8"))
        self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        for name in ("snapshot", "proposal", "approval", "completion", "event"):
            self.assertIn(name, schema["$defs"])


if __name__ == "__main__":
    unittest.main()
