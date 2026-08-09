#!/usr/bin/env python3
"""Evaluate explicit practice observations against versioned deterministic gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

OUTCOMES = {"pass", "fail", "unknown", "not-applicable", "blocked"}
STATES = {"discovered", "developing", "reliable-isolation", "reliable-context", "maintained", "paused", "retired"}
TRANSITIONS = {
    "discovered": {"developing", "paused", "retired"},
    "developing": {"reliable-isolation", "paused", "retired"},
    "reliable-isolation": {"developing", "reliable-context", "paused", "retired"},
    "reliable-context": {"developing", "reliable-isolation", "maintained", "paused", "retired"},
    "maintained": {"developing", "reliable-isolation", "reliable-context", "paused", "retired"},
    "paused": {"developing", "reliable-isolation", "reliable-context", "maintained", "retired"},
    "retired": {"discovered"},
}


class AssessmentError(ValueError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentError(f"{field} must be a non-empty string")
    return value.strip()


def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(nonempty(value, field))
    except ValueError as error:
        raise AssessmentError(f"{field} must be an ISO date") from error


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def validate_gate_set(gates: dict[str, Any]) -> None:
    if not isinstance(gates, dict) or gates.get("version") != 1:
        raise AssessmentError("gate set must be an object with version 1")
    nonempty(gates.get("id"), "gate_set.id")
    revision = gates.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise AssessmentError("gate_set.revision must be a positive integer")
    definitions = gates.get("gates")
    if not isinstance(definitions, list) or not definitions:
        raise AssessmentError("gate_set.gates must be a non-empty list")
    seen: set[str] = set()
    for gate in definitions:
        if not isinstance(gate, dict):
            raise AssessmentError("each gate must be an object")
        gate_id = nonempty(gate.get("id"), "gate.id")
        if gate_id in seen:
            raise AssessmentError(f"duplicate gate id: {gate_id}")
        seen.add(gate_id)
        nonempty(gate.get("dimension"), f"gate.{gate_id}.dimension")
        rule = gate.get("rule")
        if not isinstance(rule, dict) or rule.get("type") not in {"observation-equals", "evidence-count"}:
            raise AssessmentError(f"gate {gate_id} has unsupported rule")
        if rule["type"] == "observation-equals":
            nonempty(rule.get("field"), f"gate.{gate_id}.rule.field")
            if "expected" not in rule:
                raise AssessmentError(f"gate {gate_id} needs rule.expected")
        else:
            kinds = rule.get("evidence_types")
            if not isinstance(kinds, list) or not kinds or not all(isinstance(item, str) and item for item in kinds):
                raise AssessmentError(f"gate {gate_id} needs evidence_types")
            minimum = rule.get("minimum", 1)
            sessions = rule.get("minimum_sessions", 1)
            if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (minimum, sessions)):
                raise AssessmentError(f"gate {gate_id} count requirements must be positive integers")


def validate_request(request: dict[str, Any]) -> None:
    if not isinstance(request, dict) or request.get("version") != 1:
        raise AssessmentError("assessment request must be an object with version 1")
    nonempty(request.get("target_id"), "target_id")
    if request.get("current_state") not in STATES:
        raise AssessmentError("current_state is unsupported")
    proposed = request.get("proposed_state")
    if proposed not in STATES:
        raise AssessmentError("proposed_state is unsupported")
    if proposed not in TRANSITIONS[request["current_state"]]:
        raise AssessmentError(f"invalid transition: {request['current_state']} -> {proposed}")
    nonempty(request.get("state_revision"), "state_revision")
    parse_date(request.get("as_of"), "as_of")
    evidence = request.get("evidence", [])
    if not isinstance(evidence, list):
        raise AssessmentError("evidence must be a list")
    ids: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict):
            raise AssessmentError("evidence entries must be objects")
        evidence_id = nonempty(item.get("id"), "evidence.id")
        if evidence_id in ids:
            raise AssessmentError(f"duplicate evidence id: {evidence_id}")
        ids.add(evidence_id)
        if item.get("target_id") != request["target_id"]:
            raise AssessmentError("evidence target_id must match assessment target")
        parse_date(item.get("date"), f"evidence.{evidence_id}.date")
        nonempty(item.get("session_id"), f"evidence.{evidence_id}.session_id")
        nonempty(item.get("evidence_type"), f"evidence.{evidence_id}.evidence_type")
        observations = item.get("observations", {})
        if not isinstance(observations, dict):
            raise AssessmentError(f"evidence.{evidence_id}.observations must be an object")
    conflicts = request.get("conflicting_evidence_ids", [])
    if not isinstance(conflicts, list) or not all(isinstance(item, str) for item in conflicts):
        raise AssessmentError("conflicting_evidence_ids must be a list of strings")


def observation_values(request: dict[str, Any], field: str) -> list[Any]:
    values = []
    for item in request["evidence"]:
        if field in item.get("observations", {}):
            values.append(item["observations"][field])
    return values


def evaluate_gate(gate: dict[str, Any], request: dict[str, Any], as_of: date) -> dict[str, Any]:
    gate_id = gate["id"]
    if gate.get("applies_to_states") and request["proposed_state"] not in gate["applies_to_states"]:
        return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "not-applicable", "reason": "gate does not apply to proposed state", "used_evidence_ids": [], "missing": []}
    blocked_by = gate.get("blocked_by_observation")
    if isinstance(blocked_by, dict):
        values = observation_values(request, blocked_by.get("field", ""))
        if blocked_by.get("value") in values:
            return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "blocked", "reason": blocked_by.get("reason", "explicit blocking observation present"), "used_evidence_ids": [item["id"] for item in request["evidence"] if item.get("observations", {}).get(blocked_by.get("field")) == blocked_by.get("value")], "missing": []}
    rule = gate["rule"]
    max_age = gate.get("max_age_days")
    eligible = []
    for item in request["evidence"]:
        age = (as_of - parse_date(item["date"], "evidence.date")).days
        if age < 0:
            continue
        if max_age is None or age <= max_age:
            eligible.append(item)
    if rule["type"] == "observation-equals":
        field, expected = rule["field"], rule["expected"]
        relevant = [item for item in eligible if field in item.get("observations", {})]
        if not relevant:
            return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "unknown", "reason": f"no explicit observation for {field}", "used_evidence_ids": [], "missing": [field]}
        values = [item["observations"][field] for item in relevant]
        conflicts = set(values)
        if len(conflicts) > 1:
            return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "unknown", "reason": f"conflicting explicit observations for {field}", "used_evidence_ids": [item["id"] for item in relevant], "missing": []}
        outcome = "pass" if values[0] == expected else "fail"
        return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": outcome, "reason": f"{field} is {values[0]!r}; expected {expected!r}", "used_evidence_ids": [item["id"] for item in relevant], "missing": []}
    kinds = set(rule["evidence_types"])
    relevant = [item for item in eligible if item["evidence_type"] in kinds]
    sessions = {item["session_id"] for item in relevant}
    minimum = rule.get("minimum", 1)
    minimum_sessions = rule.get("minimum_sessions", 1)
    if len(relevant) < minimum or len(sessions) < minimum_sessions:
        missing = []
        if len(relevant) < minimum:
            missing.append(f"evidence_count:{minimum - len(relevant)}")
        if len(sessions) < minimum_sessions:
            missing.append(f"session_count:{minimum_sessions - len(sessions)}")
        return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "unknown", "reason": "insufficient qualifying evidence", "used_evidence_ids": [item["id"] for item in relevant], "missing": missing}
    return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "pass", "reason": "required evidence count and session separation satisfied", "used_evidence_ids": [item["id"] for item in relevant], "missing": []}


def assess(request: dict[str, Any], gate_set: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    validate_gate_set(gate_set)
    as_of = parse_date(request["as_of"], "as_of")
    results = [evaluate_gate(gate, request, as_of) for gate in gate_set["gates"]]
    required = [result for gate, result in zip(gate_set["gates"], results) if gate.get("required", True) and result["outcome"] != "not-applicable"]
    missing = sorted({item for result in required for item in result["missing"]})
    conflicts = sorted(set(request.get("conflicting_evidence_ids", [])))
    promotable = bool(required) and all(result["outcome"] == "pass" for result in required) and not conflicts
    transition = request["proposed_state"] if promotable else None
    input_fingerprint = stable_hash({"request": request, "gate_set": gate_set})
    proposal_id = f"assessment-{request['target_id']}-{input_fingerprint}"
    return {
        "version": 1,
        "proposal_id": proposal_id,
        "target_id": request["target_id"],
        "current_state": request["current_state"],
        "proposed_state": transition,
        "requested_state": request["proposed_state"],
        "state_revision": request["state_revision"],
        "gate_set": {"id": gate_set["id"], "revision": gate_set["revision"]},
        "ruleset_fingerprint": stable_hash(gate_set),
        "input_fingerprint": input_fingerprint,
        "gate_results": results,
        "supporting_evidence_ids": sorted({evidence_id for result in results if result["outcome"] == "pass" for evidence_id in result["used_evidence_ids"]}),
        "conflicting_evidence_ids": conflicts,
        "missing_evidence": missing,
        "transition_valid": promotable,
        "requires_approval": True,
        "application_key": f"{proposal_id}:{request['state_revision']}",
        "stale_when_state_revision_changes": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("gate_set")
    args = parser.parse_args()
    try:
        result = assess(read_json(Path(args.request)), read_json(Path(args.gate_set)))
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (AssessmentError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
