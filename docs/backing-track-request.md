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
| `tempo_bpm` | Requested tempo; must also fit the selected preset range |
| `meter` | Requested meter; must exactly match the selected groove preset |
| `groove_preset` | Stable ID from the public groove catalog |
| `count_in_bars` | Zero to four count-in bars; defaults to one |
| `form.bars` | Total musical bars, from 1 to 128 |
| `form.progression` | Chord progression repeated deterministically across the form |
| `form.section_name` | Optional marker name; defaults to `PRACTICE` |
| `instrumentation` | Bounded roles: `drums`, `bass`, `keys`, `pad` |
| `arrangement` | Optional whole-accompaniment bar cycle |

Example:

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

The committed example is at `examples/backing-tracks/funk-wah-request.json`.

## Deterministic resolution

`resolve_backing_track_request.py` validates the request and derives fields that are
not caller-controlled:

- MIDI channels;
- General MIDI programs;
- track names and default velocities;
- track ordering;
- progression expansion to exactly one chord per bar;
- output path under `generated/backing-tracks/`;
- backing-track provenance metadata.

Instrumentation is canonicalized in the order `drums`, `bass`, `keys`, `pad`,
regardless of the order supplied by the caller.

A groove preset reference is checked against both meter and its catalog tempo range.
Unknown presets, unsupported chord qualities, unsafe IDs, duplicate roles, unknown
request fields, and malformed arrangement cycles fail closed before a manifest is
returned.

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
  examples/backing-tracks/funk-wah-request.json
```

To write the resolved manifest:

```bash
python3 scripts/resolve_backing_track_request.py \
  examples/backing-tracks/funk-wah-request.json \
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

The public repository does not need to know how the upstream caller chose the
preset, progression, tempo, or practice purpose. It only needs a valid versioned
request and returns deterministic domain data.

This keeps the integration replaceable: a different caller can produce the same
request without changing the groove engine, backing-track engine, or MIDI renderer.
