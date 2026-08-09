#!/usr/bin/env python3
"""Generate deterministic practice schedule proposals from explicit state snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

STATES = {"discovered", "developing", "reliable-isolation", "reliable-context", "maintained", "paused", "retired"}
LOADS = {"normal", "high"}

class SchedulingError(ValueError):
    pass

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchedulingError(f"{field} must be a non-empty string")
    return value.strip()

def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(nonempty(value, field))
    except ValueError as error:
        raise SchedulingError(f"{field} must be an ISO date") from error

def parse_datetime(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(nonempty(value, field))
    except ValueError as error:
        raise SchedulingError(f"{field} must be an ISO datetime") from error
    if parsed.tzinfo is None:
        raise SchedulingError(f"{field} must include a UTC offset")
    return parsed

def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]

def week_bounds(day: date, week_start: int) -> tuple[date, date]:
    start = day - timedelta(days=(day.weekday() - week_start) % 7)
    return start, start + timedelta(days=6)

def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        raise SchedulingError("snapshot must be an object with version 1")
    nonempty(snapshot.get("snapshot_version"), "snapshot_version")
    nonempty(snapshot.get("ruleset_version"), "ruleset_version")
    parse_datetime(snapshot.get("generated_at"), "generated_at")
    effective = parse_date(snapshot.get("effective_date"), "effective_date")
    nonempty(snapshot.get("timezone"), "timezone")
    week_start = snapshot.get("week_start", 0)
    if isinstance(week_start, bool) or not isinstance(week_start, int) or not 0 <= week_start <= 6:
        raise SchedulingError("week_start must be 0..6 (Monday..Sunday)")
    constraints = snapshot.get("constraints")
    if not isinstance(constraints, dict):
        raise SchedulingError("constraints must be an object")
    for field, low, high in (("max_active_items", 1, 12), ("weekly_session_budget", 1, 21), ("weekly_minute_budget", 5, 2000), ("default_session_minutes", 5, 240), ("recovery_days", 0, 30), ("high_load_recovery_days", 0, 30), ("max_sessions_per_target_per_week", 1, 14)):
        value = constraints.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SchedulingError(f"constraints.{field} must be between {low} and {high}")
    items = snapshot.get("items")
    if not isinstance(items, list):
        raise SchedulingError("items must be a list")
    ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise SchedulingError("items must contain objects")
        item_id = nonempty(item.get("id"), "item.id")
        if item_id in ids:
            raise SchedulingError(f"duplicate item id: {item_id}")
        ids.add(item_id)
        if item.get("state") not in STATES:
            raise SchedulingError(f"item {item_id} has unsupported state")
        priority = item.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
            raise SchedulingError(f"item {item_id} priority must be a positive integer")
        if not isinstance(item.get("active"), bool):
            raise SchedulingError(f"item {item_id} active must be boolean")
        if item.get("state") in {"paused", "retired"} and item.get("active"):
            raise SchedulingError(f"item {item_id} cannot be active while paused or retired")
        interval = item.get("maintenance_interval_days")
        if interval is not None and (isinstance(interval, bool) or not isinstance(interval, int) or not 1 <= interval <= 365):
            raise SchedulingError(f"item {item_id} maintenance interval must be 1..365 or null")
        duration = item.get("session_minutes", constraints["default_session_minutes"])
        if isinstance(duration, bool) or not isinstance(duration, int) or not 5 <= duration <= 240:
            raise SchedulingError(f"item {item_id} session_minutes must be 5..240")
        if item.get("self_reported_load", "normal") not in LOADS:
            raise SchedulingError(f"item {item_id} has unsupported self_reported_load")
        for field in ("last_practice_date", "last_verified_date"):
            if item.get(field) is not None and parse_date(item[field], f"item.{item_id}.{field}") > effective:
                raise SchedulingError(f"item {item_id} {field} is after effective_date")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise SchedulingError(f"item {item_id} dependencies must be a list")
        for dep in dependencies:
            if not isinstance(dep, dict):
                raise SchedulingError(f"item {item_id} dependency must be an object")
            nonempty(dep.get("target_id"), "dependency.target_id")
            states = dep.get("required_states")
            if not isinstance(states, list) or not states or not all(state in STATES for state in states):
                raise SchedulingError(f"item {item_id} dependency required_states is invalid")
    unknown_deps = sorted({dep["target_id"] for item in items for dep in item.get("dependencies", [])} - ids)
    if unknown_deps:
        raise SchedulingError(f"dependencies reference unknown items: {unknown_deps}")
    history = snapshot.get("history", [])
    if not isinstance(history, list):
        raise SchedulingError("history must be a list")
    for event in history:
        if not isinstance(event, dict) or event.get("type") not in {"completed", "missed", "approved-transition", "paused", "resumed"}:
            raise SchedulingError("history contains unsupported event")
        if event.get("target_id") not in ids:
            raise SchedulingError("history target_id must reference an item")
        event_date = parse_date(event.get("date"), "history.date")
        if event_date > effective:
            raise SchedulingError("history event is after effective_date")
        if event["type"] == "completed":
            minutes = event.get("minutes")
            if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
                raise SchedulingError("completed history requires positive minutes")

def item_status(item: dict[str, Any], effective: date) -> dict[str, Any]:
    interval = item.get("maintenance_interval_days")
    verified = parse_date(item["last_verified_date"], "last_verified_date") if item.get("last_verified_date") else None
    due_date = verified + timedelta(days=interval) if interval and verified else None
    overdue_days = max(0, (effective - due_date).days) if due_date and effective >= due_date else 0
    return {"maintenance_due": bool(due_date and effective >= due_date), "maintenance_due_date": due_date.isoformat() if due_date else None, "overdue_days": overdue_days}

def dependency_blockers(item: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(dep["target_id"] for dep in item.get("dependencies", []) if by_id[dep["target_id"]]["state"] not in dep["required_states"])

def propose(snapshot: dict[str, Any]) -> dict[str, Any]:
    validate_snapshot(snapshot)
    effective = parse_date(snapshot["effective_date"], "effective_date")
    constraints = snapshot["constraints"]
    items = snapshot["items"]
    by_id = {item["id"]: item for item in items}
    week_start, week_end = week_bounds(effective, snapshot.get("week_start", 0))
    completed = [event for event in snapshot.get("history", []) if event["type"] == "completed" and week_start <= parse_date(event["date"], "history.date") <= week_end]
    missed = {event["target_id"] for event in snapshot.get("history", []) if event["type"] == "missed" and week_start <= parse_date(event["date"], "history.date") <= effective}
    per_target = {item["id"]: 0 for item in items}
    for event in completed:
        per_target[event["target_id"]] += 1
    remaining_sessions = max(0, constraints["weekly_session_budget"] - len(completed))
    remaining_minutes = max(0, constraints["weekly_minute_budget"] - sum(event["minutes"] for event in completed))
    active_count = sum(1 for item in items if item["active"] and item["state"] not in {"paused", "retired"})
    status_rows: list[dict[str, Any]] = []
    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for item in items:
        status = item_status(item, effective)
        blockers = dependency_blockers(item, by_id)
        reasons: list[str] = []
        eligible = True
        if item["state"] in {"paused", "retired"}:
            eligible = False; reasons.append(item["state"])
        if blockers:
            eligible = False; reasons.append("blocked-by:" + ",".join(blockers))
        last_practice = parse_date(item["last_practice_date"], "last_practice_date") if item.get("last_practice_date") else None
        recovery = constraints["high_load_recovery_days"] if item.get("self_reported_load", "normal") == "high" else constraints["recovery_days"]
        if last_practice and (effective - last_practice).days < recovery:
            eligible = False; reasons.append("recovery-window")
        if per_target[item["id"]] >= constraints["max_sessions_per_target_per_week"]:
            eligible = False; reasons.append("weekly-repeat-limit")
        if not item["active"] and not status["maintenance_due"] and active_count >= constraints["max_active_items"]:
            eligible = False; reasons.append("active-capacity-full")
        catch_up = item["id"] in missed
        age = (effective - last_practice).days if last_practice else 999999
        rank = (0 if status["maintenance_due"] else 1, 0 if catch_up else 1, item["priority"], -status["overdue_days"], -age, item["id"])
        row = {"target_id": item["id"], **status, "catch_up": catch_up, "eligible": eligible, "blockers": blockers, "reasons": reasons, "rank_key": list(rank)}
        status_rows.append(row)
        if eligible:
            candidates.append((rank, item))
    selected: list[dict[str, Any]] = []
    for _, item in sorted(candidates, key=lambda pair: pair[0]):
        if remaining_sessions <= 0:
            break
        minutes = item.get("session_minutes", constraints["default_session_minutes"])
        if minutes > remaining_minutes:
            continue
        selected.append({"target_id": item["id"], "minutes": minutes, "reason": next(row for row in status_rows if row["target_id"] == item["id"])["reasons"], "maintenance_due": item_status(item, effective)["maintenance_due"], "catch_up": item["id"] in missed})
        remaining_sessions -= 1
        remaining_minutes -= minutes
    selected_ids = {item["target_id"] for item in selected}
    excluded = [{"target_id": row["target_id"], "reasons": row["reasons"] or ["lower-deterministic-rank-or-budget"]} for row in status_rows if row["target_id"] not in selected_ids]
    fingerprint_input = {"snapshot": snapshot, "selected": selected, "excluded": excluded}
    proposal_id = f"schedule-{snapshot['effective_date']}-{stable_hash(fingerprint_input)}"
    return {"version": 1, "proposal_id": proposal_id, "snapshot_version": snapshot["snapshot_version"], "ruleset_version": snapshot["ruleset_version"], "generated_at": snapshot["generated_at"], "effective_date": snapshot["effective_date"], "timezone": snapshot["timezone"], "week": {"start": week_start.isoformat(), "end": week_end.isoformat()}, "selected": selected, "excluded": excluded, "projection": sorted(status_rows, key=lambda row: row["target_id"]), "remaining_budget": {"sessions": remaining_sessions, "minutes": remaining_minutes}, "status": "no-op" if not selected else "proposed", "requires_approval": True, "application_key": f"{proposal_id}:{snapshot['snapshot_version']}", "stale_when_snapshot_version_changes": True, "input_fingerprint": stable_hash(snapshot)}

def application_status(proposal: dict[str, Any], current_snapshot_version: str, applied_keys: list[str] | None = None) -> str:
    if proposal.get("snapshot_version") != current_snapshot_version:
        return "stale"
    if proposal.get("application_key") in set(applied_keys or []):
        return "already-applied"
    return "applicable"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    args = parser.parse_args()
    try:
        json.dump(propose(read_json(Path(args.snapshot))), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (SchedulingError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
