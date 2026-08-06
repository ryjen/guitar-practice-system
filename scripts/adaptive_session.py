#!/usr/bin/env python3
"""Generate advisory practice-session recommendations from explicit context."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

DURATIONS = {15, 30, 45, 60}
ENVIRONMENTS = {"normal", "quiet", "headphones", "acoustic-only", "no-computer"}
BLOCK_TYPES = {"warmup", "technique", "theory", "application", "evidence"}


class SessionError(ValueError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SessionError(f"{field} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def validate_request(request: dict[str, Any]) -> None:
    if not isinstance(request, dict):
        raise SessionError("request must be an object")
    duration = request.get("duration_minutes")
    if isinstance(duration, bool) or duration not in DURATIONS:
        raise SessionError("duration_minutes must be one of 15, 30, 45, or 60")
    environment = request.get("environment", "normal")
    if environment not in ENVIRONMENTS:
        raise SessionError(f"unsupported environment: {environment!r}")
    priorities = clean_strings(request.get("priorities"), "priorities")
    maintenance = clean_strings(request.get("maintenance_due"), "maintenance_due")
    active = clean_strings(request.get("active_techniques"), "active_techniques")
    if not priorities and not maintenance and not active:
        raise SessionError("provide priorities, maintenance_due, or active_techniques")
    max_active = request.get("max_active_techniques", 3)
    if isinstance(max_active, bool) or not isinstance(max_active, int) or not 1 <= max_active <= 6:
        raise SessionError("max_active_techniques must be between 1 and 6")
    if len(active) > max_active:
        raise SessionError("active_techniques exceeds max_active_techniques")
    clean_strings(request.get("available_gear"), "available_gear")
    clean_strings(request.get("available_backing_tracks"), "available_backing_tracks")
    clean_strings(request.get("desired_genres"), "desired_genres")
    clean_strings(request.get("theory_focus"), "theory_focus")
    evidence = request.get("evidence", {})
    if not isinstance(evidence, dict):
        raise SessionError("evidence must be an object")
    for key, value in evidence.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise SessionError("evidence entries must map technique IDs to objects")
        if "largest_audible_defect" in value and not isinstance(value["largest_audible_defect"], str):
            raise SessionError("largest_audible_defect must be a string")


def fingerprint(request: dict[str, Any]) -> str:
    raw = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def allocation(duration: int) -> dict[str, int]:
    return {
        15: {"warmup": 2, "technique": 7, "application": 4, "evidence": 2},
        30: {"warmup": 4, "technique": 12, "theory": 4, "application": 7, "evidence": 3},
        45: {"warmup": 5, "technique": 18, "theory": 6, "application": 11, "evidence": 5},
        60: {"warmup": 7, "technique": 24, "theory": 8, "application": 14, "evidence": 7},
    }[duration]


def select_focus(request: dict[str, Any]) -> tuple[str, str, list[str]]:
    maintenance = clean_strings(request.get("maintenance_due"), "maintenance_due")
    priorities = clean_strings(request.get("priorities"), "priorities")
    active = clean_strings(request.get("active_techniques"), "active_techniques")
    max_active = request.get("max_active_techniques", 3)
    evidence = request.get("evidence", {})
    warnings: list[str] = []

    if len(active) >= max_active:
        blocked = [item for item in priorities if item not in active and item not in maintenance]
        priorities = [item for item in priorities if item in active or item in maintenance]
        if blocked:
            warnings.append(
                "Active-work capacity is full; skipped new priority candidates: " + ", ".join(blocked)
            )

    ordered = list(dict.fromkeys(maintenance + priorities + active))
    for technique in ordered:
        entry = evidence.get(technique, {})
        defect = entry.get("largest_audible_defect")
        if isinstance(defect, str) and defect.strip():
            return technique, f"Selected from explicit evidence: {defect.strip()}.", warnings
    if maintenance:
        return maintenance[0], "Selected because maintenance is explicitly due.", warnings
    if priorities:
        return priorities[0], "Selected from the stated priority order.", warnings
    if active:
        return active[0], "Selected from the active technique set.", warnings
    raise SessionError("active-work capacity is full and no eligible active or maintenance focus remains")


def environment_notes(environment: str) -> tuple[list[str], list[str]]:
    gear: list[str] = []
    notes: list[str] = []
    if environment == "quiet":
        notes.append("Use unplugged, very low-volume, or muted-string work; avoid feedback-dependent tasks.")
    elif environment == "headphones":
        gear.append("headphones")
        notes.append("Use direct monitoring and conservative headphone level.")
    elif environment == "acoustic-only":
        notes.append("Use acoustic or unamplified material; replace pedal-dependent application with articulation work.")
    elif environment == "no-computer":
        notes.append("Use amp, looper, metronome, or offline material only; do not require a DAW.")
    return gear, notes


def block(block_type: str, minutes: int, title: str, why: str, *, target: str | None = None,
          gear: list[str] | None = None, evidence_required: bool = False) -> dict[str, Any]:
    if block_type not in BLOCK_TYPES:
        raise SessionError(f"unsupported block type: {block_type}")
    value: dict[str, Any] = {"type": block_type, "minutes": minutes, "title": title, "why": why}
    if target:
        value["target_id"] = target
    if gear:
        value["gear"] = gear
    if evidence_required:
        value["evidence_required"] = True
    return value


def build_blocks(request: dict[str, Any], duration: int, focus: str, focus_reason: str) -> list[dict[str, Any]]:
    split = allocation(duration)
    environment = request.get("environment", "normal")
    environment_gear, _ = environment_notes(environment)
    gear = clean_strings(request.get("available_gear"), "available_gear")
    backing = clean_strings(request.get("available_backing_tracks"), "available_backing_tracks")
    desired_genres = clean_strings(request.get("desired_genres"), "desired_genres")
    theory_focus = clean_strings(request.get("theory_focus"), "theory_focus")

    blocks = [
        block("warmup", split["warmup"], "Prepare the exact movement", f"Low-fatigue preparation for {focus}.", target=focus),
        block("technique", split["technique"], f"Primary technique: {focus}", focus_reason, target=focus, gear=gear[:3]),
    ]
    if split.get("theory"):
        subject = theory_focus[0] if theory_focus else "intervals or chord tones in the application"
        blocks.append(block("theory", split["theory"], f"Connect theory: {subject}", "Theory is included only as support for the primary musical task."))

    application_title = f"Apply {focus} musically"
    if backing and environment not in {"acoustic-only", "quiet", "no-computer"}:
        application_title = f"Apply over {backing[0]}"
    elif desired_genres:
        application_title += f" in {desired_genres[0]} vocabulary"
    blocks.append(block(
        "application",
        split["application"],
        application_title,
        "Use available accompaniment or a constrained creative fragment so isolated control transfers to musical context.",
        target=focus,
        gear=environment_gear,
    ))
    blocks.append(block(
        "evidence",
        split["evidence"],
        "Capture one short evidence take",
        "Record or note only what is needed to identify the next audible defect; this does not update progress automatically.",
        target=focus,
        evidence_required=True,
    ))
    return blocks


def recommend(request: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    duration = request["duration_minutes"]
    focus, focus_reason, warnings = select_focus(request)
    environment = request.get("environment", "normal")
    _, environment_guidance = environment_notes(environment)
    blocks = build_blocks(request, duration, focus, focus_reason)

    fallback_duration = {15: 15, 30: 15, 45: 30, 60: 30}[duration]
    fallback_blocks = build_blocks(request, fallback_duration, focus, focus_reason)
    if not request.get("evidence", {}).get(focus):
        warnings.append(f"No evidence supplied for {focus}; recommendation uses stated priorities and does not claim a weakness.")
    if environment == "acoustic-only" and ("wah" in focus.lower() or "ebow" in focus.lower()):
        warnings.append("The selected focus depends on electric capability; use the block as mechanics/phrasing preparation or choose another approved focus.")

    return {
        "status": "complete",
        "recommendation_id": "session-" + fingerprint(request),
        "advisory": True,
        "requires_approval": True,
        "duration_minutes": duration,
        "environment": environment,
        "focus_technique": focus,
        "blocks": blocks,
        "environment_guidance": environment_guidance,
        "fallback": {
            "duration_minutes": fallback_duration,
            "blocks": fallback_blocks,
            "instruction": "Use this complete shorter variant; do not silently truncate the evidence block.",
        },
        "warnings": warnings,
        "prohibited_mutations": ["schedule", "progress", "mastery", "maintenance state", "active-work state", "evidence records"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    args = parser.parse_args()
    try:
        json.dump(recommend(read_json(Path(args.request))), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (SessionError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
