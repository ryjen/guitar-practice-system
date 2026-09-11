#!/usr/bin/env python3
"""Compatibility entrypoint for starter MIDI practice exercise generation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from guitar_practice.adapters.binary_files import BinaryFileStore  # noqa: E402
from guitar_practice.adapters.json_files import JsonFileStore  # noqa: E402
from guitar_practice.application.generation import GenerateMidiExercises  # noqa: E402
from guitar_practice.domain import midi_exercises as _domain  # noqa: E402

PPQ = _domain.PPQ
MANIFEST = ROOT / "midi" / "exercises.json"
OUT_DIR = ROOT / "generated" / "midi"
Note = _domain.Note
ControlChange = _domain.ControlChange
Event = _domain.Event
vlq = _domain.vlq
meta_text = _domain.meta_text
tempo_event = _domain.tempo_event
program_change = _domain.program_change
note_on = _domain.note_on
note_off = _domain.note_off
cc = _domain.cc
track_chunk = _domain.track_chunk
midi_file = _domain.midi_file
notes_to_events = _domain.notes_to_events
meta_track = _domain.meta_track
instrument_track = _domain.instrument_track
drum_track = _domain.drum_track
muted_16th_warmup = _domain.muted_16th_warmup
wah_accent_groove = _domain.wah_accent_groove
u2_delay_pulse = _domain.u2_delay_pulse
minor_pentatonic_call_response = _domain.minor_pentatonic_call_response
bend_intonation_drone = _domain.bend_intonation_drone
GENERATORS = _domain.GENERATORS


def main() -> None:
    outputs = GenerateMidiExercises(
        documents=JsonFileStore(ROOT),
        artifacts=BinaryFileStore(ROOT),
    ).execute()
    for output in outputs:
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
