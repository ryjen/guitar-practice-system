"""Deterministic slow/medium/fast backing-track practice progression rules."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any

from guitar_practice.domain import backing, backing_request, groove, midi

PROGRESSION_VERSION = 1
PROFILE = "tempo-space-v1"


@dataclass(frozen=True)
class StageDefinition:
    name: str
    tempo_percent: int
    drum_gap_cycle: dict[str, Any] | None


STAGES = (
    StageDefinition("slow", 70, None),
    StageDefinition("medium", 85, {"length": 4, "mute_bars": [3]}),
    StageDefinition("fast", 100, {"length": 4, "mute_bars": [2, 3]}),
)


def _tempo(target: int, percent: int, minimum: int) -> int:
    scaled = (target * percent + 50) // 100
    return max(minimum, min(target, scaled))


def _cycle_mutes(cycle: dict[str, Any], bar: int) -> bool:
    return bar % cycle["length"] in cycle["mute_bars"]


def compose_bar_cycles(
    existing: dict[str, Any] | None,
    added: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if existing is None:
        return copy.deepcopy(added)
    if added is None:
        return copy.deepcopy(existing)

    length = math.lcm(existing["length"], added["length"])
    if length > 64:
        raise midi.ManifestError("composed drum gap cycle cannot exceed 64 bars")
    mute_bars = [
        bar
        for bar in range(length)
        if _cycle_mutes(existing, bar) or _cycle_mutes(added, bar)
    ]
    return {"length": length, "mute_bars": mute_bars}


def _progression_groove(
    groove_catalog: dict[str, Any],
    preset_id: str,
    added_cycle: dict[str, Any] | None,
) -> dict[str, Any]:
    resolved = groove.resolved_groove(groove_catalog, preset_id)
    existing = resolved.get("bar_cycle")
    combined = compose_bar_cycles(existing, added_cycle)
    if combined is None:
        resolved.pop("bar_cycle", None)
    else:
        resolved["bar_cycle"] = combined
    return resolved


def _stage_spec(
    base_spec: dict[str, Any],
    *,
    groove_catalog: dict[str, Any],
    preset_id: str,
    preset_min_tempo: int,
    stage: StageDefinition,
) -> dict[str, Any]:
    spec = copy.deepcopy(base_spec)
    base_id = base_spec["id"]
    base_title = base_spec["title"]
    stage_id = f"{base_id}-{stage.name}"

    spec["id"] = stage_id
    spec["title"] = f"{base_title} — {stage.name.title()}"
    spec["tempo_bpm"] = _tempo(
        base_spec["tempo_bpm"],
        stage.tempo_percent,
        preset_min_tempo,
    )
    spec["practice_progression"] = {
        "version": PROGRESSION_VERSION,
        "profile": PROFILE,
        "stage": stage.name,
        "tempo_percent": stage.tempo_percent,
        "added_drum_gap_cycle": copy.deepcopy(stage.drum_gap_cycle),
    }
    spec["outputs"]["midi"] = f"generated/backing-tracks/{stage_id}.mid"

    drum_tracks = [track for track in spec["tracks"] if track["role"] == "drums"]
    if len(drum_tracks) != 1:
        raise midi.ManifestError(
            "practice progression requires exactly one drum track"
        )
    drum = drum_tracks[0]
    drum["groove"] = _progression_groove(
        groove_catalog,
        preset_id,
        stage.drum_gap_cycle,
    )
    drum.pop("groove_preset", None)

    backing.validate_manifest(spec, groove_catalog)
    return spec


def resolve_progression(
    request: dict[str, Any],
    groove_catalog: dict[str, Any],
    progression_catalog: dict[str, Any],
    *,
    profile: str = PROFILE,
) -> dict[str, Any]:
    if profile != PROFILE:
        raise midi.ManifestError(
            f"unsupported practice progression profile: {profile!r}"
        )

    base_spec = backing_request.resolve_request(
        request,
        groove_catalog,
        progression_catalog,
    )
    preset_id = request["groove_preset"].strip()
    preset = groove.get_preset(groove_catalog, preset_id)
    minimum_tempo = preset["tempo_range_bpm"][0]

    stages = []
    for stage in STAGES:
        spec = _stage_spec(
            base_spec,
            groove_catalog=groove_catalog,
            preset_id=preset_id,
            preset_min_tempo=minimum_tempo,
            stage=stage,
        )
        stages.append(
            {
                "name": stage.name,
                "tempo_percent": stage.tempo_percent,
                "tempo_bpm": spec["tempo_bpm"],
                "added_drum_gap_cycle": copy.deepcopy(stage.drum_gap_cycle),
                "spec": spec,
            }
        )

    return {
        "version": PROGRESSION_VERSION,
        "profile": PROFILE,
        "source_request_id": base_spec["id"],
        "stages": stages,
    }
