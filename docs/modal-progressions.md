# Modal progression semantics

Modal backing-track requests distinguish four separate concepts that ordinary major-key progression requests can often collapse:

- **tonal centre** — the pitch heard as home for the guitar part;
- **mode** — preset-owned interval/harmonic context such as Dorian or Mixolydian;
- **key signature** — MIDI metadata for the shared pitch collection / parent major key;
- **progression preset** — the reusable Roman-numeral harmonic recipe.

Groove, instrumentation, bass style, and voicing remain separate realization choices. A modal progression does not change the Groove Engine, bass engine, arrangement model, or MIDI format.

## Why tonal centre is explicit

D Dorian uses the pitch collection of C major, but D is the tonal centre. Encoding the request as key D would make the MIDI key-signature event incorrect. The bounded request therefore carries both values:

```json
{
  "key_signature": "C",
  "tonal_center": "D",
  "form": {
    "bars": 4,
    "progression_preset": "progression-modal-dorian-i-iv"
  }
}
```

The resolver transposes the preset's Roman numerals from `tonal_center`, derives the expected parent-major key signature from the preset-owned mode, and rejects a request when the supplied MIDI key signature disagrees.

## Initial presets

### Dorian i-IV

`progression-modal-dorian-i-iv` owns `mode: dorian` and the form:

```text
| Im | Im | IV | IV |
```

For D Dorian the deterministic resolution is:

```text
Dm | Dm | G | G
```

The expected MIDI key signature is C major.

### Mixolydian I-bVII

`progression-modal-mixolydian-i-bvii` owns `mode: mixolydian` and the form:

```text
| I | I | bVII | bVII |
```

For G Mixolydian the deterministic resolution is:

```text
G | G | F | F
```

The expected MIDI key signature is C major.

## Bounded v1 surface

BackingTrackRequest v1 accepts natural-note modal tonal centres only:

```text
C D E F G A B
```

Accidental/enharmonic spellings such as `F#`, `Gb`, `Bb`, or `A#` fail closed for `tonal_center`. This is intentional: expanding enharmonic modal spelling should be a deliberate contract change rather than an implicit guess.

`tonal_center` is also rejected for:

- explicit chord-list forms;
- non-modal progression presets.

A modal preset without `tonal_center` is invalid.

## Provenance

Existing non-modal request output is unchanged. A resolved modal request adds these fields to request provenance:

- `progression_preset`
- `mode`
- `tonal_center`
- `key_signature`

This keeps the generated `BackingTrackSpec` ordinary and renderable while preserving enough information to explain why its chord roots and MIDI key-signature metadata differ.

## Examples

Two checked-in requests exercise the initial boundary:

- `examples/backing-tracks/d-dorian-request.json`
- `examples/backing-tracks/g-mixolydian-request.json`

Resolve them with the normal request command:

```bash
python scripts/resolve_backing_track_request.py examples/backing-tracks/d-dorian-request.json
python scripts/resolve_backing_track_request.py examples/backing-tracks/g-mixolydian-request.json
```

The progression catalog CLI can also resolve a modal preset directly when a tonal centre is explicit:

```bash
python scripts/progression_catalog.py resolve progression-modal-dorian-i-iv C --tonal-center D
python scripts/progression_catalog.py resolve progression-modal-mixolydian-i-bvii C --tonal-center G
```
