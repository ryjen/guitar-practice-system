#!/usr/bin/env python3
"""Create deterministic v2 practice schedule proposals from normalized explicit state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CONTRACT_VERSION = "scheduling/v2"
PROGRESSION_STATES = {
    "discovered",
    "developing",
    "reliable-isolation",
    "reliable-context",
    "maintained",
    "paused",
    "retired",
}
DEVELOPMENT_STATES = {
    "discovered",
    "developing",
    "reliable-isolation",
    "reliable-context",
}


class SchedulingError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    item_id: str
    work_kind: str
    tier: int
    goal_priority: int
    work_priority: int
    target_minutes: int
    min_recovery_hours: int
    missed: bool
    due_state: str
    overdue_days: int
    reasons: tuple[str, ...]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise SchedulingError(f"{field} must be a non-empty string of at most 256 characters")
    return value.strip()


def require_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SchedulingError(f"{field} must be an integer between {minimum} and {maximum}")
    return value


def require_string_list(value: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise SchedulingError(f"{field} must be a list")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(require_id(item, f"{field}[{index}]"))
    if len(result) != len(set(result)):
        raise SchedulingError(f"{field} must not contain duplicates")
    return result


def parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise SchedulingError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SchedulingError(f"{field} must be an ISO date string") from error


def parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise SchedulingError(f"{field} must be an ISO datetime string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SchedulingError(f"{field} must be an ISO datetime string") from error
    if result.tzinfo is None:
        raise SchedulingError(f"{field} must include a timezone offset")
    return result


def validate_constraints(constraints: Any) -> dict[str, Any]:
    if not isinstance(constraints, dict):
        raise SchedulingError("constraints must be an object")
    session_minutes = require_int(constraints.get("session_minutes"), "constraints.session_minutes", 1, 240)
    minimum_block = require_int(constraints.get("minimum_block_minutes"), "constraints.minimum_block_minutes", 1, 60)
    if minimum_block > session_minutes:
        raise SchedulingError("minimum_block_minutes cannot exceed session_minutes")
    require_int(constraints.get("max_active_items"), "constraints.max_active_items", 0, 20)
    if constraints.get("self_reported_load") not in {"normal", "high"}:
        raise SchedulingError("constraints.self_reported_load must be normal or high")
    require_int(constraints.get("high_load_max_minutes"), "constraints.high_load_max_minutes", 1, 240)

    budget = constraints.get("weekly_budget")
    if not isinstance(budget, dict):
        raise SchedulingError("constraints.weekly_budget must be an object")
    max_sessions = require_int(budget.get("max_sessions"), "weekly_budget.max_sessions", 0, 50)
    completed_sessions = require_int(budget.get("completed_sessions"), "weekly_budget.completed_sessions", 0, 50)
    max_minutes = require_int(budget.get("max_minutes"), "weekly_budget.max_minutes", 0, 10080)
    completed_minutes = require_int(budget.get("completed_minutes"), "weekly_budget.completed_minutes", 0, 10080)
    require_int(budget.get("max_same_target"), "weekly_budget.max_same_target", 1, 50)
    if completed_sessions > max_sessions:
        raise SchedulingError("completed_sessions cannot exceed max_sessions")
    if completed_minutes > max_minutes:
        raise SchedulingError("completed_minutes cannot exceed max_minutes")
    return constraints


def validate_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise SchedulingError("snapshot must be an object")
    if snapshot.get("record_type") != "schedule-snapshot":
        raise SchedulingError("record_type must be schedule-snapshot")
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise SchedulingError(f"contract_version must be {CONTRACT_VERSION}")

    require_id(snapshot.get("snapshot_id"), "snapshot_id")
    require_int(snapshot.get("state_revision"), "state_revision", 0, 2**63 - 1)
    require_id(snapshot.get("ruleset_version"), "ruleset_version")
    generated_at = parse_datetime(snapshot.get("generated_at"), "generated_at")
    effective_date = parse_date(snapshot.get("effective_date"), "effective_date")
    timezone = require_id(snapshot.get("timezone"), "timezone")
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise SchedulingError(f"unknown timezone: {timezone}") from error
    if generated_at.astimezone(zone).date() != effective_date:
        raise SchedulingError("effective_date must match generated_at in timezone")

    constraints = validate_constraints(snapshot.get("constraints"))

    progression = snapshot.get("progression")
    if not isinstance(progression, list) or len(progression) > 256:
        raise SchedulingError("progression must be an array with at most 256 records")
    progression_by_id: dict[str, dict[str, Any]] = {}
    for index, projection in enumerate(progression):
        if not isinstance(projection, dict):
            raise SchedulingError(f"progression[{index}] must be an object")
        item_id = require_id(projection.get("item_id"), f"progression[{index}].item_id")
        if item_id in progression_by_id:
            raise SchedulingError(f"duplicate progression item: {item_id}")
        state = projection.get("state")
        if state not in PROGRESSION_STATES:
            raise SchedulingError(f"progression[{index}].state is invalid")
        require_id(projection.get("state_revision"), f"progression[{index}].state_revision")
        require_string_list(
            projection.get("supporting_assessment_proposal_ids"),
            f"progression[{index}].supporting_assessment_proposal_ids",
        )
        require_int(projection.get("weekly_count"), f"progression[{index}].weekly_count", 0, 100)
        require_string_list(projection.get("plateau_observation_ids"), f"progression[{index}].plateau_observation_ids")
        for field in ("last_meaningful_practice_date", "last_verification_date"):
            if field in projection:
                parse_date(projection[field], f"progression[{index}].{field}")
        if "last_practiced_at" in projection:
            parse_datetime(projection["last_practiced_at"], f"progression[{index}].last_practiced_at")
        progression_by_id[item_id] = projection

    goals = snapshot.get("goals")
    if not isinstance(goals, list) or len(goals) > 128:
        raise SchedulingError("goals must be an array with at most 128 records")
    goals_by_id: dict[str, dict[str, Any]] = {}
    for index, goal in enumerate(goals):
        if not isinstance(goal, dict):
            raise SchedulingError(f"goals[{index}] must be an object")
        goal_id = require_id(goal.get("goal_id"), f"goals[{index}].goal_id")
        if goal_id in goals_by_id:
            raise SchedulingError(f"duplicate goal: {goal_id}")
        require_int(goal.get("priority"), f"goals[{index}].priority", 0, 10000)
        if goal.get("status") not in {"active", "paused", "completed"}:
            raise SchedulingError(f"goals[{index}].status is invalid")
        targets = require_string_list(goal.get("target_item_ids"), f"goals[{index}].target_item_ids", allow_empty=False)
        unknown = sorted(set(targets) - progression_by_id.keys())
        if unknown:
            raise SchedulingError(f"goal {goal_id} references unknown items: {unknown}")
        goals_by_id[goal_id] = goal

    active_work = snapshot.get("active_work")
    if not isinstance(active_work, list) or len(active_work) > 20:
        raise SchedulingError("active_work must be an array with at most 20 records")
    if len(active_work) > constraints["max_active_items"]:
        raise SchedulingError("active_work count exceeds constraints.max_active_items")
    active_ids: set[str] = set()
    for index, work in enumerate(active_work):
        if not isinstance(work, dict):
            raise SchedulingError(f"active_work[{index}] must be an object")
        item_id = require_id(work.get("item_id"), f"active_work[{index}].item_id")
        if item_id in active_ids:
            raise SchedulingError(f"duplicate active work item: {item_id}")
        active_ids.add(item_id)
        projection = progression_by_id.get(item_id)
        if projection is None:
            raise SchedulingError(f"active work references unknown item: {item_id}")
        if projection["state"] not in DEVELOPMENT_STATES:
            raise SchedulingError(f"active work item {item_id} is not in a development progression state")
        goal_id = require_id(work.get("goal_id"), f"active_work[{index}].goal_id")
        goal = goals_by_id.get(goal_id)
        if goal is None:
            raise SchedulingError(f"active work {item_id} references unknown goal: {goal_id}")
        if goal["status"] != "active":
            raise SchedulingError(f"active work {item_id} references a non-active goal")
        if item_id not in goal["target_item_ids"]:
            raise SchedulingError(f"active work {item_id} is not targeted by goal {goal_id}")
        require_int(work.get("priority"), f"active_work[{index}].priority", 0, 10000)
        require_int(work.get("target_minutes"), f"active_work[{index}].target_minutes", 1, 240)
        require_int(work.get("min_recovery_hours"), f"active_work[{index}].min_recovery_hours", 0, 720)
        if not isinstance(work.get("missed"), bool):
            raise SchedulingError(f"active_work[{index}].missed must be boolean")

    maintenance_rules = snapshot.get("maintenance_rules")
    if not isinstance(maintenance_rules, list) or len(maintenance_rules) > 256:
        raise SchedulingError("maintenance_rules must be an array with at most 256 records")
    maintenance_ids: set[str] = set()
    for index, rule in enumerate(maintenance_rules):
        if not isinstance(rule, dict):
            raise SchedulingError(f"maintenance_rules[{index}] must be an object")
        item_id = require_id(rule.get("item_id"), f"maintenance_rules[{index}].item_id")
        if item_id in maintenance_ids:
            raise SchedulingError(f"duplicate maintenance rule for item: {item_id}")
        maintenance_ids.add(item_id)
        if item_id not in progression_by_id:
            raise SchedulingError(f"maintenance rule references unknown item: {item_id}")
        require_int(rule.get("interval_days"), f"maintenance_rules[{index}].interval_days", 1, 3650)
        require_int(rule.get("priority"), f"maintenance_rules[{index}].priority", 0, 10000)
        require_int(rule.get("target_minutes"), f"maintenance_rules[{index}].target_minutes", 1, 240)
        require_int(rule.get("min_recovery_hours"), f"maintenance_rules[{index}].min_recovery_hours", 0, 720)

    dependencies = snapshot.get("dependencies")
    if not isinstance(dependencies, list) or len(dependencies) > 512:
        raise SchedulingError("dependencies must be an array with at most 512 records")
    dependency_keys: set[tuple[str, str]] = set()
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise SchedulingError(f"dependencies[{index}] must be an object")
        item_id = require_id(dependency.get("item_id"), f"dependencies[{index}].item_id")
        requires_id = require_id(dependency.get("requires_item_id"), f"dependencies[{index}].requires_item_id")
        if item_id == requires_id:
            raise SchedulingError(f"item {item_id} cannot depend on itself")
        if item_id not in progression_by_id or requires_id not in progression_by_id:
            raise SchedulingError("dependency references an unknown progression item")
        key = (item_id, requires_id)
        if key in dependency_keys:
            raise SchedulingError(f"duplicate dependency: {item_id} -> {requires_id}")
        dependency_keys.add(key)
        states = dependency.get("satisfied_states")
        if not isinstance(states, list) or not states or any(state not in PROGRESSION_STATES for state in states):
            raise SchedulingError(f"dependencies[{index}].satisfied_states is invalid")
        if len(states) != len(set(states)):
            raise SchedulingError(f"dependencies[{index}].satisfied_states contains duplicates")

    return snapshot


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def dependencies_satisfied(
    item_id: str,
    dependencies_by_item: dict[str, list[dict[str, Any]]],
    progression_by_id: dict[str, dict[str, Any]],
) -> bool:
    for dependency in dependencies_by_item.get(item_id, []):
        required = progression_by_id[dependency["requires_item_id"]]
        if required["state"] not in dependency["satisfied_states"]:
            return False
    return True


def in_recovery(
    projection: dict[str, Any],
    min_recovery_hours: int,
    generated_at: datetime,
    high_load: bool,
) -> bool:
    if high_load:
        min_recovery_hours *= 2
    last_practiced = projection.get("last_practiced_at")
    if not last_practiced or min_recovery_hours <= 0:
        return False
    previous = parse_datetime(last_practiced, f"{projection['item_id']}.last_practiced_at")
    return generated_at < previous + timedelta(hours=min_recovery_hours)


def maintenance_due(projection: dict[str, Any], rule: dict[str, Any], effective: date) -> tuple[str, int]:
    last_verified = projection.get("last_verification_date")
    if last_verified is None:
        return "due", 0
    due_date = parse_date(last_verified, f"{projection['item_id']}.last_verification_date") + timedelta(days=rule["interval_days"])
    if effective < due_date:
        return "not-due", 0
    return "due", (effective - due_date).days


def classify(snapshot: dict[str, Any]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    progression_by_id = {entry["item_id"]: entry for entry in snapshot["progression"]}
    goals_by_id = {entry["goal_id"]: entry for entry in snapshot["goals"]}
    active_by_id = {entry["item_id"]: entry for entry in snapshot["active_work"]}
    maintenance_by_id = {entry["item_id"]: entry for entry in snapshot["maintenance_rules"]}
    dependencies_by_item: dict[str, list[dict[str, Any]]] = {}
    for dependency in snapshot["dependencies"]:
        dependencies_by_item.setdefault(dependency["item_id"], []).append(dependency)

    constraints = snapshot["constraints"]
    budget = constraints["weekly_budget"]
    max_same_target = budget["max_same_target"]
    generated_at = parse_datetime(snapshot["generated_at"], "generated_at")
    effective = parse_date(snapshot["effective_date"], "effective_date")
    high_load = constraints["self_reported_load"] == "high"

    candidates: list[Candidate] = []
    excluded: list[dict[str, Any]] = []

    for item_id in sorted(progression_by_id):
        projection = progression_by_id[item_id]
        state = projection["state"]

        if state == "paused":
            excluded.append({"item_id": item_id, "reason_codes": ["paused"]})
            continue
        if state == "retired":
            excluded.append({"item_id": item_id, "reason_codes": ["retired"]})
            continue

        if state == "maintained":
            rule = maintenance_by_id.get(item_id)
            if rule is None:
                excluded.append({"item_id": item_id, "reason_codes": ["maintenance-rule-missing"]})
                continue
            if not dependencies_satisfied(item_id, dependencies_by_item, progression_by_id):
                excluded.append({"item_id": item_id, "reason_codes": ["prerequisite-blocked"]})
                continue
            if projection["weekly_count"] >= max_same_target:
                excluded.append({"item_id": item_id, "reason_codes": ["weekly-repetition-cap"]})
                continue
            if in_recovery(projection, rule["min_recovery_hours"], generated_at, high_load):
                excluded.append({"item_id": item_id, "reason_codes": ["recovery-window"]})
                continue
            due_state, overdue_days = maintenance_due(projection, rule, effective)
            if due_state == "not-due":
                excluded.append({"item_id": item_id, "reason_codes": ["maintenance-not-due"]})
                continue
            candidates.append(Candidate(
                item_id=item_id,
                work_kind="maintenance",
                tier=0,
                goal_priority=0,
                work_priority=rule["priority"],
                target_minutes=rule["target_minutes"],
                min_recovery_hours=rule["min_recovery_hours"],
                missed=False,
                due_state=due_state,
                overdue_days=overdue_days,
                reasons=("maintenance-due",),
            ))
            continue

        work = active_by_id.get(item_id)
        if work is None:
            excluded.append({"item_id": item_id, "reason_codes": ["not-active-work"]})
            continue
        if not dependencies_satisfied(item_id, dependencies_by_item, progression_by_id):
            excluded.append({"item_id": item_id, "reason_codes": ["prerequisite-blocked"]})
            continue
        if projection["weekly_count"] >= max_same_target:
            excluded.append({"item_id": item_id, "reason_codes": ["weekly-repetition-cap"]})
            continue
        if in_recovery(projection, work["min_recovery_hours"], generated_at, high_load):
            excluded.append({"item_id": item_id, "reason_codes": ["recovery-window"]})
            continue

        goal = goals_by_id[work["goal_id"]]
        candidates.append(Candidate(
            item_id=item_id,
            work_kind="development",
            tier=1 if work["missed"] else 2,
            goal_priority=goal["priority"],
            work_priority=work["priority"],
            target_minutes=work["target_minutes"],
            min_recovery_hours=work["min_recovery_hours"],
            missed=work["missed"],
            due_state="not-applicable",
            overdue_days=0,
            reasons=("missed-session-recovery",) if work["missed"] else ("active-work-priority",),
        ))

    candidates.sort(key=lambda candidate: (
        candidate.tier,
        -candidate.overdue_days if candidate.tier == 0 else 0,
        candidate.goal_priority,
        candidate.work_priority,
        candidate.item_id,
    ))
    return candidates, sorted(excluded, key=lambda entry: entry["item_id"])


def propose(snapshot: Any) -> dict[str, Any]:
    snapshot = validate_snapshot(snapshot)
    candidates, excluded = classify(snapshot)
    constraints = snapshot["constraints"]
    budget = constraints["weekly_budget"]
    conflicts: list[str] = []

    if budget["completed_sessions"] >= budget["max_sessions"]:
        conflicts.append("weekly-session-budget-exhausted")
    remaining_weekly_minutes = budget["max_minutes"] - budget["completed_minutes"]
    if remaining_weekly_minutes <= 0:
        conflicts.append("weekly-minute-budget-exhausted")

    session_limit = min(constraints["session_minutes"], max(0, remaining_weekly_minutes))
    if constraints["self_reported_load"] == "high":
        session_limit = min(session_limit, constraints["high_load_max_minutes"])
    if session_limit < constraints["minimum_block_minutes"] and not conflicts:
        conflicts.append("insufficient-session-budget")

    selected: list[dict[str, Any]] = []
    remaining = session_limit
    if conflicts:
        reason = conflicts[0]
        for candidate in candidates:
            excluded.append({"item_id": candidate.item_id, "reason_codes": [reason]})
    else:
        for candidate in candidates:
            if remaining < constraints["minimum_block_minutes"]:
                excluded.append({"item_id": candidate.item_id, "reason_codes": ["session-time-exhausted"]})
                continue
            minutes = min(candidate.target_minutes, remaining)
            if minutes < constraints["minimum_block_minutes"]:
                excluded.append({"item_id": candidate.item_id, "reason_codes": ["session-time-exhausted"]})
                continue
            reasons = list(candidate.reasons)
            if minutes < candidate.target_minutes:
                reasons.append("partial-time-allocation")
            selected.append({
                "item_id": candidate.item_id,
                "work_kind": candidate.work_kind,
                "minutes": minutes,
                "reason_codes": reasons,
                "due_state": candidate.due_state,
                "overdue_days": candidate.overdue_days,
            })
            remaining -= minutes

    excluded.sort(key=lambda entry: entry["item_id"])
    proposal_basis = {
        "snapshot_id": snapshot["snapshot_id"],
        "state_revision": snapshot["state_revision"],
        "ruleset_version": snapshot["ruleset_version"],
        "effective_date": snapshot["effective_date"],
        "selected": selected,
        "excluded": excluded,
        "conflicts": conflicts,
    }
    return {
        "record_type": "schedule-proposal",
        "contract_version": CONTRACT_VERSION,
        "proposal_id": "schedule-" + canonical_hash(proposal_basis),
        "snapshot_id": snapshot["snapshot_id"],
        "state_revision": snapshot["state_revision"],
        "ruleset_version": snapshot["ruleset_version"],
        "generated_at": snapshot["generated_at"],
        "effective_date": snapshot["effective_date"],
        "expires_after_date": snapshot["effective_date"],
        "status": "complete" if selected else "no-op",
        "selected": selected,
        "excluded": excluded,
        "conflicts": conflicts,
        "requires_approval": True,
    }


def approval_status(proposal: Any, current_snapshot: Any) -> dict[str, Any]:
    if not isinstance(proposal, dict) or proposal.get("record_type") != "schedule-proposal":
        raise SchedulingError("proposal must be a schedule-proposal")
    if proposal.get("contract_version") != CONTRACT_VERSION:
        raise SchedulingError(f"proposal contract_version must be {CONTRACT_VERSION}")
    current = validate_snapshot(current_snapshot)
    reasons: list[str] = []
    if proposal.get("snapshot_id") != current["snapshot_id"]:
        reasons.append("snapshot-changed")
    if proposal.get("state_revision") != current["state_revision"]:
        reasons.append("state-revision-changed")
    if proposal.get("ruleset_version") != current["ruleset_version"]:
        reasons.append("ruleset-version-changed")
    if proposal.get("effective_date") != current["effective_date"]:
        reasons.append("effective-date-changed")
    if proposal.get("status") != "complete":
        reasons.append("proposal-has-no-work")
    return {"status": "valid" if not reasons else "stale", "reasons": reasons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose_parser = subparsers.add_parser("propose")
    propose_parser.add_argument("snapshot")
    approval_parser = subparsers.add_parser("check-approval")
    approval_parser.add_argument("proposal")
    approval_parser.add_argument("current_snapshot")
    args = parser.parse_args()

    try:
        if args.command == "propose":
            result = propose(read_json(Path(args.snapshot)))
        else:
            result = approval_status(read_json(Path(args.proposal)), read_json(Path(args.current_snapshot)))
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (SchedulingError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
