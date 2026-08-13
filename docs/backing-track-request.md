# Backing-Track Request Boundary

`BackingTrackRequest` is the small caller-facing contract above `BackingTrackSpec`.
It lets an external planner or supervisor gateway request a practice backing track
without controlling low-level MIDI details.

```text
practice intent
    |
external planner / supervisor gateway
    |
BackingTrackRequest
    |
strict validation + deterministic resolution
    |
BackingTrackSpec
    |
backing-track engine
    |
Type 1 MIDI
```

The request boundary is deliberately narrower than the backing-track manifest.
Callers choose musical constraints; the public resolver owns concrete rendering
configuration.

## Request shape

A version 1 request contains:

| Field | Purpose |
|---|---|
| `version` | Contract version; currently `1` |
| `id` | Lower-case kebab-case artifact identity |
| `title` | Human-readable practice title |
| `purpose` | Practice intent expressed as descriptive metadata |
| `key_signature` | MIDI key signature understood by the existing renderer |
| `tempo_bpm` | Requested tempo; must also fit the selected groove range |
| `meter` | Requested meter; must match selected groove and progression presets |
| `groove_preset` | Stable ID from the public groove catalog |
| `bass_style` | Optional bounded bass style; defaults to `auto` when bass is present |
| `count_in_bars` | Zero to four count-in bars; defaults to one |
| `form.bars` | Total musical bars, from 1 to 128 |
| `form.progression` | Inline chord progression repeated deterministically across the form |
| `form.progression_preset` | Stable ID from the public progression catalog |
| `form.section_name` | Optional marker name; defaults to `PRACTICE` |
| `instrumentation` | Bounded roles: `drums`, `bass`, `keys`, `pad` |
| `arrangement` | Optional whole-accompaniment bar cycle |

A form must provide **exactly one** of `progression` or `progression_preset`.

### Inline progression

Inline progressions remain useful for arbitrary, modal, non-functional, or otherwise
uncatalogued harmony. A shorter list repeats to fill `form.bars`.

```json
{
  "form": {
    "bars": 8,
    "progression": ["Em7", "A7"],
    "section_name": "POCKET"
  }
}
```

### Progression preset

A progression preset references a reusable form owned by the progression catalog.
The resolver transposes it using `key_signature`; callers do not copy the resolved
chord list into the request.

```json
{
  "key_signature": "C",
  "meter": [4, 4],
  "form": {
    "bars": 12,
    "progression_preset": "jazz-blues-12",
    "section_name": "JAZZ-BLUES-12"
  }
}
```

Preset-backed forms are intentionally stricter than inline progressions:

- the preset must exist;
- `form.bars` must exactly match the preset length;
- request meter must exactly match the preset meter;
- the key must be supported by the preset resolver;
- the resolved chords are validated before a `BackingTrackSpec` is returned.

This prevents a stable 12-bar identity from being silently stretched or rewritten by
a request.

## Complete example

```json
{
  "version": 1,
  "id": "funk-wah-pocket-em-96",
  "title": "Funk/Wah Pocket Practice",
  "purpose": "Practice wah timing and muted sixteenth-note articulation.",
  "key_signature": "Emin",
  "tempo_bpm": 96,
  "meter": [4, 4],
  "groove_preset": "funk-wah-16",
  "bass_style": "auto",
  "count_in_bars": 1,
  "form": {
    "bars": 8,
    "progression": ["Em7", "A7"],
    "section_name": "POCKET"
  },
  "instrumentation": ["drums", "bass"],
  "arrangement": {
    "bar_cycle": {
      "length": 4,
      "mute_bars": [3]
    }
  }
}
```

Committed examples:

- `examples/backing-tracks/funk-wah-request.json` uses an inline progression.
- `examples/backing-tracks/jazz-blues-12-request.json` uses the `jazz-blues-12` preset.

## Deterministic resolution

`resolve_backing_track_request.py` validates the request and derives fields that are
not caller-controlled:

- MIDI channels;
- General MIDI programs;
- track names and default velocities;
- track ordering;
- automatic bass style for the selected groove preset;
- progression expansion or preset transposition to exactly one chord per bar;
- output path under `generated/backing-tracks/`;
- backing-track provenance metadata.

Instrumentation is canonicalized in the order `drums`, `bass`, `keys`, `pad`,
regardless of the order supplied by the caller.

When bass is present, `bass_style` may be `auto`, `kick-root`, `kick-root-fifth`,
`kick-root-octave`, or `walking`. `auto` maps deterministically from the groove
preset; the mapping is documented in `docs/bass-engine.md`. Supplying a bass style
without bass instrumentation fails closed.

A groove preset reference is checked against both meter and its catalog tempo range.
A progression preset is checked against key, meter, and exact form length. Unknown
presets, unsupported chord qualities, unsafe IDs, duplicate roles, unknown request
fields, and malformed arrangement cycles fail closed before a manifest is returned.

When a progression preset is used, its stable ID is retained in request provenance;
the rendered `BackingTrackSpec` still contains ordinary concrete chord symbols.

## Why not accept a complete track list

The request boundary is an authority boundary. A complete `BackingTrackSpec` can
name channels, programs, output paths, track objects, and other rendering details.
Those are useful inside the public engine but unnecessary for an external planner.

`BackingTrackRequest` therefore does not expose:

- arbitrary filesystem paths;
- MIDI channel selection;
- General MIDI program selection;
- raw drum notes or timing events;
- arbitrary track dictionaries;
- shell, DAW, or MIDI-device operations;
- free-form execution instructions.

The gateway chooses from a musical vocabulary; the deterministic resolver owns the
mechanical translation into the public backing-track domain.

## Resolve a request

From the repository root:

```bash
python3 scripts/resolve_backing_track_request.py \
  examples/backing-tracks/jazz-blues-12-request.json
```

To write the resolved manifest:

```bash
python3 scripts/resolve_backing_track_request.py \
  examples/backing-tracks/jazz-blues-12-request.json \
  --output /tmp/backing-track.json
```

The output is a normal `BackingTrackSpec` and can be passed to the existing
`backing_track_engine.py` generation path.

## Supervisor gateway integration

A future supervisor gateway can treat the request schema as its capability payload:

```text
music.backing-track.request
    request: BackingTrackRequest v1
    response: BackingTrackSpec
```

The public repository does not need to know how the upstream caller chose the groove,
progression preset, tempo, bass style, or practice purpose. It only needs a valid
versioned request and returns deterministic domain data.

This keeps the integration replaceable: a different caller can produce the same
request without changing the groove engine, progression catalog, backing-track
engine, bass engine, or MIDI renderer.
