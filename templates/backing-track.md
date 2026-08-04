# Backing track: <name>

- **ID:** `<stable-lowercase-id>`
- **Purpose:** <musical problem or context this asset supports>
- **Linked techniques:** `<technique-id>`
- **Linked songs:** `<song-id>` or none
- **Status:** proposed | manifest-ready | generated | import-verified | maintained

## Reusable references

- **Progression IDs:**
- **Rhythm / meter IDs:**
- **Mode / tonal-context IDs:**
- **Genre layers:**
- **Expression intent:**

This asset owns concrete arrangement choices. Shared progression and rhythm definitions remain in their canonical files.

## Musical realization

- **Key / tonal centre:**
- **Tempo:**
- **Meter / grouping overrides:**
- **Feel overrides:**
- **Concrete chords / voicings:**
- **Length / form:**
- **Count-in:**
- **Loop start / end markers:**

## Harmony and form

| Section | Bars | Progression ID / override | Harmonic rhythm | Guitar room / cues |
|---|---:|---|---|---|
| | | | | |

## Instrument roles

| Track | Channel | Role | Register | Articulation | Instrument intent |
|---|---:|---|---|---|---|
| Conductor | — | Tempo, meter, key, markers | — | — | Metadata only |
| Drums | 10 | | | | |
| Bass | | | | | |
| Keys | | | | | |
| Other | | | | | |

## Arrangement room

- **Open beats / bars:**
- **Response windows:**
- **Delayed guitar entry:**
- **Sustain / decay allowance:**
- **Register reserved for guitar:**
- **Density ceiling:**
- **Musical purpose:**

## Variants

- **Tempo:**
- **Key:**
- **Density:**
- **Difficulty:**

Create a separate asset when feel, meter, harmonic function, form, target technique, or arrangement-room behaviour changes materially.

## Portable source

- **Metadata manifest:** `backing-tracks/<id>/manifest.json`
- **MIDI generator:**
- **Generated `.mid`:** `generated/backing-tracks/<variant-id>.mid`
- **Rendered audio:**
- **DAW project:**

The manifest and generator are canonical. Generated artifacts remain ignored unless deliberately promoted.

## DAW import notes

- Track naming:
- Instrument assignment:
- Routing:
- Markers:
- Loop range:
- Humanization or articulation changes:
- DAW-specific limitations:

## Provenance

- **Original / derived:**
- **Source or licence notes:**
- **Redistribution constraints:**

## Validation

### Automated

- [ ] Referenced IDs and section lengths are valid
- [ ] Output is Standard MIDI File Type 1
- [ ] Tempo, meter, and key metadata are present
- [ ] Tracks are separately and uniquely named
- [ ] Section markers match the manifest
- [ ] MIDI structure is not truncated or malformed

### Musical / DAW

- [ ] Tempo, meter, key, grouping, and markers import correctly
- [ ] Loop boundaries align to bars and do not cut notes unexpectedly
- [ ] Note ranges are appropriate for assigned instruments
- [ ] The arrangement leaves intended rhythmic and register room for the target guitar part
- [ ] Decay and response windows survive rendering and import
- [ ] A dry or minimally processed practice version remains available
- [ ] Import verification records the DAW and version

## Promotion

- `manifest-ready`: metadata and arrangement source are complete.
- `generated`: deterministic MIDI generation and automated validation pass.
- `import-verified`: DAW import confirms metadata, routing, loop behaviour, and intended arrangement room.
- `maintained`: regeneration and import checks continue to pass after meaningful source changes.
