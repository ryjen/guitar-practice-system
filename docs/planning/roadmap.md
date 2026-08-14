# Roadmap

## Current status

Public reference core with active deterministic practice, evidence, timing, catalog, scheduling, assessment, and artifact-generation workflows.

The software-contract baseline is substantially implemented. The current project risk is no longer missing architecture; it is whether the model, handoffs, and generated practice material remain useful in real playing sessions.

The roadmap covers only independently useful public capabilities. Private product direction and implementation details remain out of scope.

## Current milestone

**M3: Real-session validation** is the active milestone.

M1 practice/progression contracts, M2 evidence/assessment contracts, and the initial M4 deterministic catalog workflow have working versioned implementations with deterministic tests and CI coverage. They should receive bounded fixes when evidence finds a defect, not remain permanent "stabilization" projects.

The two near-term engineering dependencies that may proceed alongside M3 are:

- **#89** — unify static analysis and CI trust gates;
- **#83** — add the minimal tonal-centre-aware modal request/catalog boundary needed for Dorian and Mixolydian backing tracks.

## Near-term sequence

1. Execute the first canonical real-session validation through **#87 / #4** using `slide-slow-blues-a-60`.
2. Complete **#89** so material repository changes receive consistent static-analysis, public-boundary, and pinned-action validation.
3. Complete **#83** for deterministic D Dorian and G Mixolydian backing-track semantics without conflating tonal centre and MIDI key signature.
4. Continue **#87** through wah and E-Bow sessions; use repeated playing friction to drive only necessary docs/spec/code changes.
5. Expand **#85** from the validated Dorian/Mixolydian pattern rather than implementing all seven modes in one slice.
6. Keep **#67** versioned release packaging planned until a concrete public distribution need justifies moving it into P1.

## Milestones

### M1: Practice and progression contracts — implemented baseline

Delivered capabilities include:

- practice-session workflow and reusable session structures;
- goals and active-work state;
- maintenance and due-state rules;
- explicit dependency relationships;
- deterministic schedule proposal and approval contracts;
- replay, timezone, idempotency, and stale-state semantics;
- normalized scheduling v2 aligned with canonical progression states.

Baseline expectations:

- the same versioned state, rules, and clock produce the same proposal;
- missed sessions and maintenance are representable without hidden inference;
- canonical state changes remain approval-gated.

Future changes should be driven by concrete defects, compatibility needs, or real-session evidence.

### M2: Evidence and assessment contracts — implemented baseline

Delivered capabilities include:

- versioned evidence structures;
- explicit observations;
- quality-gate definitions;
- pass/fail/unknown/blocked/not-applicable outcomes;
- deterministic comparison and transition proposals;
- provenance and approval semantics;
- reproducible assessment fixtures and CI validation.

Baseline expectations:

- gate outcomes are reproducible from explicit inputs;
- missing evidence remains unknown rather than becoming an inferred failure;
- progression proposals preserve provenance and require approval.

Future changes should preserve those properties and avoid turning musical judgment into false aggregate precision.

### M3: Real-session validation — active

Goal: ensure the practice model helps actual playing rather than expanding ontology indefinitely.

Primary executable work is **#87**, beginning with the slide session in **#4**.

Deliverables:

- representative slide, wah, E-Bow, and optional country sessions;
- pre-drill baseline, largest-defect isolation, musical reintegration, and comparable verification;
- captured deviations and fatigue/stop observations;
- evidence records linked to session context;
- explicit review of timing, phrasing, dynamics, and **space** where relevant;
- at least one evidence → assessment → explicit approval decision → scheduling handoff exercised end to end;
- documentation/spec fixes only where repeated friction appears.

Exit criteria:

- at least three representative real sessions have been completed;
- at least one full deterministic lifecycle handoff has been exercised;
- repeated modeling or workflow friction has either been resolved or converted into bounded follow-up work;
- the capture/review overhead remains proportionate to actual playing time.

### M4: Deterministic catalog workflows — implemented baseline

Goal: support repository-local discovery without opaque ranking.

Delivered capabilities include:

- explicit filtering and scoring rules;
- source/provenance fields;
- deterministic candidate ordering;
- synthetic fixtures;
- approval boundaries before practice-state mutation;
- adaptive-session generation from explicit inputs.

Future work should be based on concrete discovery failures, missing catalog data, or real-session usability evidence rather than adding opaque ranking sophistication.

### M5: Music artifact workflows — active / partial

Goal: connect source specs to actual music-making tools while keeping sources portable.

Implemented baseline includes:

- deterministic Type-1 MIDI generation;
- backing-track, groove, bass, and progression contracts/engines;
- deterministic practice-progression variants;
- reproducible public artifact bundles with provenance and checksums;
- source-first generated-output policy;
- successful REAPER and GarageBand import/play verification for the canonical slide backing track.

Remaining candidate integrations include:

- additional real DAW/play-through verification for wah, E-Bow, country, and modal tracks;
- MusicXML / MuseScore / Guitar Pro references where they solve a concrete practice need;
- local recording references;
- calendar-compatible schedule export;
- explicit versioned GitHub Release packaging under #67 when distribution is needed.

Definition of done for any promoted integration:

- it attaches a useful practice artifact or reference;
- core practice data remains portable;
- generated artifacts can be reproduced from explicit sources;
- the result has been validated in the actual target workflow where practical;
- copyrighted tabs, lyrics, recordings, or unauthorized derivative material are not committed accidentally.

## Validation and delivery

The repository should keep validation layered and risk-based:

- fast deterministic unit/component tests at the base;
- targeted contract/integration tests at scheduling, assessment, discovery, request/catalog, and MIDI boundaries;
- small real-workflow checks for DAW import, actual practice sessions, and public Pages behavior where automation cannot prove usefulness;
- static analysis and consistent CI trust gates as tracked by #89.

Ordinary CI remains read-only and ephemeral. Generated binaries are not canonical source and should not be uploaded as ordinary Actions artifacts.

## Runtime options

The public core may remain a combination of:

- Markdown/YAML/JSON plus scripts;
- CLI plus local files;
- SQLite-backed local tooling where persistent local state becomes justified;
- static web documentation and practice surfaces.

Decision criteria:

- capture friction;
- deterministic replay;
- data portability;
- privacy posture;
- maintenance cost;
- ease of validation.

Do not add a runtime layer solely because the project has enough implementation to support one.

## Public scope

The public core should support:

- practice goals and sessions;
- repertoire and technique references;
- deterministic scheduling and maintenance;
- evidence and gate evaluation;
- metronome/timing realizations;
- deterministic catalog filtering;
- source-first MIDI, notation, and backing-track transformations;
- import/export and conformance fixtures;
- deterministic domain contracts that remain independently useful to public consumers.

## Out of scope

- opaque recommendation or ranking logic;
- inferred weaknesses or intent;
- opaque external recommendation services;
- private personalization or product experiments;
- user accounts, billing, entitlement, or marketplace behavior;
- autonomous mutation of canonical progress.

## Open questions

- Which remaining public concepts genuinely need stable machine-readable schemas versus Markdown-only guidance?
- Which deterministic workflows justify CLI support after real-session use?
- What observations are useful without creating false precision or aggregate proficiency scores?
- Which generated artifacts deserve promotion to canonical curated assets after real DAW/session validation?
- When does explicit versioned public release packaging provide enough consumer value to promote #67 to P1?
