#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic practice progression generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import midi_workflow as _midi_workflow  # noqa: E402
from guitar_practice.adapters.binary_files import BinaryFileStore  # noqa: E402
from guitar_practice.adapters.json_files import JsonFileStore  # noqa: E402
from guitar_practice.application.generation import GeneratePracticeProgression  # noqa: E402
from guitar_practice.domain import practice_progression as _domain  # noqa: E402

midi_workflow = _midi_workflow
PROGRESSION_VERSION = _domain.PROGRESSION_VERSION
PROFILE = _domain.PROFILE
StageDefinition = _domain.StageDefinition
STAGES = _domain.STAGES
_tempo = _domain._tempo
_cycle_mutes = _domain._cycle_mutes
compose_bar_cycles = _domain.compose_bar_cycles


def _catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


GROOVE_CATALOG = ROOT / "catalogs" / "grooves" / "catalog.json"
PROGRESSION_CATALOG = ROOT / "catalogs" / "progressions" / "catalog.json"


def _progression_groove(preset_id: str, added_cycle: dict[str, Any] | None) -> dict[str, Any]:
    return _domain._progression_groove(_catalog(GROOVE_CATALOG), preset_id, added_cycle)


def _stage_spec(
    base_spec: dict[str, Any],
    *,
    preset_id: str,
    preset_min_tempo: int,
    stage: StageDefinition,
) -> dict[str, Any]:
    return _domain._stage_spec(
        base_spec,
        groove_catalog=_catalog(GROOVE_CATALOG),
        preset_id=preset_id,
        preset_min_tempo=preset_min_tempo,
        stage=stage,
    )


def resolve_progression(
    request: dict[str, Any],
    *,
    profile: str = PROFILE,
) -> dict[str, Any]:
    return _domain.resolve_progression(
        request,
        _catalog(GROOVE_CATALOG),
        _catalog(PROGRESSION_CATALOG),
        profile=profile,
    )


def resolve_file(path: Path, *, profile: str = PROFILE) -> dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    return resolve_progression(request, profile=profile)


def write_progression(
    progression: dict[str, Any],
    output_dir: Path,
    *,
    render_midi: bool,
) -> None:
    GeneratePracticeProgression(
        documents=JsonFileStore(ROOT),
        artifacts=BinaryFileStore(ROOT),
    ).write(progression, str(output_dir), render_midi=render_midi)


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
            write_progression(progression, args.output_dir, render_midi=args.render_midi)
            print(args.output_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
