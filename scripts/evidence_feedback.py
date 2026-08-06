#!/usr/bin/env python3
"""Validate practice evidence and derive advisory feedback without mutating state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

EVIDENCE_TYPES = {"baseline", "isolated-check", "musical-context", "full-take", "maintenance"}
TARGET_TYPES = {"technique", "song", "song-section", "exercise", "practice-session"}
PRIVACY = {"private", "local", "public"}
OBSERVATION_FIELDS = {
    "timing", "intonation", "articulation_muting", "dynamics", "phrasing_space",
    "physical_tension", "consistency", "recovery",
}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class EvidenceError(ValueError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field} must be a non-empty string")
    return value.strip()


def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(nonempty(value, field))
    except ValueError as error:
        raise EvidenceError(f"{field} must be an ISO date") from error


def validate_media_reference(value: Any) -> None:
    reference = nonempty(value, "media_reference")
    lowered = reference.lower()
    forbidden = ("token=", "signature=", "x-amz-signature", "password=", "secret=")
    if any(part in lowered for part in forbidden):
        raise EvidenceError("media_reference appears to contain a credential or signed token")
    if reference.startswith(("/home/", "/Users/", "file:///home/", "file:///Users/")):
        raise EvidenceError("media_reference must not expose a personal absolute home path")


def validate_record(record: dict[str, Any]) -> None:
    if not isinstance(record, dict) or record.get("version") != 1:
        raise EvidenceError("record must be an object with version 1")
    record_id = nonempty(record.get("id"), "id")
    if not ID_RE.fullmatch(record_id):
        raise EvidenceError("id must be lowercase kebab-case")
    parse_date(record.get("date"), "date")
    if record.get("target_type") not in TARGET_TYPES:
        raise EvidenceError("unsupported target_type")
    nonempty(record.get("target_id"), "target_id")
    if record.get("evidence_type") not in EVIDENCE_TYPES:
        raise EvidenceError("unsupported evidence_type")
    if record.get("privacy") not in PRIVACY:
        raise EvidenceError("privacy must be private, local, or public")
    validate_media_reference(record.get("media_reference"))

    context = record.get("context", {})
    if not isinstance(context, dict):
        raise EvidenceError("context must be an object")
    tempo = context.get("tempo_bpm")
    if tempo is not None and (isinstance(tempo, bool) or not isinstance(tempo, int) or not 20 <= tempo <= 300):
        raise EvidenceError("context.tempo_bpm must be null or between 20 and 300")

    observations = record.get("observations", {})
    if not isinstance(observations, dict) or set(observations) - OBSERVATION_FIELDS:
        raise EvidenceError("observations contains unsupported fields")
    for field, value in observations.items():
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise EvidenceError(f"observations.{field} must be null or a non-empty string")

    nonempty(record.get("largest_audible_defect"), "largest_audible_defect")
    nonempty(record.get("next_action"), "next_action")
    gates = record.get("quality_gates_checked", [])
    if not isinstance(gates, list) or not all(isinstance(item, str) and item.strip() for item in gates):
        raise EvidenceError("quality_gates_checked must be a list of non-empty strings")
    regression = record.get("regression_observed", False)
    if not isinstance(regression, bool):
        raise EvidenceError("regression_observed must be boolean")
    comparison = record.get("comparison_evidence_id")
    if regression and not isinstance(comparison, str):
        raise EvidenceError("regression requires comparison_evidence_id")
    interval = record.get("maintenance_interval_days")
    if interval is not None and (isinstance(interval, bool) or not isinstance(interval, int) or not 1 <= interval <= 365):
        raise EvidenceError("maintenance_interval_days must be null or between 1 and 365")


def summarize(records: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    if not isinstance(records, list) or not records:
        raise EvidenceError("records must be a non-empty list")
    for record in records:
        validate_record(record)

    records = sorted(records, key=lambda item: (item["target_id"], item["date"], item["id"]))
    targets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        targets.setdefault(record["target_id"], []).append(record)

    feedback = []
    for target_id, history in sorted(targets.items()):
        latest = history[-1]
        kinds = {item["evidence_type"] for item in history}
        interval = latest.get("maintenance_interval_days")
        age_days = (as_of - parse_date(latest["date"], "date")).days
        maintenance = "unknown"
        if interval is not None:
            maintenance = "due" if age_days >= interval else "not-due"
        eligible = (
            "isolated-check" in kinds
            and bool(kinds & {"musical-context", "full-take"})
            and bool(latest.get("quality_gates_checked"))
            and "tension" not in latest["largest_audible_defect"].lower()
        )
        feedback.append({
            "target_id": target_id,
            "latest_evidence_id": latest["id"],
            "largest_audible_defect": latest["largest_audible_defect"],
            "next_action": latest["next_action"],
            "maintenance_status": maintenance,
            "regression_observed": latest.get("regression_observed", False),
            "reliability_eligible": eligible,
            "requires_approval": True,
            "warnings": ([] if latest.get("media_reference") != "none" else ["No retained media reference; observations cannot be independently replayed."]),
        })
    return {
        "status": "complete",
        "as_of": as_of.isoformat(),
        "advisory": True,
        "targets": feedback,
        "prohibited_mutations": ["progress", "reliability", "mastery", "maintenance state", "active-work state"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records")
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args()
    try:
        payload = read_json(Path(args.records))
        records = payload.get("records") if isinstance(payload, dict) else payload
        result = summarize(records, parse_date(args.as_of, "as_of"))
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (EvidenceError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
