from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scheduling = load_module("scheduling_v2", ROOT / "scripts" / "scheduling_v2.py")
assessment = load_module("assessment_core_for_scheduling", ROOT / "scripts" / "assessment_core.py")
FIXTURE_DATA = json.loads((ROOT / "examples" / "scheduling" / "v2-fixtures.json").read_text(encoding="utf-8"))


class SchedulingV2Tests(unittest.TestCase):
    def scenario(self, name: str) -> tuple[dict, dict]:
        case = copy.deepcopy(next(item for item in FIXTURE_DATA["scenarios"] if item["name"] == name))
        snapshot = copy.deepcopy(FIXTURE_DATA["base_snapshot"])
        snapshot.update(copy.deepcopy(case["overrides"]))
        snapshot["snapshot_id"] = f"snapshot-{name.replace(' ', '-')}"
        return snapshot, case

    def test_progression_states_match_assessment_core(self) -> None:
        self.assertEqual(assessment.STATES, scheduling.PROGRESSION_STATES)

    def test_schema_uses_assessment_progression_states(self) -> None:
        schema = json.loads((ROOT / "contracts" / "scheduling" / "v2" / "scheduling.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(assessment.STATES), sorted(schema["$defs"]["progressionState"]["enum"]))
        for definition in (
            "practiceGoal",
            "activeWorkItem",
            "maintenanceRule",
            "dependency",
            "progressionProjection",
            "scheduleConstraint",
            "proposal",
            "approval",
            "completion",
            "event",
        ):
            self.assertIn(definition, schema["$defs"])

    def test_scenario_fixtures(self) -> None:
        for case in FIXTURE_DATA["scenarios"]:
            with self.subTest(scenario=case["name"]):
                snapshot, expected = self.scenario(case["name"])
                proposal = scheduling.propose(snapshot)
                self.assertEqual(expected["expected_selected"], [item["item_id"] for item in proposal["selected"]])
                if "expected_first_reason" in expected:
                    self.assertIn(expected["expected_first_reason"], proposal["selected"][0]["reason_codes"])
                if "expected_overdue_days" in expected:
                    self.assertEqual(expected["expected_overdue_days"], proposal["selected"][0]["overdue_days"])
                if "expected_conflict" in expected:
                    self.assertIn(expected["expected_conflict"], proposal["conflicts"])
                for item_id, reason in expected.get("expected_excluded", {}).items():
                    exclusion = next(item for item in proposal["excluded"] if item["item_id"] == item_id)
                    self.assertIn(reason, exclusion["reason_codes"])

    def test_progression_state_is_distinct_from_active_membership(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["active_work"] = [snapshot["active_work"][0]]
        snapshot["progression"][1]["state"] = "reliable-context"
        proposal = scheduling.propose(snapshot)
        self.assertEqual(["slide"], [item["item_id"] for item in proposal["selected"]])
        wah = next(item for item in proposal["excluded"] if item["item_id"] == "wah")
        self.assertIn("not-active-work", wah["reason_codes"])

    def test_maintained_item_cannot_be_active_development_work(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["progression"][0]["state"] = "maintained"
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_active_work_must_reference_active_goal(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["goals"][0]["status"] = "paused"
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_active_capacity_is_explicit_input_validation(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["constraints"]["max_active_items"] = 1
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)

    def test_high_load_caps_minutes_and_expands_recovery(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["constraints"]["self_reported_load"] = "high"
        snapshot["constraints"]["high_load_max_minutes"] = 20
        snapshot["active_work"][0]["min_recovery_hours"] = 24
        snapshot["progression"][0]["last_practiced_at"] = "2026-08-07T12:00:00-07:00"
        proposal = scheduling.propose(snapshot)
        slide = next(item for item in proposal["excluded"] if item["item_id"] == "slide")
        self.assertIn("recovery-window", slide["reason_codes"])
        self.assertLessEqual(sum(item["minutes"] for item in proposal["selected"]), 20)

    def test_weekly_repetition_cap_is_projection_data(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["progression"][0]["weekly_count"] = snapshot["constraints"]["weekly_budget"]["max_same_target"]
        proposal = scheduling.propose(snapshot)
        slide = next(item for item in proposal["excluded"] if item["item_id"] == "slide")
        self.assertIn("weekly-repetition-cap", slide["reason_codes"])

    def test_same_snapshot_is_deterministic_and_read_only(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        original = copy.deepcopy(snapshot)
        first = scheduling.propose(snapshot)
        second = scheduling.propose(copy.deepcopy(snapshot))
        self.assertEqual(first, second)
        self.assertEqual(original, snapshot)
        self.assertTrue(first["proposal_id"].startswith("schedule-"))
        self.assertTrue(first["requires_approval"])

    def test_stale_revision_and_ruleset_reject_approval(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        proposal = scheduling.propose(copy.deepcopy(snapshot))

        changed_state = copy.deepcopy(snapshot)
        changed_state["state_revision"] += 1
        status = scheduling.approval_status(proposal, changed_state)
        self.assertEqual("stale", status["status"])
        self.assertIn("state-revision-changed", status["reasons"])

        changed_rules = copy.deepcopy(snapshot)
        changed_rules["ruleset_version"] = "scheduling-rules-v3"
        status = scheduling.approval_status(proposal, changed_rules)
        self.assertEqual("stale", status["status"])
        self.assertIn("ruleset-version-changed", status["reasons"])

    def test_unchanged_complete_proposal_is_approval_valid(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        proposal = scheduling.propose(copy.deepcopy(snapshot))
        self.assertEqual({"status": "valid", "reasons": []}, scheduling.approval_status(proposal, snapshot))

    def test_supporting_assessment_references_are_projection_provenance_not_scores(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        baseline = scheduling.propose(copy.deepcopy(snapshot))
        snapshot["progression"][0]["supporting_assessment_proposal_ids"] = ["assessment-1", "assessment-2"]
        snapshot["state_revision"] += 1
        changed = scheduling.propose(snapshot)
        self.assertEqual(
            [item["item_id"] for item in baseline["selected"]],
            [item["item_id"] for item in changed["selected"]],
        )

    def test_effective_date_must_match_declared_timezone(self) -> None:
        snapshot, _ = self.scenario("normal progression")
        snapshot["effective_date"] = "2026-08-09"
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.propose(snapshot)


if __name__ == "__main__":
    unittest.main()
