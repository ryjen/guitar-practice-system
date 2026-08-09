#!/usr/bin/env python3
"""Create deterministic practice schedule proposals from explicit versioned state."""

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

CONTRACT_VERSION = "scheduling/v1"
VALID_STATES = {"candidate", "active", "verified", "maintenance", "paused", "retired"}


class SchedulingError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    item: dict[str, Any]
    tier: int
    overdue_days: int
    due_state: str
    reasons: tuple[str, ...]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def require_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SchedulingError(f"{field} must be an integer between {minimum} and {maximum}")
    return value


def require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise SchedulingError(f"{field} must be a non-empty string of at most 256 characters")
    return value.strip()


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

    session_minutes = require_int(snapshot.get("session_minutes"), "session_minutes", 1, 240)
    minimum_block = require_int(snapshot.get("minimum_block_minutes"), "minimum_block_minutes", 1, 60)
    if minimum_block > session_minutes:
        raise SchedulingError("minimum_block_minutes cannot exceed session_minutes")
    max_active = require_int(snapshot.get("max_active_items"), "max_active_items", 0, 20)
    load = snapshot.get("self_reported_load")
    if load not in {"normal", "high"}:
        raise SchedulingError("self_reported_load must be normal or high")
    require_int(snapshot.get("high_load_max_minutes"), "high_load_max_minutes", 1, 240)

    budget = snapshot.get("weekly_budget")
    if not isinstance(budget, dict):
        raise SchedulingError("weekly_budget must be an object")
    max_sessions = require_int(budget.get("max_sessions"), "weekly_budget.max_sessions", 0, 50)
    completed_sessions = require_int(budget.get("completed_sessions"), "weekly_budget.completed_sessions", 0, 50)
    max_minutes = require_int(budget.get("max_minutes"), "weekly_budget.max_minutes", 0, 10080)
    completed_minutes = require_int(budget.get("completed_minutes"), "weekly_budget.completed_minutes", 0, 10080)
    require_int(budget.get("max_same_target"), "weekly_budget.max_same_target", 1, 50)
    if completed_sessions > max_sessions:
        raise SchedulingError("completed_sessions cannot exceed max_sessions")
    if completed_minutes > max_minutes:
        raise SchedulingError("completed_minutes cannot exceed max_minutes")

    items = snapshot.get("items")
    if not isinstance(items, list) or len(items) > 256:
        raise SchedulingError("items must be an array with at most 256 entries")

    ids: set[str] = set()
    active_count = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SchedulingError(f"items[{index}] must be an object")
        item_id = require_id(item.get("id"), f"items[{index}].id")
        if item_id in ids:
            raise SchedulingError(f"duplicate item id: {item_id}")
        ids.add(item_id)
        state = item.get("state")
        if state not in VALID_STATES:
            raise SchedulingError(f"items[{index}].state is invalid")
        if state == "active":
            active_count += 1
        require_int(item.get("priority"), f"items[{index}].priority", 0, 10000)
        require_int(item.get("target_minutes"), f"items[{index}].target_minutes", 1, 240)
        require_int(item.get("weekly_count", 0), f"items[{index}].weekly_count", 0, 100)
        require_int(item.get("min_recovery_hours", 0), f"items[{index}].min_recovery_hours", 0, 720)
        if "maintenance_interval_days" in item:
            require_int(item["maintenance_interval_days"], f"items[{index}].maintenance_interval_days", 1, 3650)
        if "last_verified_date" in item:
            parse_date(item["last_verified_date"], f"items[{index}].last_verified_date")
        if "last_practiced_at" in item:
            parse_datetime(item["last_practiced_at"], f"items[{index}].last_practiced_at")
        if "missed" in item and not isinstance(item["missed"], bool):
            raise SchedulingError(f"items[{index}].missed must be boolean")
        prerequisites = item.get("prerequisites")
        if not isinstance(prerequisites, list) or len(prerequisites) > 64:
            raise SchedulingError(f"items[{index}].prerequisites must be an array")
        for p_index, prerequisite in enumerate(prerequisites):
            if not isinstance(prerequisite, dict):
                raise SchedulingError(f"items[{index}].prerequisites[{p_index}] must be an object")
            required_id = require_id(prerequisite.get("item_id"), f"items[{index}].prerequisites[{p_index}].item_id")
            if required_id == item_id:
                raise SchedulingError(f"item {item_id} cannot depend on itself")
            states = prerequisite.get("satisfied_states")
            if not isinstance(states, list) or not states or any(state not in VALID_STATES for state in states):
                raise SchedulingError(f"items[{index}].prerequisites[{p_index}].satisfied_states is invalid")

    if active_count > max_active:
        raise SchedulingError("active item count exceeds max_active_items")

    for item in items:
        for prerequisite in item["prerequisites"]:
            if prerequisite["item_id"] not in ids:
                raise SchedulingError(f"unknown prerequisite item: {prerequisite['item_id']}")

    return snapshot


def maintenance_due(item: dict[str, Any], effective: date) -> tuple[str, int]:
    interval = item.get("maintenance_interval_days")
    if interval is None:
        if item["state"] == "maintenance":
            return "due", 0
        return "not-applicable", 0
    last_verified = item.get("last_verified_date")
    if last_verified is None:
        return "due", 0
    due_date = parse_date(last_verified, f"{item['id']}.last_verified_date") + timedelta(days=interval)
    if effective < due_date:
        return "not-due", 0
    return "due", (effective - due_date).days


def prerequisites_satisfied(item: dict[str, Any], state_by_id: dict[str, str]) -> bool:
    for prerequisite in item["prerequisites"]:
        if state_by_id[prerequisite["item_id"]] not in prerequisite["satisfied_states"]:
            return False
    return True


def in_recovery(item: dict[str, Any], generated_at: datetime, high_load: bool) -> bool:
    last_practiced = item.get("last_practiced_at")
    recovery_hours = item.get("min_recovery_hours", 0)
    if high_load:
        recovery_hours *= 2
    if not last_practiced or recovery_hours <= 0:
        return False
    previous = parse_datetime(last_practiced, f"{item['id']}.last_practiced_at")
    return generated_at < previous + timedelta(hours=recovery_hours)


def classify(snapshot: dict[str, Any]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    items = snapshot["items"]
    state_by_id = {item["id"]: item["state"] for item in items}
    effective = parse_date(snapshot["effective_date"], "effective_date")
    generated_at = parse_datetime(snapshot["generated_at"], "generated_at")
    high_load = snapshot["self_reported_load"] == "high"
    max_same_target = snapshot["weekly_budget"]["max_same_target"]
    candidates: list[Candidate] = []
    excluded: list[dict[str, Any]] = []

    for item in items:
        reasons: list[str] = []
        state = item["state"]
        if state == "paused":
            excluded.append({"item_id": item["id"], "reason_codes": ["paused"]})
            continue
        if state == "retired":
            excluded.append({"item_id": item["id"], "reason_codes": ["retired"]})
            continue
        if not prerequisites_satisfied(item, state_by_id):
            excluded.append({"item_id": item["id"], "reason_codes": ["prerequisite-blocked"]})
            continue
        if item.get("weekly_count", 0) >= max_same_target:
            excluded.append({"item_id": item["id"], "reason_codes": ["weekly-repetition-cap"]})
            continue
        if in_recovery(item, generated_at, high_load):
            excluded.append({"item_id": item["id"], "reason_codes": ["recovery-window"]})
            continue

        due_state, overdue_days = maintenance_due(item, effective)
        if due_state == "due" and state in {"maintenance", "verified"}:
            reasons.append("maintenance-due")
            candidates.append(Candidate(item, 0, overdue_days, due_state, tuple(reasons)))
            continue
        if state == "maintenance":
            excluded.append({"item_id": item["id"], "reason_codes": ["maintenance-not-due"]})
            continue
        if state == "verified":
            excluded.append({"item_id": item["id"], "reason_codes": ["no-work-due"]})
            continue
        if item.get("missed", False):
            reasons.append("missed-session-recovery")
            candidates.append(Candidate(item, 1, overdue_days, due_state, tuple(reasons)))
            continue
        if state == "active":
            reasons.append("active-priority")
            candidates.append(Candidate(item, 2, overdue_days, due_state, tuple(reasons)))
            continue
        if state == "candidate":
            reasons.append("candidate-priority")
            candidates.append(Candidate(item, 3, overdue_days, due_state, tuple(reasons)))
            continue
        raise SchedulingError(f"unhandled item state: {state}")

    candidates.sort(key=lambda candidate: (
        candidate.tier,
        -candidate.overdue_days if candidate.tier == 0 else 0,
        candidate.item["priority"],
        candidate.item["id"],
    ))
    excluded.sort(key=lambda entry: entry["item_id"])
    return candidates, excluded


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def propose(snapshot: Any) -> dict[str, Any]:
    snapshot = validate_snapshot(snapshot)
    candidates, excluded = classify(snapshot)
    budget = snapshot["weekly_budget"]
    conflicts: list[str] = []

    if budget["completed_sessions"] >= budget["max_sessions"]:
        conflicts.append("weekly-session-budget-exhausted")
    remaining_weekly_minutes = budget["max_minutes"] - budget["completed_minutes"]
    if remaining_weekly_minutes <= 0:
        conflicts.append("weekly-minute-budget-exhausted")

    session_limit = min(snapshot["session_minutes"], max(0, remaining_weekly_minutes))
    if snapshot["self_reported_load"] == "high":
        session_limit = min(session_limit, snapshot["high_load_max_minutes"])
    if session_limit < snapshot["minimum_block_minutes"] and not conflicts:
        conflicts.append("insufficient-session-budget")

    selected: list[dict[str, Any]] = []
    active_count = sum(1 for item in snapshot["items"] if item["state"] == "active")
    candidate_slots = snapshot["max_active_items"] - active_count
    remaining = session_limit

    if not conflicts:
        for candidate in candidates:
            item = candidate.item
            if item["state"] == "candidate":
                if candidate_slots <= 0:
                    excluded.append({"item_id": item["id"], "reason_codes": ["active-capacity-full"]})
                    continue
            if remaining < snapshot["minimum_block_minutes"]:
                excluded.append({"item_id": item["id"], "reason_codes": ["session-time-exhausted"]})
                continue
            minutes = min(item["target_minutes"], remaining)
            if minutes < snapshot["minimum_block_minutes"]:
                excluded.append({"item_id": item["id"], "reason_codes": ["session-time-exhausted"]})
                continue
            reasons = list(candidate.reasons)
            if minutes < item["target_minutes"]:
                reasons.append("partial-time-allocation")
            selected.append({
                "item_id": item["id"],
                "minutes": minutes,
                "reason_codes": reasons,
                "due_state": candidate.due_state,
                "overdue_days": candidate.overdue_days,
            })
            remaining -= minutes
            if item["state"] == "candidate":
                candidate_slots -= 1
    else:
        budget_reason = conflicts[0]
        for candidate in candidates:
            excluded.append({"item_id": candidate.item["id"], "reason_codes": [budget_reason]})

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
