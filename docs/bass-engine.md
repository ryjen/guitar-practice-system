# Groove-Aware Bass Accompaniment

The bass engine adds deterministic accompaniment that can interact with the drum
groove without moving musical planning into the MIDI renderer.

```text
BackingTrackSpec
├── drums
│   └── GrooveSpec
├── bass
│   └── BassSpec
└── arrangement
    └── whole-accompaniment gaps
```

Existing bass tracks without a `bass` object keep the legacy root/fifth quarter-note
renderer. A bass track opts into the new engine explicitly.

## BassSpec

```json
{
  "name": "Bass",
  "role": "bass",
  "channel": 0,
  "program": 34,
  "velocity": 80,
  "bass": {
    "style": "kick-root-fifth",
    "gate_percent": 72,
    "follow_kick_velocity": true
  }
}
```

Supported styles:

| Style | Timing source | Pitch behavior |
|---|---|---|
| `kick-root` | kick pattern | chord root on every kick |
| `kick-root-fifth` | kick pattern | alternate root and fifth |
| `kick-root-octave` | kick pattern | alternate root and octave |
| `walking` | meter pulse | cycle through available chord tones |

`gate_percent` controls note length from 20–95 percent of the available rhythmic
window. Kick-locked styles follow kick velocity by default; `walking` does not.

## Kick locking

Kick-locked styles reuse the exact kick timing produced by `GrooveSpec`, including
swing and bounded timing variation. This keeps bass attacks aligned with the drum
pocket rather than placing them on an unrelated fixed grid.

The bass engine uses the **underlying kick pattern**, not the rendered drum mute
state. This preserves the established scope of `groove.bar_cycle`:

```text
GrooveSpec.bar_cycle
    drums only

BassSpec kick lock
    follows the underlying kick pattern

BackingTrackSpec.arrangement.bar_cycle
    drums + bass + keys + pads
```

That distinction allows practice where the drums disappear but harmonic support
continues. To create full-band silence, use `arrangement.bar_cycle`.

## Request integration

`BackingTrackRequest v1` accepts an optional `bass_style` when `bass` is present in
`instrumentation`:

```json
{
  "groove_preset": "funk-wah-16",
  "bass_style": "auto",
  "instrumentation": ["drums", "bass"]
}
```

`auto` resolves deterministically from the selected groove preset:

| Groove preset | Automatic bass style |
|---|---|
| `blues-shuffle` | `kick-root-fifth` |
| `country-train` | `kick-root-fifth` |
| `funk-wah-16` | `kick-root-octave` |
| `jazz-swing` | `walking` |
| `alt-rock` | `kick-root` |
| `80s-rock` | `kick-root-fifth` |
| `odd-7-8` | `kick-root-fifth` |
| `call-response-2x2` | `kick-root` |

A caller may also request any explicit supported style. Invalid styles and a
`bass_style` supplied without bass instrumentation fail closed.

## Determinism and authority

The bass engine does not choose chord progressions, files, channels, instruments,
or external actions. It receives validated domain data and emits MIDI events. The
same groove, chord, bar index, tempo, and BassSpec produce the same result.

This keeps the supervisor-facing boundary small:

```text
practice intent
      |
BackingTrackRequest
      |
BackingTrackSpec
      |
GrooveSpec + BassSpec
      |
deterministic MIDI
```
