#!/usr/bin/env python3
"""Derive deterministic slow/medium/fast practice variants from one request."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import backing_track_engine
import groove_catalog
import midi_workflow
import resolve_backing_track_request


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
    """Compose two drum-only cycles without losing either source's mute bars."""
    if existing is None:
        return json.loads(json.dumps(added)) if added is not None else None
    if added is None:
        return json.loads(json.dumps(existing))

    length = math.lcm(existing["length"], added["length"])
    if length > 64:
        raise midi_workflow.ManifestError(
            "composed drum gap cycle cannot exceed 64 bars"
        )
    mute_bars = [
        bar
        for bar in range(length)
        if _cycle_mutes(existing, bar) or _cycle_mutes(added, bar)
    ]
    return {"length": length, "mute_bars": mute_bars}


def _progression_groove(
    preset_id: str,
    added_cycle: dict[str, Any] | None,
) -> dict[str, Any]:
    groove = groove_catalog.resolved_groove(preset_id)
    existing = groove.get("bar_cycle")
    combined = compose_bar_cycles(existing, added_cycle)
    if combined is None:
        groove.pop("bar_cycle", None)
    else:
        groove["bar_cycle"] = combined
    return groove


def _stage_spec(
    base_spec: dict[str, Any],
    *,
    preset_id: str,
    preset_min_tempo: int,
    stage: StageDefinition,
) -> dict[str, Any]:
    spec = json.loads(json.dumps(base_spec))
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
        "added_drum_gap_cycle": json.loads(json.dumps(stage.drum_gap_cycle)),
    }
    spec["outputs"]["midi"] = f"generated/backing-tracks/{stage_id}.mid"

    drum_tracks = [track for track in spec["tracks"] if track["role"] == "drums"]
    if len(drum_tracks) != 1:
        raise midi_workflow.ManifestError(
            "practice progression requires exactly one drum track"
        )
    drum = drum_tracks[0]
    drum["groove"] = _progression_groove(preset_id, stage.drum_gap_cycle)
    drum.pop("groove_preset", None)

    backing_track_engine.validate_manifest(spec)
    return spec


def resolve_progression(
    request: dict[str, Any],
    *,
    profile: str = PROFILE,
) -> dict[str, Any]:
    if profile != PROFILE:
        raise midi_workflow.ManifestError(
            f"unsupported practice progression profile: {profile!r}"
        )

    base_spec = resolve_backing_track_request.resolve_request(request)
    preset_id = request["groove_preset"].strip()
    preset = groove_catalog.get_preset(preset_id)
    minimum_tempo = preset["tempo_range_bpm"][0]

    stages = []
    for stage in STAGES:
        spec = _stage_spec(
            base_spec,
            preset_id=preset_id,
            preset_min_tempo=minimum_tempo,
            stage=stage,
        )
        stages.append(
            {
                "name": stage.name,
                "tempo_percent": stage.tempo_percent,
                "tempo_bpm": spec["tempo_bpm"],
                "added_drum_gap_cycle": json.loads(
                    json.dumps(stage.drum_gap_cycle)
                ),
                "spec": spec,
            }
        )

    return {
        "version": PROGRESSION_VERSION,
        "profile": PROFILE,
        "source_request_id": base_spec["id"],
        "stages": stages,
    }


def resolve_file(path: Path, *, profile: str = PROFILE) -> dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    return resolve_progression(request, profile=profile)


def write_progression(
    progression: dict[str, Any],
    output_dir: Path,
    *,
    render_midi: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = output_dir / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)

    for stage in progression["stages"]:
        spec = stage["spec"]
        manifest = manifests / f"{spec['id']}.json"
        manifest.write_text(
            json.dumps(spec, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if render_midi:
            midi_path = output_dir / spec["outputs"]["midi"]
            backing_track_engine.generate(manifest, midi_path)
            midi_workflow.validate_output(manifest, midi_path)

    (output_dir / "progression.json").write_text(
        json.dumps(progression, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--profile", default=PROFILE, choices=[PROFILE])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--render-midi", action="store_true")
    args = parser.parse_args(argv)

    if args.render_midi and args.output_dir is None:
        parser.error("--render-midi requires --output-dir")

    try:
        progression = resolve_file(args.request, profile=args.profile)
        if args.output_dir is None:
            print(json.dumps(progression, indent=2, sort_keys=True))
        else:
            write_progression(
                progression,
                args.output_dir,
                render_midi=args.render_midi,
            )
            print(args.output_dir)
    except (OSError, json.JSONDecodeError, midi_workflow.ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
