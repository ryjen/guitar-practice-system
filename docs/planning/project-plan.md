# Guitar Practice System — Implementation Plan

## Core framing

This repository is a **source-first practice-material system**.

The purpose is to help create concrete things to practice from explicit musical decisions:

- MIDI scaffolds
- backing-track structures
- rhythm and bassline specs
- wah / delay / E-Bow exercises
- GarageBand drummer specs
- Guitar Pro / MuseScore starting points
- song-section practice briefs
- style-specific session plans

Progress tracking exists only where it helps choose and validate useful musical work.

## Problem statement

Many practice systems drift toward streaks, dashboards, analytics, and habit mechanics. This repo solves a narrower problem:

> Given an explicit style, technique, musical goal, or recorded weakness, create useful practice material that can be played, looped, arranged, exported, reviewed, and reproduced.

## Phase plan

### Phase 1 — Repository identity

- [x] Define project framing
- [x] Add system overview
- [x] Add practice-material workflow
- [x] Add style map and workflow diagrams

### Phase 2 — Source templates

- [x] Add session brief template
- [x] Add song structure template
- [x] Add backing-track spec template
- [x] Add MIDI sketch spec template
- [x] Add GarageBand drummer spec template
- [x] Add lightweight review template
- [x] Add technique, rhythm, progression, timing, and evidence templates

### Phase 3 — Worked examples

- [x] Add representative wah, slide, E-Bow, rhythm, harmony, and backing-track examples
- [x] Add GarageBand drummer and MIDI scaffold examples
- [x] Add odd-meter and metronome-realization examples

### Phase 4 — Deterministic transformations

- [x] Keep specs source-first
- [x] Ignore bulk generated artifacts
- [x] Promote only curated MIDI or notation artifacts
- [x] Add MusicXML / MuseScore / Guitar Pro guidance
- [ ] Expand deterministic render/validation helpers only where stable source formats justify them

### Phase 5 — Practice state and assessment

- [ ] Add deterministic long-term scheduling and maintenance contracts
- [ ] Add versioned evidence gates and transition proposals
- [ ] Add replay, stale-state, timezone, and idempotency semantics
- [ ] Validate the model with real practice sessions

### Phase 6 — Deterministic catalog discovery

- [x] Add repository catalog and request/candidate contracts
- [ ] Ensure ranking is explicit, versioned, and reproducible
- [ ] Preserve unknown metadata rather than inferring it
- [ ] Add stable tie-breaking and compatibility fixtures

## Decisions

### Generated MIDI

Use source specs and generator code as canonical. Generated files should go under `generated/` and be ignored by default. Curated MIDI can be promoted later with a matching source note.

### Workflow

Use explicit source specs with small deterministic CLI helpers. Scripts may render or validate accepted specs, but musical intent must remain visible in the source.

### GarageBand target

GarageBand is a useful worked example, while the underlying model stays DAW-neutral.

### Notation target

Use Markdown specs now and interoperable notation formats where useful. MuseScore and Guitar Pro are consumers, not canonical formats.

### External references

Only human-curated or explicitly imported references should be promoted into repository docs. Store metadata and lawful links rather than protected source material.

### Gear specificity

Gear-aware but optional. Describe musical intent first, gear second.

### Review layer

Keep review bounded and actionable:

```text
What was useful?
What should change?
What should be practised or created next?
```

### Fragment vs song

Use a fragment-to-arrangement workflow. Create riffs, loops, drones, grooves, and transitions first; expand promising fragments into song forms.

### Artist references

Use references only to extract documented musical traits and practice context, not to reproduce protected material.
