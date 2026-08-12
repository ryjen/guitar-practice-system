# Groove Catalog

The groove catalog is a set of deterministic, named drum presets intended for
practice backing tracks. A preset is not an opaque generator: each entry contains
ordinary `GrooveSpec` data that can be inspected, copied, modified, validated, and
rendered to Type 1 MIDI.

## Why a catalog

A stable preset ID is a useful integration boundary:

```text
practice request
    |
planner / supervisor
    |
preset ID + requested tempo/meter constraints
    |
catalog lookup
    |
GrooveSpec validation
    |
deterministic MIDI rendering
```

The planning layer may select or adapt a preset, but the public repository owns
the preset vocabulary, validation rules, and deterministic renderer.

## Initial presets

| ID | Meter | Default BPM | Primary use |
|---|---:|---:|---|
| `blues-shuffle` | 4/4 | 78 | Shuffle feel, slide, phrasing |
| `country-train` | 4/4 | 112 | Country picking and fills |
| `funk-wah-16` | 4/4 | 96 | Wah, muting, syncopation |
| `jazz-swing` | 4/4 | 120 | Comping, ii-V-I, swing feel |
| `alt-rock` | 4/4 | 108 | Riffing and dynamic control |
| `80s-rock` | 4/4 | 116 | Power chords, palm muting, lead practice |
| `odd-7-8` | 7/8 | 92 | 2+2+3 accents and odd-meter phrasing |
| `call-response-2x2` | 4/4 | 92 | Internal time, space, call/response |

These are intentionally style archetypes rather than transcriptions of commercial
recordings.

## Inspect and validate

```bash
python3 scripts/groove_catalog.py validate
python3 scripts/groove_catalog.py list
python3 scripts/groove_catalog.py show blues-shuffle
```

`show` returns the full preset including the underlying `GrooveSpec`.

## Bar cycles and gap practice

`GrooveSpec.bar_cycle` can mute deterministic bars inside a repeating cycle:

```json
{
  "bar_cycle": {
    "length": 4,
    "mute_bars": [2, 3]
  }
}
```

Bar indexes are zero-based within the cycle. The example therefore plays bars
1-2 and leaves bars 3-4 silent before repeating. Count-in bars are not part of the
cycle.

This supports internal-time, gap, and call/response exercises without teaching
the renderer any special musical workflow.

## Extension rules

New presets should:

- have a unique lower-case kebab-case ID;
- state a supported meter and bounded tempo range;
- include at least one practice intent and descriptive tag;
- remain deterministic for a fixed seed;
- avoid copying distinctive commercial drum performances;
- pass `groove_catalog.py validate` and the unit tests.

The catalog is a vocabulary, not a closed set. More genre-specific and technique-
specific presets can be added without changing the `GrooveSpec` renderer.
