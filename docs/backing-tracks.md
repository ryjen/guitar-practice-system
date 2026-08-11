# Backing Tracks and MIDI Workflow

## Purpose

Backing tracks are first-class practice assets. They create musical context for a technique without turning a DAW project into the source of truth.

The canonical source is:

1. a human-readable manifest
2. a deterministic generator where practical
3. optional DAW-specific refinement notes

Generated MIDI, rendered audio, and DAW projects are outputs.

## Directory convention

```text
backing-tracks/
  <stable-track-id>/
    manifest.json
    README.md              # optional human notes
scripts/
  midi_workflow.py
  generate_backing_tracks.py
generated/
  backing-tracks/
    <variant-id>.mid       # ignored unless deliberately promoted
```

Use lowercase kebab-case IDs. The ID should describe purpose rather than a particular plugin or DAW.

## Manifest model

Required fields:

- `id` and `title`
- musical purpose
- linked technique and song IDs
- key signature, tempo, meter, feel, and count-in
- ordered sections with one chord symbol per bar
- separately named instrument tracks
- provenance
- output paths

Variants belong in one manifest when they preserve the same musical role and form. Create a separate backing-track asset when the arrangement, feel, meter, harmonic function, or target technique changes materially.

## Source versus output policy

| Artifact | Default policy |
|---|---|
| Manifest | Commit; canonical |
| Generator | Commit; canonical |
| Generated MIDI | Ignore and regenerate |
| Curated MIDI | Commit only when interoperability or manual edits make it independently valuable |
| Rendered audio | Keep outside Git by default |
| DAW project | Optional refinement artifact; never the only source |
| Samples or third-party loops | Do not commit without clear redistribution rights |

A promoted output should include provenance and a reason it cannot be regenerated adequately from source.

## Generate and validate

Generate and validate one asset:

```bash
python scripts/midi_workflow.py generate \
  backing-tracks/slide-slow-blues/manifest.json \
  generated/backing-tracks/slide-slow-blues-a-60.mid

python scripts/midi_workflow.py validate \
  backing-tracks/slide-slow-blues/manifest.json \
  generated/backing-tracks/slide-slow-blues-a-60.mid
```

Generate and validate the entire committed backing-track catalog:

```bash
python scripts/generate_backing_tracks.py
```

The catalog command discovers every `backing-tracks/*/manifest.json`, uses each manifest's canonical `outputs.midi` path, rejects repository-escape/output-name mismatches, regenerates the Type-1 MIDI, and validates it immediately.

Validation checks:

- file format and track count
- separately named tracks
- tempo, meter, and key-signature events
- section markers
- structural integrity of track chunks
- manifest/output ID consistency for catalog generation

Generated `.mid` files remain ignored build artifacts by default.

## MIDI conventions

- PPQN: 480 ticks per quarter note
- Format: Standard MIDI File Type 1
- Track 1: conductor metadata
- Channel 10: drums
- Other roles: distinct melodic channels
- Program changes: General MIDI-compatible hints only
- Instrument choice: assigned in the DAW; not coupled to General MIDI playback
- Count-in: represented as an explicit marker and silent harmonic bar
- Section boundaries: marker events on the conductor track

## DAW assignment and routing

See [backing-track-daw-routing.md](backing-track-daw-routing.md) for the intended instrument assignments, routing, guitar-space rules, and the explicit GarageBand/REAPER verification matrix.

The slide asset has now been successfully imported in both REAPER and GarageBand at its intended 60 BPM. Other catalog assets remain structurally validated but do not need individual cross-DAW verification before they can be used as practice scaffolds.

## DAW import checklist

After import:

1. Confirm tempo, meter, key, and markers.
2. Confirm tracks remain separately named.
3. Assign suitable drum, bass, keyboard, or pad instruments.
4. Route each track independently.
5. Confirm the count-in and section boundaries align to bars.
6. Loop from the intended start marker to `END`.
7. Preserve a dry or minimally processed practice version.
8. Apply humanization only after confirming the source imports correctly.

DAWs interpret some metadata differently. The portable contract is the MIDI file and manifest, not exact plugin patches, mixer state, or articulation maps.

## Current catalog

| ID | Technique | Form | Source/generator status | DAW verification |
|---|---|---|---|---|
| `slide-slow-blues-a-60` | `slide-foundations` | Two 12-bar choruses | Implemented | Verified REAPER + GarageBand |
| `ebow-ambient-bed-d-56` | E-Bow sustain and layering | `DRONE` + `LIFT`, 16 bars | Implemented | Optional |
| `wah-rhythmic-groove-em-96` | rhythmic/expressive wah | `GROOVE-A` + `LEAD-B`, 16 bars | Implemented | Optional |
| `country-i-iv-v-g-100` | hybrid/country picking | I-IV-V + turnaround, 16 bars | Implemented | Optional |
| `country-rock-form-a-108` | country picking + rhythm/fill switching | 28-bar multi-section form | Implemented | Optional |
| `hard-rock-riff-bed-em-112` | muted rhythm articulation | `RIFF-A` + `LIFT-B` + `RIFF-C`, 24 bars | Implemented | Optional |
| `melodic-ballad-bed-g-72` | lead phrasing | `VERSE-A` + `CHORUS-B` + `RESPONSE-C`, 24 bars | Implemented | Optional |

Every committed manifest is exercised as a catalog by `tests/test_midi_workflow.py`; adding another manifest automatically brings it under generation/metadata validation.

## Practice intent

### E-Bow ambient bed

Keep long harmonic windows, restrained support parts, and upper-register space for activation, sustain, string changes, drones, and counter-melodies. Muting the drum track in the DAW is a valid diagnostic variant.

### Wah rhythmic groove

Prioritize an obvious stable pulse over arrangement complexity. The guitar owns subdivision detail; supporting instruments should not compete with busy sixteenth-note figures.

### Country I-IV-V

Use this as the cleaner diagnostic context for alternating bass, hybrid picking, string separation, double-stops, chord-tone targeting, and bend intonation.

### Country-rock form

The named `RHYTHM-A`, `FILL-B`, `RHYTHM-C`, and `TURNAROUND` sections make role switching explicit. The goal is to stop continuous fill-playing and practice leaving arrangement space while moving deliberately between accompaniment and short lead vocabulary.

### Hard-rock riff bed

The support arrangement provides a firm pulse and power-chord landmarks but intentionally does not encode the target guitar riff. Use `RIFF-A` and `RIFF-C` for palm-muted articulation and riff consistency, then use `LIFT-B` for opening the dynamics or switching to fills/lead work. The guitar owns syncopation, muting, accents, and riff identity.

### Melodic ballad bed

Use the long harmonic windows for sustained bends, vibrato, dynamic arcs, call-and-response, delayed entries, early releases, and explicit rests. `RESPONSE-C` is especially useful for leaving one phrase unanswered rather than filling every bar.

## Trade-offs

### Programmatic generation

Advantages:

- reproducible
- diffable source
- parameterized tempo and key variants
- straightforward metadata validation

Limitations:

- nuanced groove and articulation require more explicit modelling
- generated arrangements can sound mechanical
- MIDI does not preserve plugin-specific expression

### Direct DAW authoring

Advantages:

- immediate musical feedback
- easier detailed arranging and sound design
- better access to proprietary articulation and groove tools

Limitations:

- opaque binary source
- poor portability
- difficult deterministic variation
- easy accidental coupling to unavailable plugins

The intended workflow is hybrid: generate a portable scaffold, then refine in the DAW without discarding the manifest.
