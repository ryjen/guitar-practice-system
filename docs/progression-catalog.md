# Progression Catalog

Chord progressions are reusable musical objects. The progression catalog keeps their harmonic identity separate from groove, instrumentation, voicing, and backing-track arrangement.

```text
Progression preset
      |
      +-- Roman-numeral changes
      +-- bar count / meter
      +-- family / tags
      +-- optional identity invariants
      |
      v
selected major key
      |
      v
concrete chord symbols
```

The catalog is stored at `catalogs/progressions/catalog.json` and validated by `scripts/progression_catalog.py`.

## Backing-track request integration

A `BackingTrackRequest` may reference a progression by stable ID instead of copying its concrete chord list:

```json
{
  "key_signature": "C",
  "meter": [4, 4],
  "form": {
    "bars": 4,
    "progression_preset": "progression-jazz-major-ii-v-i",
    "section_name": "II-V-I"
  }
}
```

The request resolver checks the preset meter and exact form length, then transposes the Roman-numeral changes using the request key. Inline `form.progression` remains available for arbitrary or uncatalogued harmony. A form must choose exactly one source.

This keeps the catalog authoritative for reusable progression identity while the resolved `BackingTrackSpec` still contains ordinary concrete chord symbols.

## Current presets

| ID | Identity |
|---|---|
| `blues-12-dominant` | standard dominant twelve-bar blues |
| `blues-12-quick-change` | dominant blues with IV in bar 2 |
| `jazz-blues-12` | jazz-blues practice form with fixed opening and VI-II-V-I ending |
| `progression-jazz-major-ii-v-i` | four-bar major ii-V-I with repeated tonic resolution |

## Major ii-V-I identity

`progression-jazz-major-ii-v-i` promotes the existing documented worked example into executable catalog data:

```text
| ii7 | V7 | Imaj7 | Imaj7 |
```

The first three bars are the harmonic identity. The repeated tonic bar is a practice realization that leaves time to hear resolution, inspect guide-tone movement, and prepare the next key.

In C:

```text
Dm7 | G7 | Cmaj7 | Cmaj7
```

In F:

```text
Gm7 | C7 | Fmaj7 | Fmaj7
```

The committed backing-track request `examples/backing-tracks/ii-v-i-c-request.json` uses the same preset with the `jazz-swing` groove, walking bass, and light keys.

## Circle-of-fourths traversal

The progression resolver provides a bounded major-key fourths traversal for transposition and voice-leading practice.

Canonical order:

```text
C → F → Bb → Eb → Ab → Db → Gb → B → E → A → D → G
```

`F#` is accepted as an enharmonic start-key alias and normalized to the canonical `Gb` position. A traversal contains between one and twelve positions and may start anywhere in the sequence. It wraps deterministically at the end.

Examples:

```text
start C, count 4 → C, F, Bb, Eb
start A, count 4 → A, D, G, C
start F#, count 2 → Gb, B
```

The traversal changes only the tonic used to resolve the progression. It does not change groove, tempo, instrumentation, voicing, or fretboard position.

## Jazz blues identity

`jazz-blues-12` intentionally uses this exact twelve-bar map:

```text
| I7  | I7  | IV7 | IV7 |
| I7  | I7  | V7  | I7  |
| VI7 | II7 | V7  | I7  |
```

Two invariants are stored with the preset:

```text
opening = I7 I7 IV7 IV7
ending  = VI7 II7 V7 I7
```

Catalog validation fails if those blocks drift from the actual changes. This keeps optional jazz vocabulary from silently redefining the base form.

In C the resolver produces:

```text
C7 | C7 | F7 | F7 | C7 | C7 | G7 | C7 | A7 | D7 | G7 | C7
```

In A it produces:

```text
A7 | A7 | D7 | D7 | A7 | A7 | E7 | A7 | F#7 | B7 | E7 | A7
```

## Optional enrichment versus form identity

Guide-tone practice, ii-V language, diminished colour, altered-dominant vocabulary, and turnaround anticipation are useful jazz-blues layers. They should not change the canonical `jazz-blues-12` opening or ending unless a future preset is deliberately given a different identity.

This distinction lets practice sessions vary vocabulary while keeping the form stable enough to hear and internalize.

## CLI

Validate the catalog:

```bash
python3 scripts/progression_catalog.py validate
```

List presets:

```bash
python3 scripts/progression_catalog.py list
```

Resolve ii-V-I in C:

```bash
python3 scripts/progression_catalog.py resolve progression-jazz-major-ii-v-i C
```

Resolve four adjacent positions through the circle of fourths:

```bash
python3 scripts/progression_catalog.py fourths \
  progression-jazz-major-ii-v-i \
  --start-key C \
  --count 4
```

Resolve jazz blues in C:

```bash
python3 scripts/progression_catalog.py resolve jazz-blues-12 C
```

The resolver currently targets major-key progression presets and emits chord symbols supported by the deterministic MIDI renderer.
