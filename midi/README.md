# MIDI Exercises

This directory defines starter MIDI practice material for the guitar practice system.

The repo keeps MIDI generation source in text form so exercises are reviewable, diffable, and reproducible. Generated `.mid` files should be treated as build artifacts unless a later ADR decides to version them directly.

## Current exercises

| ID | Purpose | Default BPM |
|---|---:|---:|
| `muted_16th_warmup` | Timing, muting, relaxed right-hand motion | 80 |
| `wah_accent_groove` | Wah/expression timing over a simple groove | 92 |
| `u2_delay_pulse` | Dotted-eighth pulse / arpeggiated timing | 104 |
| `minor_pentatonic_call_response` | Phrase construction and response space | 88 |
| `bend_intonation_drone` | Bend target awareness against a drone | 72 |

## Generate MIDI files

From the repo root:

```bash
python3 tools/generate_midi.py
```

Generated files are written to:

```text
generated/midi/
```

## Design notes

- MIDI is useful for backing cues, timing drills, drum/metronome patterns, and simple guide tones
- MIDI is not a good representation of full guitar nuance, tone, wah behavior, or bend feel
- Generated material should be editable in GarageBand, MuseScore, Guitar Pro, Flow, or another DAW/notation tool
- The canonical exercise definition should remain text-first until the format stabilizes

## Privacy / copyright notes

- Do not commit copied commercial MIDI, tabs, lyrics, or full transcriptions unless licensing is explicit
- Prefer short original drills, backing structures, guide tones, and practice cues
- Store external references as links or metadata rather than copying third-party material
