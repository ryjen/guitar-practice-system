from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "assessment_core.py"
SPEC = importlib.util.spec_from_file_location("assessment_core", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
assessment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = assessment
SPEC.loader.exec_module(assessment)


class AssessmentCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = json.loads((ROOT / "examples" / "assessment" / "slide-reliable-context.json").read_text())
        self.gates = json.loads((ROOT / "templates" / "assessment-gate-set.json").read_text())

    def test_promotion_fixture_passes_all_required_gates(self) -> None:
        result = assessment.assess(self.request, self.gates)
        self.assertTrue(result["transition_valid"])
        self.assertEqual("reliable-context", result["proposed_state"])
        self.assertTrue(result["requires_approval"])
        self.assertTrue(all(item["outcome"] in assessment.OUTCOMES for item in result["gate_results"]))
        self.assertFalse(result["missing_evidence"])

    def test_replay_is_deterministic(self) -> None:
        first = assessment.assess(self.request, self.gates)
        second = assessment.assess(self.request, self.gates)
        self.assertEqual(first, second)

    def test_missing_musical_context_is_unknown_not_fail(self) -> None:
        request = dict(self.request)
        request["evidence"] = [item for item in self.request["evidence"] if item["evidence_type"] != "musical-context"]
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "musical-context-transfer")
        self.assertEqual("unknown", gate["outcome"])
        self.assertFalse(result["transition_valid"])

    def test_conflicting_observations_are_unknown(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["evidence"][-1]["observations"]["timing_gate"] = "fail"
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "timing-explicit")
        self.assertEqual("unknown", gate["outcome"])
        self.assertFalse(result["transition_valid"])

    def test_explicit_failed_observation_is_fail(self) -> None:
        request = json.loads(json.dumps(self.request))
        for item in request["evidence"]:
            item["observations"]["timing_gate"] = "fail"
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "timing-explicit")
        self.assertEqual("fail", gate["outcome"])
        self.assertFalse(result["transition_valid"])

    def test_explicit_stop_condition_blocks_transition(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["evidence"][-1]["observations"]["physical_stop"] = True
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "physical-stop-condition")
        self.assertEqual("blocked", gate["outcome"])
        self.assertFalse(result["transition_valid"])

    def test_two_attempts_in_one_session_do_not_satisfy_session_separation(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["evidence"][1]["session_id"] = request["evidence"][0]["session_id"]
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "isolated-repeatability")
        self.assertEqual("unknown", gate["outcome"])
        self.assertIn("session_count:1", gate["missing"])

    def test_stale_evidence_does_not_qualify(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["evidence"][0]["date"] = "2026-01-01"
        result = assessment.assess(request, self.gates)
        gate = next(item for item in result["gate_results"] if item["gate_id"] == "isolated-repeatability")
        self.assertEqual("unknown", gate["outcome"])

    def test_conflicting_evidence_list_blocks_transition(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["conflicting_evidence_ids"] = ["slide-context-1"]
        result = assessment.assess(request, self.gates)
        self.assertFalse(result["transition_valid"])
        self.assertEqual(["slide-context-1"], result["conflicting_evidence_ids"])

    def test_partial_regression_can_target_only_isolation_state(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["current_state"] = "reliable-context"
        request["proposed_state"] = "reliable-isolation"
        result = assessment.assess(request, self.gates)
        context_gate = next(item for item in result["gate_results"] if item["gate_id"] == "musical-context-transfer")
        self.assertEqual("not-applicable", context_gate["outcome"])
        self.assertTrue(result["transition_valid"])
        self.assertEqual("reliable-isolation", result["proposed_state"])

    def test_failed_maintenance_can_propose_regression_without_mutating(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["current_state"] = "maintained"
        request["proposed_state"] = "reliable-context"
        for item in request["evidence"]:
            item["observations"]["timing_gate"] = "fail"
        result = assessment.assess(request, self.gates)
        self.assertFalse(result["transition_valid"])
        self.assertIsNone(result["proposed_state"])
        self.assertTrue(result["requires_approval"])

    def test_invalid_transition_is_rejected(self) -> None:
        request = dict(self.request)
        request["current_state"] = "discovered"
        request["proposed_state"] = "reliable-context"
        with self.assertRaises(assessment.AssessmentError):
            assessment.assess(request, self.gates)

    def test_gate_revision_changes_ruleset_and_proposal_identity(self) -> None:
        first = assessment.assess(self.request, self.gates)
        gates = json.loads(json.dumps(self.gates))
        gates["revision"] = 2
        second = assessment.assess(self.request, gates)
        self.assertNotEqual(first["ruleset_fingerprint"], second["ruleset_fingerprint"])
        self.assertNotEqual(first["proposal_id"], second["proposal_id"])

    def test_non_authoritative_metadata_is_ignored(self) -> None:
        request = json.loads(json.dumps(self.request))
        request["evidence"][-1]["confidence"] = 0.99
        request["evidence"][-1]["interpretation"] = "probably mastered"
        request["evidence"][-1]["recommendation"] = "promote"
        baseline = assessment.assess(self.request, self.gates)
        decorated = assessment.assess(request, self.gates)
        self.assertEqual(baseline["transition_valid"], decorated["transition_valid"])
        self.assertEqual(baseline["gate_results"], decorated["gate_results"])


if __name__ == "__main__":
    unittest.main()
