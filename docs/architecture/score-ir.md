# Score IR architecture

## Purpose

Score IR is the canonical structured symbolic-music representation for Guitar Practice System. It is intentionally independent of MuseScore, Guitar Pro, MusicXML, MIDI byte encoding, audio renderers, CLI state, filesystems, and hardware export profiles.

A song is musical subject matter. Score IR is the deterministic representation used by score editing, import/export, practice/backing derivation, playback realization, and later inference workflows.

## Versioning

Every document carries:

```json
{
  "schema": "guitar-practice.score",
  "version": 1
}
```

Version 1 is strict: unknown structural fields are rejected. A structural change that changes accepted/required fields or semantics requires a new integer schema version and an explicit migration path. Readers reject unsupported versions rather than guessing.

The domain serializer emits canonical UTF-8 JSON with sorted object keys, compact separators, and one trailing newline. Arrays preserve semantic order. Loading and re-dumping an accepted document produces identical canonical bytes.

## Exact musical time

Score IR does not use MIDI ticks as canonical time.

Rational values are two-element reduced integer arrays:

```text
[numerator, denominator]
```

The denominator is positive and the fraction must be in lowest terms.

A location is:

```json
{"bar": 3, "beat": [3, 2]}
```

`beat` is 1-based in units of the active meter denominator. In 4/4, `[3, 2]` means beat 1.5. In 6/8, beat `[4, 1]` is the fourth eighth-note position.

A duration is a positive fraction of a whole note. For example:

- quarter note: `[1, 4]`
- eighth note: `[1, 8]`
- triplet eighth sounding duration: `[1, 12]`

Events may not cross a bar boundary. Tied notes are represented as separate bar-local events with tie state.

## Version 1 shape

```json
{
  "schema": "guitar-practice.score",
  "version": 1,
  "id": "blue-thing",
  "metadata": {
    "title": "Blue Thing",
    "composer": "Example Writer",
    "source": {
      "kind": "user",
      "id": "manual-transcription"
    }
  },
  "bars": [
    {"number": 1, "repeat_start": true},
    {"number": 2},
    {"number": 3, "ending_numbers": [1]},
    {"number": 4, "repeat_end": 2}
  ],
  "meter_map": [
    {"bar": 1, "beats": 4, "beat_unit": 4}
  ],
  "tempo_map": [
    {"location": {"bar": 1, "beat": [1, 1]}, "bpm": 110, "beat_unit": [1, 4]}
  ],
  "key_map": [
    {"bar": 1, "fifths": 2, "mode": "major"}
  ],
  "sections": [
    {"id": "verse", "label": "Verse", "start_bar": 1, "end_bar": 4}
  ],
  "rehearsal_marks": [
    {"location": {"bar": 1, "beat": [1, 1]}, "label": "A"}
  ],
  "harmony": [
    {"location": {"bar": 1, "beat": [1, 1]}, "symbol": "Em7"},
    {"location": {"bar": 2, "beat": [1, 1]}, "symbol": "A7"}
  ],
  "parts": [
    {
      "id": "guitar-1",
      "name": "Guitar",
      "role": "guitar",
      "instrument": {
        "name": "Electric Guitar",
        "family": "guitar",
        "midi": {
          "program": 29,
          "channel": 1,
          "percussion": false
        }
      },
      "guitar": {
        "tuning": [
          {"string": 6, "pitch": {"step": "E", "alter": 0, "octave": 2}},
          {"string": 5, "pitch": {"step": "A", "alter": 0, "octave": 2}},
          {"string": 4, "pitch": {"step": "D", "alter": 0, "octave": 3}},
          {"string": 3, "pitch": {"step": "G", "alter": 0, "octave": 3}},
          {"string": 2, "pitch": {"step": "B", "alter": 0, "octave": 3}},
          {"string": 1, "pitch": {"step": "E", "alter": 0, "octave": 4}}
        ]
      },
      "events": [
        {
          "kind": "note",
          "location": {"bar": 1, "beat": [1, 1]},
          "duration": [1, 4],
          "voice": 1,
          "pitch": {"step": "E", "alter": 0, "octave": 4},
          "position": {"string": 1, "fret": 0},
          "articulations": ["accent"],
          "dynamics": "mf"
        },
        {
          "kind": "rest",
          "location": {"bar": 1, "beat": [2, 1]},
          "duration": [1, 4],
          "voice": 1
        }
      ]
    }
  ]
}
```

Required top-level fields are `schema`, `version`, `id`, `metadata`, `bars`, `meter_map`, `tempo_map`, and `parts`. `key_map`, `sections`, `rehearsal_marks`, `harmony`, and `provenance` are optional.

For version 1, optional fields are omitted when absent. If an optional structural collection is present, it must have its documented type; explicit JSON `null` is not equivalent to omission.

## Bars and form

Bars are globally numbered, contiguous, and 1-based. Bar records may carry notation-level repeat/ending membership:

- `repeat_start: true`
- `repeat_end: <positive repeat count>`
- `ending_numbers: [1, 2, ...]`

Sections use inclusive `start_bar` / `end_bar` ranges. Rehearsal marks are location-anchored.

## Meter, tempo, and key maps

`meter_map` entries take effect at the start of the given bar. The first entry must start at bar 1. Meter changes are ordered by bar and unique per bar.

`tempo_map` entries are location-anchored. BPM is positive. `beat_unit` is a positive whole-note fraction such as `[1, 4]`.

`key_map` is optional. Version 1 represents conventional key signatures using `fifths` in `[-7, 7]` and a non-empty mode string.

## Harmony

Harmony events are global and location-anchored. The `symbol` is the explicit chord spelling supplied by a deterministic source, import, or user. Harmonic rhythm therefore remains independent from note events and guitar fingering.

## Parts, instruments, and roles

A part has a stable `id`, display `name`, semantic `role`, normalized `instrument`, and events. Instrument identity is semantic, not a renderer selection. Import adapters may derive these fields from source metadata. An instrument may additionally carry a bounded `midi` interoperability hint (`program`, `channel`, `percussion`) when the source provides that identity; it preserves imported routing/program facts without making MIDI byte encoding or a specific synthesizer canonical.

A guitar part may declare tuning. String numbers are explicit so alternate tunings and non-six-string instruments do not require implicit conventions.

## Events

Version 1 event kinds are `note` and `rest`.

All events have:

- `location`
- positive exact `duration`
- positive integer `voice`

Notes additionally have `pitch`. Pitch is the sounding pitch at the event attack and preserves spelling with `step`, integer `alter`, and `octave`.

Optional note fields include:

- `position`: string/fret position
- `tie`: `start`, `continue`, or `stop`
- `tuplet`: exact ratio and base written duration
- `articulations`: ordered string identifiers
- `techniques`: ordered technique descriptors
- `dynamics`: explicit dynamic marking
- `provenance`

Rests do not carry pitch or guitar position.

If a part declares guitar tuning and a note declares string/fret position, the attack pitch must equal the tuned open-string pitch plus fret offset. This checks that pitch and fingering coexist without becoming the same field.

### Tuplets

A tuplet descriptor is:

```json
{
  "id": "triplet-1",
  "actual": 3,
  "normal": 2,
  "base": [1, 8]
}
```

For a tuplet event, `duration` must equal `base * normal / actual`. Events sharing a tuplet id within a part must use the same ratio/base definition.

## Provenance and inference

Objects that may originate outside deterministic user-authored state can carry:

```json
{
  "provenance": {
    "kind": "inferred",
    "source": "chord-specialist",
    "confidence": 0.71,
    "alternatives": ["G7", "G7b9"]
  }
}
```

`kind` is one of `user`, `imported`, `generated`, or `inferred`. `source` is a stable descriptive identifier, not an executable path or command. `confidence` is allowed only for inferred data and is in `[0.0, 1.0]`. `alternatives` is optional inference metadata and does not change the accepted musical value.

This metadata allows later AI/import workflows to retain uncertainty without making inference mandatory for deterministic content.

## Validation invariants

Version 1 validation includes:

- exact schema id/version and no unknown structural fields
- stable slug identifiers where ids are used
- contiguous bars starting at 1
- first meter at bar 1 and valid meter/tempo/key locations
- reduced rational values with positive denominators
- event starts and durations contained within the active bar
- note/rest field separation
- pitch spelling/range validation
- unique part/section ids
- valid section ranges
- tuning string uniqueness and guitar pitch/fret coherence
- consistent tuplet definitions per tuplet id
- bounded provenance confidence semantics

More advanced notation invariants such as complete voice filling, beaming, enharmonic policy, and cross-part engraving are intentionally exporter/editor concerns unless they become necessary canonical invariants later.
