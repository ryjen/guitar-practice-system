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
    "bars": 12,
    "progression_preset": "jazz-blues-12",
    "section_name": "JAZZ-BLUES-12"
  }
}
```

The request resolver checks the preset meter and exact form length, then transposes the Roman-numeral changes using the request key. Inline `form.progression` remains available for arbitrary or uncatalogued harmony. A form must choose exactly one source.

This keeps the catalog authoritative for reusable progression identity while the resolved `BackingTrackSpec` still contains ordinary concrete chord symbols.

## Current twelve-bar presets

| ID | Identity |
|---|---|
| `blues-12-dominant` | standard dominant twelve-bar blues |
| `blues-12-quick-change` | dominant blues with IV in bar 2 |
| `jazz-blues-12` | jazz-blues practice form with fixed opening and VI-II-V-I ending |

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

Resolve jazz blues in C:

```bash
python3 scripts/progression_catalog.py resolve jazz-blues-12 C
```

The resolver currently targets major-key progression presets and emits chord symbols supported by the deterministic MIDI renderer.
