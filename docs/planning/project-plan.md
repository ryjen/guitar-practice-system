# Guitar Practice System — Implementation Plan

## Core framing

This repository is a **practice-material generation system**, not a practice tracker.

The purpose is to help generate concrete things to practice:

- MIDI scaffolds
- backing-track structures
- rhythm and bassline prompts
- wah / delay / E-Bow exercises
- GarageBand drummer specs
- Guitar Pro / MuseScore starting points
- song-section practice briefs
- style-specific session prompts

Progress tracking is intentionally secondary. It may exist as lightweight session notes, but it should not become the center of the system.

## Problem statement

Most practice systems drift toward productivity mechanics: streaks, dashboards, analytics, and habit tracking. That can become a distraction from the actual goal: making better musical material and playing more.

This repo solves a narrower problem:

> Given a style, technique, mood, reference, or weakness, quickly generate useful practice material that can be played, looped, arranged, exported, or expanded.

## Phase plan

### Phase 1 — Repo identity

- [x] Replace README with corrected project framing
- [x] Add system overview
- [x] Add practice-material workflow
- [x] Add style map
- [x] Add Mermaid workflow diagram

### Phase 2 — Prompt library

- [x] Add session generator prompt
- [x] Add backing-track generator prompt
- [x] Add MIDI scaffold generator prompt
- [x] Add rhythm groove generator prompt
- [x] Add arrangement expander prompt
- [x] Add Guitar Pro / MuseScore prompt
- [x] Add YouTube playlist/reference prompt

### Phase 3 — Templates

- [x] Add session brief template
- [x] Add song structure template
- [x] Add backing-track spec template
- [x] Add MIDI sketch spec template
- [x] Add GarageBand drummer spec template
- [x] Add lightweight review template

### Phase 4 — Examples

- [x] Add U2-style wah/delay session
- [x] Add post-punk driving bass session
- [x] Add E-Bow ambient session
- [x] Add GarageBand drummer example
- [x] Add MIDI scaffold example

### Phase 5 — MIDI and notation workflow

- [x] Keep specs source-first
- [x] Ignore bulk generated artifacts
- [x] Promote only curated MIDI or notation artifacts
- [x] Add MusicXML / MuseScore / Guitar Pro guidance

### Phase 6 — Optional lightweight review

- [x] Add review boundary doc
- [x] Keep review to three prompts
- [x] Link review output back to generation

## Decisions

### Generated MIDI

Use source specs and generator code as canonical. Generated files should go under `generated/` and be ignored by default. Curated MIDI can be promoted later into `midi/curated/` with a matching Markdown source note.

### First workflow

Use a prompt-first UX with small CLI helpers. Prompts generate session briefs and scaffold specs; scripts generate artifacts from accepted specs.

### GarageBand target

GarageBand should be the primary worked example, but the underlying model should stay DAW-neutral.

### Notation target

Use Markdown specs now, likely MusicXML-first later. MuseScore and Guitar Pro should be consumers, not canonical formats.

### YouTube references

AI may suggest candidates, but only human-curated references should be promoted into repo docs.

### Style scope

Start with:

- U2 / rhythmic delay
- post-punk driving bass
- ambient / E-Bow
- expressive wah

Adjacent future lanes:

- shoegaze
- new wave
- goth rock
- krautrock
- cinematic western
- art rock

### Gear specificity

Gear-aware but optional. Describe musical intent first, gear second.

### Review layer

Optional lightweight review only:

```text
What was useful?
What should change?
What should be generated next?
```

### Fragment vs song

Use a fragment-to-arrangement workflow. Generate riffs, loops, drones, and grooves first; expand promising fragments into song forms.

### Artist references

Use references only to extract actionable traits, not to imitate directly.
