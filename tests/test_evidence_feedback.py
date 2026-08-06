from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "evidence_feedback.py"
SPEC = importlib.util.spec_from_file_location("evidence_feedback", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
feedback = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = feedback
SPEC.loader.exec_module(feedback)


class EvidenceFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        payload = json.loads((ROOT / "examples" / "evidence" / "slide-feedback.json").read_text())
        self.records = payload["records"]

    def test_example_is_reliability_eligible_but_advisory(self) -> None:
        result = feedback.summarize(self.records, date(2026, 8, 6))
        target = result["targets"][0]
        self.assertTrue(target["reliability_eligible"])
        self.assertTrue(target["requires_approval"])
        self.assertEqual("not-due", target["maintenance_status"])
        self.assertIn("reliability", result["prohibited_mutations"])

    def test_musical_context_is_required_for_reliability(self) -> None:
        result = feedback.summarize([self.records[0]], date(2026, 8, 6))
        self.assertFalse(result["targets"][0]["reliability_eligible"])

    def test_stale_context_does_not_qualify_as_recent(self) -> None:
        records = [dict(item) for item in self.records]
        records[0]["date"] = "2026-01-01"
        records[1]["date"] = "2026-08-05"
        result = feedback.summarize(records, date(2026, 8, 6))
        self.assertFalse(result["targets"][0]["reliability_eligible"])

    def test_missing_interval_is_unknown_not_overdue_or_reliable(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["maintenance_interval_days"] = None
        result = feedback.summarize(records, date(2026, 8, 6))
        target = result["targets"][0]
        self.assertEqual("unknown", target["maintenance_status"])
        self.assertFalse(target["reliability_eligible"])

    def test_regression_requires_comparison_evidence(self) -> None:
        record = dict(self.records[-1])
        record["regression_observed"] = True
        record["comparison_evidence_id"] = None
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(record)

    def test_regression_comparison_must_exist_and_be_earlier(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["regression_observed"] = True
        records[-1]["comparison_evidence_id"] = "missing-evidence"
        with self.assertRaises(feedback.EvidenceError):
            feedback.summarize(records, date(2026, 8, 6))

    def test_duplicate_evidence_ids_are_rejected(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["id"] = records[0]["id"]
        with self.assertRaises(feedback.EvidenceError):
            feedback.summarize(records, date(2026, 8, 6))

    def test_future_dated_evidence_is_rejected(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["date"] = "2026-08-07"
        with self.assertRaises(feedback.EvidenceError):
            feedback.summarize(records, date(2026, 8, 6))

    def test_signed_or_secret_media_reference_is_rejected(self) -> None:
        record = dict(self.records[-1])
        record["media_reference"] = "https://example.invalid/audio?X-Amz-Signature=secret"
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(record)

    def test_personal_absolute_home_path_is_rejected(self) -> None:
        record = dict(self.records[-1])
        record["media_reference"] = "/home/person/recordings/take.wav"
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(record)

    def test_empty_defect_or_next_action_is_rejected(self) -> None:
        record = dict(self.records[-1])
        record["largest_audible_defect"] = ""
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(record)

    def test_physical_tension_defect_blocks_reliability(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["largest_audible_defect"] = "Physical tension increases during long phrases."
        result = feedback.summarize(records, date(2026, 8, 6))
        self.assertFalse(result["targets"][0]["reliability_eligible"])

    def test_regression_blocks_reliability(self) -> None:
        records = [dict(item) for item in self.records]
        records[-1]["regression_observed"] = True
        records[-1]["comparison_evidence_id"] = records[0]["id"]
        result = feedback.summarize(records, date(2026, 8, 6))
        self.assertFalse(result["targets"][0]["reliability_eligible"])

    def test_boolean_is_not_valid_tempo_or_interval(self) -> None:
        record = dict(self.records[-1])
        record["context"] = dict(record["context"])
        record["context"]["tempo_bpm"] = True
        with self.assertRaises(feedback.EvidenceError):
            feedback.validate_record(record)


if __name__ == "__main__":
    unittest.main()
