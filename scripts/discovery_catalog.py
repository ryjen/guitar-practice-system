#!/usr/bin/env python3
"""Deterministic local catalog search for the public practice core."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

TARGET_TYPES = {
    "song",
    "passage",
    "technique",
    "exercise",
    "warmup",
    "theory-topic",
    "backing-track",
    "gear-setup",
    "practice-session",
}
CANONICAL_GENRES = {"80s-rock", "alt-rock", "blues", "country", "jazz"}
LIST_FIELDS = {
    "genres": "genres",
    "styles": "styles",
    "techniques": "techniques",
    "gear_ids": "gear_ids",
    "roles": "roles",
}
SCALAR_FIELDS = {"tuning": "tunings", "meter": "meters", "difficulty": "difficulty"}


class DiscoveryError(ValueError):
    """Invalid request or catalog."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def token(value: str) -> str:
    return " ".join(value.strip().lower().split())


def strings(value: Any, field: str = "value") -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DiscoveryError(f"{field!r} must be a list of strings")
    return [token(item) for item in value if item.strip()]


def optional_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def text(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def validate_request(request: dict[str, Any]) -> None:
    if not isinstance(request, dict):
        raise DiscoveryError("request must be an object")
    if request.get("target_type") not in TARGET_TYPES:
        raise DiscoveryError(f"unsupported target_type: {request.get('target_type')!r}")
    if not isinstance(request.get("goal"), str) or not request["goal"].strip():
        raise DiscoveryError("goal must be a non-empty string")

    limit = request.get("limit", 5)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise DiscoveryError("limit must be between 1 and 20")

    constraints = request.get("constraints", {})
    if not isinstance(constraints, dict):
        raise DiscoveryError("constraints must be an object")

    normalized_lists: dict[str, list[str]] = {}
    for field in LIST_FIELDS:
        values = strings(constraints.get(field), f"constraints.{field}")
        normalized_lists[field] = values
        if field == "genres" and set(values) - CANONICAL_GENRES:
            raise DiscoveryError(
                f"unsupported canonical genres: {sorted(set(values) - CANONICAL_GENRES)}"
            )

    for field in SCALAR_FIELDS:
        if field in constraints and not isinstance(constraints[field], str):
            raise DiscoveryError(f"constraints.{field} must be a string")

    if "tempo_bpm" in constraints:
        tempo = constraints["tempo_bpm"]
        if not isinstance(tempo, dict):
            raise DiscoveryError("constraints.tempo_bpm must be an object")
        low, high = tempo.get("min", 20), tempo.get("max", 300)
        if (
            isinstance(low, bool)
            or isinstance(high, bool)
            or not isinstance(low, int)
            or not isinstance(high, int)
            or not 20 <= low <= high <= 300
        ):
            raise DiscoveryError("tempo_bpm must satisfy 20 <= min <= max <= 300")

    required = request.get("required_constraints", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise DiscoveryError("required_constraints must be a list of strings")

    supported = set(LIST_FIELDS) | set(SCALAR_FIELDS) | {"tempo_bpm"}
    if set(required) - supported:
        raise DiscoveryError(
            f"unsupported required constraints: {sorted(set(required) - supported)}"
        )

    missing_required = []
    for field in required:
        if field in LIST_FIELDS and not normalized_lists[field]:
            missing_required.append(field)
        elif field in SCALAR_FIELDS:
            value = constraints.get(field)
            if not isinstance(value, str) or not value.strip():
                missing_required.append(field)
        elif field == "tempo_bpm" and field not in constraints:
            missing_required.append(field)
    if missing_required:
        raise DiscoveryError(
            "required constraints need non-empty request values: "
            f"{sorted(set(missing_required))}"
        )


def normalize_evidence(value: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if not isinstance(value, list):
        return result
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get("source"), str):
            continue
        source = entry["source"].strip()
        if not source:
            continue
        normalized = {"source": source}
        for field in ("kind", "retrieved_at"):
            if isinstance(entry.get(field), str) and entry[field].strip():
                normalized[field] = entry[field].strip()
        result.append(normalized)
    return result


def fingerprint(request: dict[str, Any]) -> str:
    data = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()[:12]


def make_candidate_id(source_id: str, request: dict[str, Any]) -> str:
    data = f"repository\0{source_id}\0{fingerprint(request)}"
    return "candidate-" + hashlib.sha256(data.encode()).hexdigest()[:16]


def validate_catalog(catalog: dict[str, Any]) -> None:
    if not isinstance(catalog, dict) or catalog.get("version") != 1:
        raise DiscoveryError("catalog must be an object with version 1")
    if not isinstance(catalog.get("items"), list):
        raise DiscoveryError("catalog.items must be a list")

    seen: set[str] = set()
    for index, item in enumerate(catalog["items"]):
        if not isinstance(item, dict):
            raise DiscoveryError(f"catalog item {index} must be an object")
        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in seen:
            raise DiscoveryError(f"catalog item {index} has a missing or duplicate id")
        seen.add(source_id)
        if item.get("target_type") not in TARGET_TYPES:
            raise DiscoveryError(f"catalog item {source_id!r} has invalid target_type")
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            raise DiscoveryError(f"catalog item {source_id!r} needs a title")

        for field in LIST_FIELDS.values():
            values = strings(item.get(field), f"catalog.{source_id}.{field}")
            if field == "genres" and set(values) - CANONICAL_GENRES:
                raise DiscoveryError(f"catalog item {source_id!r} has unsupported genres")
        for field in ("tunings", "meters"):
            strings(item.get(field), f"catalog.{source_id}.{field}")
        if "tempo_bpm" in item and (
            isinstance(item["tempo_bpm"], bool)
            or not isinstance(item["tempo_bpm"], int)
            or not 20 <= item["tempo_bpm"] <= 300
        ):
            raise DiscoveryError(f"catalog item {source_id!r} has invalid tempo_bpm")


def score_item(
    request: dict[str, Any], item: dict[str, Any]
) -> tuple[int, dict[str, list[str]], dict[str, list[str]]]:
    constraints = request.get("constraints", {})
    matched: dict[str, list[str]] = {}
    unmet: dict[str, list[str]] = {}
    score = 0

    for request_field, item_field in LIST_FIELDS.items():
        requested = strings(constraints.get(request_field), request_field)
        if not requested:
            continue
        available = set(strings(item.get(item_field), item_field))
        yes = [value for value in requested if value in available]
        no = [value for value in requested if value not in available]
        if yes:
            matched[request_field] = yes
            score += 20 * len(yes)
        if no:
            unmet[request_field] = no

    for request_field, item_field in SCALAR_FIELDS.items():
        value = constraints.get(request_field)
        if not isinstance(value, str) or not value.strip():
            continue
        requested = token(value)
        raw = item.get(item_field)
        available = (
            [token(raw)]
            if item_field == "difficulty" and isinstance(raw, str)
            else strings(raw, item_field)
        )
        if requested in available:
            matched[request_field] = [requested]
            score += 15
        else:
            unmet[request_field] = [requested]

    tempo = constraints.get("tempo_bpm")
    if isinstance(tempo, dict):
        item_tempo = item.get("tempo_bpm")
        if (
            isinstance(item_tempo, int)
            and not isinstance(item_tempo, bool)
            and tempo.get("min", 20) <= item_tempo <= tempo.get("max", 300)
        ):
            matched["tempo_bpm"] = [str(item_tempo)]
            score += 15
        else:
            unmet["tempo_bpm"] = [f"{tempo.get('min', 20)}-{tempo.get('max', 300)}"]

    return score, matched, unmet


def local_candidate(
    request: dict[str, Any],
    item: dict[str, Any],
    score: int,
    matched: dict[str, list[str]],
    unmet: dict[str, list[str]],
) -> dict[str, Any]:
    identity = {"title": item["title"].strip()}
    identity.update(
        {
            field: item[field].strip()
            for field in ("artist", "composer", "version")
            if isinstance(item.get(field), str) and item[field].strip()
        }
    )
    return {
        "candidate_id": make_candidate_id(item["id"], request),
        "source_id": item["id"],
        "target_type": item["target_type"],
        "identity": identity,
        "score": score,
        "matched_constraints": matched,
        "unmet_constraints": unmet,
        "summary": text(item.get("summary"), "Repository catalog candidate."),
        "prerequisites": optional_strings(item.get("prerequisites")),
        "required_capabilities": optional_strings(item.get("required_capabilities")),
        "preferred_capabilities": optional_strings(item.get("preferred_capabilities")),
        "evidence": normalize_evidence(item.get("evidence")),
        "licensing": text(item.get("licensing"), "unknown"),
        "conflicts": optional_strings(item.get("conflicts")),
        "proposed_next_action": text(
            item.get("proposed_next_action"),
            "Review before creating or changing a domain record.",
        ),
    }


def search_catalog(
    request: dict[str, Any], catalog: dict[str, Any] | None
) -> dict[str, Any]:
    validate_request(request)
    base = {
        "catalog": "repository",
        "catalog_version": catalog.get("version") if isinstance(catalog, dict) else None,
        "request_fingerprint": fingerprint(request),
    }
    if catalog is None:
        return base | {
            "status": "degraded",
            "candidates": [],
            "warnings": ["local catalog is unavailable"],
        }

    validate_catalog(catalog)
    required = set(request.get("required_constraints", []))
    candidates = []
    for item in catalog["items"]:
        if item["target_type"] != request["target_type"]:
            continue
        score, matched, unmet = score_item(request, item)
        if required & set(unmet):
            continue
        candidates.append(local_candidate(request, item, score, matched, unmet))

    candidates.sort(key=lambda value: (-value["score"], value["source_id"]))
    candidates = candidates[: request.get("limit", 5)]
    return base | {
        "status": "complete" if candidates else "degraded",
        "candidates": candidates,
        "warnings": [] if candidates else ["no local catalog candidates matched"],
    }


def write(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("catalog")
    try:
        args = parser.parse_args(argv)
        request = read_json(Path(args.request))
        catalog_path = Path(args.catalog)
        write(search_catalog(request, read_json(catalog_path) if catalog_path.exists() else None))
        return 0
    except (DiscoveryError, json.JSONDecodeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
