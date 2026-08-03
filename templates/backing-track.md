# Backing track: <name>

- **ID:** `<stable-lowercase-id>`
- **Purpose:** <musical problem or context this asset supports>
- **Linked techniques:** `<technique-id>`
- **Linked songs:** `<song-id>` or none
- **Status:** proposed | manifest-ready | generated | import-verified | maintained

## Musical metadata

- **Key / mode:**
- **Tempo:**
- **Meter:**
- **Feel:**
- **Length / form:**
- **Count-in:**
- **Loop start / end markers:**

## Harmony and form

Use one row per musically meaningful section. The machine-readable manifest should preserve deterministic bar ordering.

| Section | Bars | Progression | Harmonic rhythm | Guitar space / cues |
|---|---:|---|---|---|
| | | | | |

## Instrument roles

Each MIDI track must have a stable, unique name. General MIDI programs are portable hints, not sound dependencies.

| Track | Channel | Role | Register | Articulation | Instrument intent |
|---|---:|---|---|---|---|
| Conductor | — | Tempo, meter, key, markers | — | — | Metadata only |
| Drums | 10 | | | | |
| Bass | | | | | |
| Keys | | | | | |
| Other | | | | | |

## Variants

Keep variants in one manifest when they preserve musical purpose and form.

- **Tempo:**
- **Key:**
- **Density:**
- **Difficulty:**

Create a separate asset when feel, meter, harmonic function, form, or target technique changes materially.

## Portable source

- **Metadata manifest:** `backing-tracks/<id>/manifest.json`
- **MIDI generator:**
- **Generated `.mid`:** `generated/backing-tracks/<variant-id>.mid`
- **Rendered audio:**
- **DAW project:**

The manifest and generator are canonical. Generated artifacts remain ignored unless deliberately promoted with provenance and a reason regeneration is insufficient.

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

- [ ] Manifest fields and section lengths are valid
- [ ] Output is Standard MIDI File Type 1
- [ ] Tempo, meter, and key metadata are present
- [ ] Tracks are separately and uniquely named
- [ ] Section markers match the manifest
- [ ] MIDI structure is not truncated or malformed

### Musical / DAW

- [ ] Tempo, meter, key, and markers import correctly
- [ ] Loop boundaries align to bars and do not cut notes unexpectedly
- [ ] Note ranges are appropriate for assigned instruments
- [ ] The arrangement leaves space for the target guitar part
- [ ] A dry or minimally processed practice version remains available
- [ ] Import verification records the DAW and version

## Promotion

- `manifest-ready`: metadata and arrangement source are complete.
- `generated`: deterministic MIDI generation and automated validation pass.
- `import-verified`: a DAW import confirms metadata, routing, and loop behaviour.
- `maintained`: regeneration and import checks continue to pass after meaningful source changes.
