#!/usr/bin/env python3
"""Project approved long-term practice state and goals from a scheduling/v1 snapshot."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEDULING_PATH = ROOT / "scripts" / "scheduling.py"
SPEC = importlib.util.spec_from_file_location("scheduling_v1", SCHEDULING_PATH)
assert SPEC is not None and SPEC.loader is not None
scheduling = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scheduling
SPEC.loader.exec_module(scheduling)


class ProjectionError(ValueError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_extensions(snapshot: dict[str, Any]) -> None:
    item_ids = {item["id"] for item in snapshot["items"]}
    for item in snapshot["items"]:
        item_id = item["id"]
        for field in ("dimension", "approved_transition_proposal_id"):
            value = item.get(field)
            if value is not None:
                scheduling.require_id(value, f"{item_id}.{field}")
        for field in ("target_realization", "maintenance_realization"):
            value = item.get(field)
            if value is not None and not isinstance(value, dict):
                raise ProjectionError(f"{item_id}.{field} must be an object")
        if "plateau_observed" in item and not isinstance(item["plateau_observed"], bool):
            raise ProjectionError(f"{item_id}.plateau_observed must be boolean")

    goals = snapshot.get("goals", [])
    if not isinstance(goals, list) or len(goals) > 256:
        raise ProjectionError("goals must be an array with at most 256 entries")
    goal_ids: set[str] = set()
    for index, goal in enumerate(goals):
        if not isinstance(goal, dict):
            raise ProjectionError(f"goals[{index}] must be an object")
        goal_id = scheduling.require_id(goal.get("id"), f"goals[{index}].id")
        if goal_id in goal_ids:
            raise ProjectionError(f"duplicate goal id: {goal_id}")
        goal_ids.add(goal_id)
        item_id = scheduling.require_id(goal.get("item_id"), f"goals[{index}].item_id")
        if item_id not in item_ids:
            raise ProjectionError(f"goal {goal_id} references unknown item: {item_id}")
        if goal.get("period") not in {"weekly", "monthly"}:
            raise ProjectionError(f"goal {goal_id} period must be weekly or monthly")
        target = scheduling.require_int(goal.get("target_sessions"), f"goals[{index}].target_sessions", 1, 1000)
        completed = scheduling.require_int(goal.get("completed_sessions"), f"goals[{index}].completed_sessions", 0, 1000)
        if completed > target:
            raise ProjectionError(f"goal {goal_id} completed_sessions cannot exceed target_sessions")


def project(snapshot: Any) -> dict[str, Any]:
    snapshot = scheduling.validate_snapshot(snapshot)
    validate_extensions(snapshot)
    effective = scheduling.parse_date(snapshot["effective_date"], "effective_date")
    state_by_id = {item["id"]: item["state"] for item in snapshot["items"]}

    items = []
    for item in sorted(snapshot["items"], key=lambda entry: entry["id"]):
        due_state, overdue_days = scheduling.maintenance_due(item, effective)
        blocked = not scheduling.prerequisites_satisfied(item, state_by_id)
        value = {
            "item_id": item["id"],
            "state": item["state"],
            "due_state": due_state,
            "overdue_days": overdue_days,
            "blocked": blocked,
            "paused": item["state"] == "paused",
            "retired": item["state"] == "retired",
            "missed": item.get("missed", False),
            "plateau_observed": item.get("plateau_observed", False),
        }
        for field in ("dimension", "approved_transition_proposal_id", "target_realization", "maintenance_realization"):
            if field in item:
                value[field] = item[field]
        items.append(value)

    goals = []
    for goal in sorted(snapshot.get("goals", []), key=lambda entry: entry["id"]):
        remaining = goal["target_sessions"] - goal["completed_sessions"]
        goals.append({
            "goal_id": goal["id"],
            "item_id": goal["item_id"],
            "period": goal["period"],
            "target_sessions": goal["target_sessions"],
            "completed_sessions": goal["completed_sessions"],
            "remaining_sessions": remaining,
            "complete": remaining == 0,
        })

    basis = {
        "snapshot_id": snapshot["snapshot_id"],
        "state_revision": snapshot["state_revision"],
        "ruleset_version": snapshot["ruleset_version"],
        "effective_date": snapshot["effective_date"],
        "items": items,
        "goals": goals,
    }
    return {
        "record_type": "progression-projection",
        "contract_version": scheduling.CONTRACT_VERSION,
        "projection_id": "projection-" + scheduling.canonical_hash(basis),
        "snapshot_id": snapshot["snapshot_id"],
        "state_revision": snapshot["state_revision"],
        "ruleset_version": snapshot["ruleset_version"],
        "generated_at": snapshot["generated_at"],
        "effective_date": snapshot["effective_date"],
        "items": items,
        "goals": goals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    args = parser.parse_args()
    try:
        json.dump(project(read_json(Path(args.snapshot))), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (ProjectionError, scheduling.SchedulingError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
