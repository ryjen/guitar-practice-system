# Roadmap

## Current status

Public reference core with active deterministic practice, evidence, timing, catalog, and artifact-generation workflows.

The roadmap covers only independently useful public capabilities. Private product direction is intentionally out of scope.

## Near-term sequence

1. Stabilize deterministic practice scheduling and long-term progression contracts.
2. Stabilize deterministic evidence assessment and progression gates.
3. Exercise the multidimensional practice model through real sessions.
4. Keep timing/metronome realizations integrated with session and evidence records.
5. Improve deterministic repository-catalog filtering and candidate normalization.
6. Validate MIDI, notation, backing-track, and DAW-neutral source workflows.

## Milestones

### M1: Practice and progression contracts

Deliverables:

- practice session schema
- goals and active-work state
- maintenance and due-state rules
- explicit dependency relationships
- deterministic schedule proposal and approval contracts
- replay, timezone, idempotency, and stale-state semantics

Definition of done:

- the same versioned state, rules, and clock produce the same proposal
- missed sessions and maintenance are representable without hidden inference
- canonical state changes remain approval-gated

### M2: Evidence and assessment contracts

Deliverables:

- versioned evidence schema
- explicit observations
- quality-gate definitions
- pass/fail/unknown/blocked/not-applicable outcomes
- immutable comparison and transition proposals
- deterministic replay and supersession semantics

Definition of done:

- gate outcomes are reproducible from explicit inputs
- missing evidence remains unknown rather than becoming an inferred failure
- progression proposals preserve provenance and require approval

### M3: Real-session validation

Goal: ensure the practice model helps actual playing rather than expanding ontology indefinitely.

Deliverables:

- representative slide, wah, E-Bow, country, rhythm, and theory sessions
- captured deviations and fatigue/stop observations
- evidence records linked to session context
- documentation fixes where repeated friction appears

### M4: Deterministic catalog workflows

Goal: support repository-local discovery without opaque ranking.

Deliverables:

- explicit filter and scoring rules
- source/provenance fields
- deterministic candidate ordering
- synthetic fixtures
- approval boundary before catalog or practice-state mutation

### M5: Music artifact workflows

Goal: connect source specs to actual music-making tools while keeping sources portable.

Candidate integrations:

- GarageBand drummer notes
- MIDI exercise export
- MusicXML / MuseScore / Guitar Pro references
- local recording references
- calendar-compatible schedule export

Definition of done:

- integrations attach useful artifacts or references
- core practice data remains portable
- generated artifacts can be reproduced from explicit sources
- copyrighted tabs, lyrics, or recordings are not committed accidentally

## Runtime options

The public core may remain a combination of:

- Markdown/YAML plus scripts
- CLI plus local files
- SQLite-backed local tooling
- static web documentation

Decision criteria:

- capture friction
- deterministic replay
- data portability
- privacy posture
- maintenance cost
- ease of validation

## Public scope

The public core should support:

- practice goals and sessions
- repertoire and technique references
- deterministic scheduling and maintenance
- evidence and gate evaluation
- metronome/timing realizations
- deterministic catalog filtering
- source-first MIDI, notation, and backing-track transformations
- import/export and conformance fixtures

## Out of scope

- opaque recommendation or ranking logic
- inferred weaknesses or intent
- opaque external recommendation services
- private personalization or product experiments
- user accounts, billing, entitlement, or marketplace behavior
- autonomous mutation of canonical progress

## Open questions

- Which public contracts need stable machine-readable schemas versus Markdown-only guidance?
- Which deterministic workflows justify CLI support?
- What metrics are useful without creating false precision?
- Which catalog-ranking dimensions are explicit enough to remain reproducible?
- Which generated artifacts deserve promotion to canonical curated assets?
