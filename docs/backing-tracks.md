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

```bash
python scripts/midi_workflow.py generate \
  backing-tracks/slide-slow-blues/manifest.json \
  generated/backing-tracks/slide-slow-blues-a-60.mid

python scripts/midi_workflow.py validate \
  backing-tracks/slide-slow-blues/manifest.json \
  generated/backing-tracks/slide-slow-blues-a-60.mid
```

The command generates a Standard MIDI File Type 1 and immediately validates:

- file format and track count
- separately named tracks
- tempo, meter, and key-signature events
- section markers
- structural integrity of track chunks

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

## DAW import checklist

After import:

1. Confirm tempo, meter, key, and markers.
2. Confirm tracks remain separately named.
3. Assign suitable drum, bass, and keyboard instruments.
4. Route each track independently.
5. Confirm the count-in and section boundaries align to bars.
6. Loop from the intended start marker to `END`.
7. Preserve a dry or minimally processed practice version.
8. Apply humanization only after confirming the source imports correctly.

DAWs interpret some metadata differently. The portable contract is the MIDI file and manifest, not exact plugin patches, mixer state, or articulation maps.

## Initial catalog

| ID | Technique | Form | Status |
|---|---|---|---|
| `slide-slow-blues-a-60` | `slide-foundations` | Two 12-bar choruses | Implemented |
| `wah-rhythmic-groove` | rhythmic wah | Short loop plus full form | Planned |
| `ebow-ambient-bed` | E-Bow sustain and layering | Evolving modal bed | Planned |
| `country-i-iv-v` | hybrid and country picking | Loop plus turnaround form | Planned |
| `hard-rock-riff-bed` | muted rhythm articulation | Riff sections | Planned |
| `melodic-ballad-bed` | lead phrasing | Verse/chorus form | Planned |

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
