# Use Cases

## Overview

The system converts musical intent into repeatable practice. The core value is closing the loop between goals, practice, review, and the next explicit plan.

```mermaid
flowchart TD
    Intent[Musical intent] --> Plan[Practice plan]
    Plan --> Session[Practice session]
    Session --> Log[Session log]
    Log --> Review[Progress review]
    Review --> Next[Next explicit plan]
    Next --> Session
```

## 1. Practice tracking

### Goal

Capture what was practiced, what changed, and what should happen next.

### User story

As a player, I want to log practice sessions quickly so that I can review progress without turning practice into admin work.

### Inputs

- Date and duration
- Focus areas
- Exercises
- Songs or sections
- Tempo ranges
- Notes
- Self-rating or confidence
- Optional recording references

### Outputs

- Session log
- Updated progress history
- Observations for review
- Candidate next steps derived from explicit rules or user choice

### Example

```yaml
practice_session:
  date: 2026-05-27
  duration_minutes: 35
  focus:
    - rhythm
    - wah-control
    - repertoire
  items:
    - type: warmup
      name: chromatic muting warmup
      duration_minutes: 5
    - type: drill
      name: wah sixteenth-note accent drill
      duration_minutes: 10
      tempo_start: 70
      tempo_end: 82
    - type: song_section
      song: example-song
      section: chorus groove
      duration_minutes: 15
  observations:
    - wah timing improves when foot motion follows picking hand accent
    - chorus transition still late above 80 bpm
```

### Acceptance criteria

- A session can be logged quickly
- Freeform notes are allowed
- Structured fields are present where they improve later review
- Logs can reference exercises and repertoire

## 2. Song learning

### Goal

Break songs into learnable sections and track progress toward playable repertoire.

### User story

As a player, I want to track songs by section so that I can focus on the parts that actually need work.

### Core workflow

```mermaid
flowchart LR
    Song[Song] --> Sections[Sections]
    Sections --> Target[Target tempo / feel]
    Target --> Practice[Section practice]
    Practice --> Status[Section status]
    Status --> Repertoire[Repertoire state]
```

### Suggested statuses

- Backlog
- Listening
- Mapping
- Learning
- Playable slowly
- Playable at tempo
- Maintenance
- Retired

### Data to track

- Song title and artist
- Tuning, capo, key, tempo
- Sections
- Current status by section
- External references
- Notes on tone, rhythm, phrasing, or technique

### Acceptance criteria

- A song can be represented without storing copyrighted material directly
- Sections can progress independently
- Repertoire can be reviewed for stale or neglected songs

## 3. Technique drills

### Goal

Maintain reusable drills linked to specific technical outcomes.

### User story

As a player, I want drills organized by technique so that I can target explicit weak areas instead of defaulting to the same comfortable material.

### Technique categories

- Timing and rhythm
- Picking
- Fretting-hand accuracy
- Bends and vibrato
- Slides and legato
- Chord transitions
- Muting and dynamics
- Wah / expression pedal control
- Ear training
- Theory application

### Exercise lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Active: reviewed
    Active --> Modified: adjusted after practice
    Modified --> Active: accepted
    Active --> Retired: no longer useful
    Retired --> Active: revived
```

### Acceptance criteria

- Exercises have a purpose, not just a pattern
- Exercises can include tempo guidance
- Exercises can be created, edited, promoted, or retired
- Practice logs can reference exercises by ID/name

## 4. Warmups

### Goal

Provide short, repeatable warmups matched to the session goal.

### User story

As a player, I want warmups that prepare me for the practice session instead of generic exercises that consume all my energy.

### Warmup types

- General finger mobility
- Timing and subdivision
- Muting and touch
- Picking-hand synchronization
- Chord grip preparation
- Wah/expression coordination
- Low-intensity song-section review

### Example warmup plan

```text
10-minute rhythm/wah warmup

1. 2 min: muted sixteenth-note strums at low tempo
2. 3 min: wah sweep on beats 2 and 4 only
3. 3 min: wah accents on selected sixteenth subdivisions
4. 2 min: apply to one chord vamp with relaxed dynamics
```

### Acceptance criteria

- Warmups are short and time-boxed
- Warmups can be selected from explicit session focus
- Warmups do not become the whole practice session by default

## 5. Deterministic practice-material transformation

### Goal

Create reusable practice artifacts from explicit source specs without hiding musical decisions inside an opaque generator.

### Inputs

- Approved session or exercise spec
- Meter, tempo, subdivision, form, and harmony
- Track or notation structure
- Export format

### Outputs

- MIDI scaffolds
- MusicXML or notation drafts
- DAW import notes
- Backing-track manifests

### Acceptance criteria

- Every output is reproducible from versioned inputs
- Musical intent remains in the source spec
- Generated artifacts are drafts until curated
- Transformation does not infer goals or alter canonical practice state

## 6. Progress review

### Goal

Summarize explicit practice history into useful next actions.

### User story

As a player, I want weekly reviews that show what improved, what stalled, and which recorded facts need attention next.

### Review dimensions

- Time spent by focus area
- Repertoire movement
- Exercises repeated
- Tempo changes
- Confidence changes
- Recurring recorded friction points
- Missed goals
- Explicitly over-practiced or under-practiced areas

### Acceptance criteria

- Review output cites session logs or observations
- Deterministic summaries do not invent missing observations
- Review supports manual edits
- Review avoids fake precision when data is sparse

## 7. Repertoire management

### Goal

Track songs, riffs, sections, and maintenance needs over time.

### User story

As a player, I want to know which songs I am learning, which are playable, and which need maintenance.

### Data to track

- Song/riff/section name
- Artist/source
- Status
- Last practiced
- Last reviewed
- Difficulty
- Key/tuning/capo
- Target tempo
- Current tempo
- Notes
- External references

### Acceptance criteria

- Repertoire can be reviewed by status
- Stale songs can be detected from explicit dates and rules
- Songs can be split into sections
- Maintenance practice can be scheduled deterministically
- External references are linked rather than copied wholesale

## Cross-cutting requirements

### Low-friction capture

The system should minimize typing during or immediately after practice.

### Local-first privacy

Practice history, recordings, and personal notes should be private by default.

### Reviewable transformation

Plans, drills, summaries, and rendered artifacts should remain editable before promotion.

### Explicit inputs

The public core operates only on declared data, rules, and constraints. Missing information remains unknown rather than inferred.

### Portability

The player should be able to export or migrate data without losing practice history.
