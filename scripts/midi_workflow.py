#!/usr/bin/env python3
"""Compatibility entrypoint for deterministic Type 1 MIDI workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: direct script execution predates the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import midi as _domain  # noqa: E402

TPQN = _domain.TPQN
DRUM_CHANNEL = _domain.DRUM_CHANNEL
ManifestError = _domain.ManifestError
vlq = _domain.vlq
meta = _domain.meta
midi_chunk = _domain.midi_chunk
TimedEvent = _domain.TimedEvent
track_bytes = _domain.track_bytes
note_events = _domain.note_events
require = _domain.require
validate_manifest = _domain.validate_manifest
NOTE_NAMES = _domain.NOTE_NAMES
chord_notes = _domain.chord_notes
key_signature_payload = _domain.key_signature_payload
conductor_track = _domain.conductor_track
arrangement_chords = _domain.arrangement_chords
generate_track = _domain.generate_track
read_vlq = _domain.read_vlq


def generate(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = _domain.render(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


def inspect_midi(path: Path) -> dict[str, object]:
    return _domain.inspect(path.read_bytes())


def validate_output(manifest_path: Path, midi_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return _domain.validate_rendered(manifest, midi_path.read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("manifest", type=Path)
    generate_parser.add_argument("output", type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("manifest", type=Path)
    validate_parser.add_argument("midi", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate(args.manifest, args.output)
            report = validate_output(args.manifest, args.output)
        else:
            report = validate_output(args.manifest, args.midi)
    except (OSError, json.JSONDecodeError, ManifestError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
