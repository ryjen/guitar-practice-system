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
ACTIVE_RANK = {
    "discovered": 0,
    "developing": 1,
    "reliable-isolation": 2,
    "reliable-context": 3,
    "maintained": 4,
}
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


def transition_kind(current: str, proposed: str) -> str:
    if proposed in {"paused", "retired"} or current in {"paused", "retired"}:
        return "lifecycle"
    if ACTIVE_RANK[proposed] > ACTIVE_RANK[current]:
        return "promotion"
    return "regression"


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

        applies = gate.get("applies_to_states")
        if applies is not None:
            if not isinstance(applies, list) or not applies or not all(state in STATES for state in applies):
                raise AssessmentError(f"gate {gate_id} has invalid applies_to_states")

        max_age = gate.get("max_age_days")
        if max_age is not None and (isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 0):
            raise AssessmentError(f"gate {gate_id} max_age_days must be a non-negative integer")

        blocked_by = gate.get("blocked_by_observation")
        if blocked_by is not None:
            if not isinstance(blocked_by, dict):
                raise AssessmentError(f"gate {gate_id} blocked_by_observation must be an object")
            nonempty(blocked_by.get("field"), f"gate.{gate_id}.blocked_by_observation.field")
            if "value" not in blocked_by:
                raise AssessmentError(f"gate {gate_id} blocked_by_observation needs value")

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
    current = request.get("current_state")
    proposed = request.get("proposed_state")
    if current not in STATES:
        raise AssessmentError("current_state is unsupported")
    if proposed not in STATES:
        raise AssessmentError("proposed_state is unsupported")
    if proposed not in TRANSITIONS[current]:
        raise AssessmentError(f"invalid transition: {current} -> {proposed}")
    nonempty(request.get("state_revision"), "state_revision")
    as_of = parse_date(request.get("as_of"), "as_of")

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
        evidence_date = parse_date(item.get("date"), f"evidence.{evidence_id}.date")
        if evidence_date > as_of:
            raise AssessmentError(f"evidence {evidence_id} is dated after as_of")
        nonempty(item.get("session_id"), f"evidence.{evidence_id}.session_id")
        nonempty(item.get("evidence_type"), f"evidence.{evidence_id}.evidence_type")
        nonempty(item.get("producer"), f"evidence.{evidence_id}.producer")
        nonempty(item.get("observation_source"), f"evidence.{evidence_id}.observation_source")
        realization = item.get("realization")
        if realization is not None and not isinstance(realization, dict):
            raise AssessmentError(f"evidence.{evidence_id}.realization must be an object")
        observations = item.get("observations", {})
        if not isinstance(observations, dict):
            raise AssessmentError(f"evidence.{evidence_id}.observations must be an object")

    for field in ("conflicting_evidence_ids", "comparison_evidence_ids"):
        refs = request.get(field, [])
        if not isinstance(refs, list) or not all(isinstance(item, str) and item for item in refs):
            raise AssessmentError(f"{field} must be a list of non-empty strings")
        missing_refs = sorted(set(refs) - ids)
        if missing_refs:
            raise AssessmentError(f"{field} references unknown evidence: {missing_refs}")

    if transition_kind(current, proposed) == "regression" and not request.get("comparison_evidence_ids"):
        raise AssessmentError("regression transition requires comparison_evidence_ids")

    supersedes = request.get("supersedes_proposal_id")
    if supersedes is not None:
        nonempty(supersedes, "supersedes_proposal_id")


def observation_values(request: dict[str, Any], field: str) -> list[Any]:
    return [item["observations"][field] for item in request["evidence"] if field in item.get("observations", {})]


def evaluate_gate(gate: dict[str, Any], request: dict[str, Any], as_of: date) -> dict[str, Any]:
    gate_id = gate["id"]
    if gate.get("applies_to_states") and request["proposed_state"] not in gate["applies_to_states"]:
        return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "not-applicable", "reason": "gate does not apply to proposed state", "used_evidence_ids": [], "missing": []}

    blocked_by = gate.get("blocked_by_observation")
    if isinstance(blocked_by, dict):
        values = observation_values(request, blocked_by["field"])
        if blocked_by["value"] in values:
            return {
                "gate_id": gate_id,
                "dimension": gate["dimension"],
                "outcome": "blocked",
                "reason": blocked_by.get("reason", "explicit blocking observation present"),
                "used_evidence_ids": [item["id"] for item in request["evidence"] if item.get("observations", {}).get(blocked_by["field"]) == blocked_by["value"]],
                "missing": [],
            }

    rule = gate["rule"]
    max_age = gate.get("max_age_days")
    eligible = []
    for item in request["evidence"]:
        age = (as_of - parse_date(item["date"], "evidence.date")).days
        if max_age is None or age <= max_age:
            eligible.append(item)

    if rule["type"] == "observation-equals":
        field, expected = rule["field"], rule["expected"]
        relevant = [item for item in eligible if field in item.get("observations", {})]
        if not relevant:
            return {"gate_id": gate_id, "dimension": gate["dimension"], "outcome": "unknown", "reason": f"no explicit observation for {field}", "used_evidence_ids": [], "missing": [field]}
        values = [item["observations"][field] for item in relevant]
        if len({json.dumps(value, sort_keys=True) for value in values}) > 1:
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
    kind = transition_kind(request["current_state"], request["proposed_state"])
    as_of = parse_date(request["as_of"], "as_of")
    results = [evaluate_gate(gate, request, as_of) for gate in gate_set["gates"]]
    required = [result for gate, result in zip(gate_set["gates"], results) if gate.get("required", True) and result["outcome"] != "not-applicable"]
    missing = sorted({item for result in required for item in result["missing"]})
    conflicts = sorted(set(request.get("conflicting_evidence_ids", [])))

    if kind == "lifecycle":
        transition_valid = not conflicts
    else:
        transition_valid = bool(required) and all(result["outcome"] == "pass" for result in required) and not conflicts

    input_fingerprint = stable_hash({"request": request, "gate_set": gate_set})
    proposal_id = f"assessment-{request['target_id']}-{input_fingerprint}"
    return {
        "version": 1,
        "proposal_id": proposal_id,
        "supersedes_proposal_id": request.get("supersedes_proposal_id"),
        "target_id": request["target_id"],
        "transition_kind": kind,
        "current_state": request["current_state"],
        "proposed_state": request["proposed_state"] if transition_valid else None,
        "requested_state": request["proposed_state"],
        "state_revision": request["state_revision"],
        "gate_set": {"id": gate_set["id"], "revision": gate_set["revision"]},
        "ruleset_fingerprint": stable_hash(gate_set),
        "input_fingerprint": input_fingerprint,
        "gate_results": results,
        "supporting_evidence_ids": sorted({evidence_id for result in results if result["outcome"] == "pass" for evidence_id in result["used_evidence_ids"]}),
        "comparison_evidence_ids": sorted(set(request.get("comparison_evidence_ids", []))),
        "conflicting_evidence_ids": conflicts,
        "missing_evidence": missing,
        "transition_valid": transition_valid,
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
