# Roadmap

## Current status

Public reference core with active deterministic practice, evidence, timing, catalog, scheduling, assessment, and artifact-generation workflows.

The software-contract baseline is substantially implemented. The current project risk is no longer missing architecture; it is whether the model, handoffs, and generated practice material remain useful in real playing sessions.

The roadmap covers only independently useful public capabilities. Private product direction and implementation details remain out of scope.

## Current milestone

**M3: Real-session validation** is the active milestone.

M1 practice/progression contracts, M2 evidence/assessment contracts, and the initial M4 deterministic catalog workflow have working versioned implementations with deterministic tests and CI coverage. They should receive bounded fixes when evidence finds a defect, not remain permanent "stabilization" projects.

The previous engineering dependencies are complete: **#83/#89** established modal and common validation foundations; **#94/#97/#100** completed the stable package-native `guitarctl` migration; and **#109–#115** established the canonical Score IR-derived import, notation, playback, and editing workflows. The deprecated scheduling v1 compatibility path remains deliberately isolated.

The bounded **M5 music-artifact software baseline** now includes score-backed MIDI/RC-3 workflows, the independently conformed guitar-DSP preset v1 contract (**#152/#158**), and deterministic versioned release packaging (**#67**, PR #163). The release machinery is implemented, **but no versioned GitHub Release has been published**. Neither software completion nor reproducible MIDI establishes actual musical usefulness; M3 remains the controlling practice milestone.

## Near-term sequence

1. **Play and record** the canonical M3 slide session under **#87 / #4**, using `examples/real-sessions/slide-m3-session.md` and only `PRACTICE-A` of `slide-slow-blues-a-60` for the first 12-bar reintegration take. Capture baseline, dominant defect, isolation work, comparable verification, fatigue/deviations, and a lightweight evidence record.
2. Continue **#87** with the documented wah (**#5**) and E-Bow (**#6**) run sheets. Exercise evidence → assessment → explicit approval decision → scheduling at least once. Do not infer outcomes from unplayed run sheets.
3. Reconcile recorded M3 friction under **#22** and the relevant technique issues. Expand seven-mode practical coverage (**#85**) only after validating the existing Dorian/Mixolydian examples by ear and in playing context.
4. Keep optional bounded DSP measurement ingestion (**#162**) deferred until a real session identifies a measurement that cannot be captured adequately with the current manual evidence path.
5. Reconcile completed-work documentation (**#164**) and review flake-first CI/runner trust and cost alignment (**#165**) independently of physical practice work. Preserve the existing verified checks until an equivalent replacement is proven.
6. Decide whether to create the first versioned GitHub Release when a public distribution need exists. The tag-triggered release pipeline is ready; publication is an explicit follow-up, not an M3 prerequisite.

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

### M5: Music artifact workflows — implemented software baseline; real-workflow qualification ongoing

Goal: connect source specs to actual music-making tools while keeping sources portable.

Implemented baseline includes:

- canonical versioned Score IR with deterministic validation/serialization;
- deterministic Type-1 MIDI generation;
- backing-track, groove, bass, and progression contracts/engines;
- deterministic practice-progression variants;
- reproducible public artifact bundles with provenance and checksums;
- source-first generated-output policy;
- successful REAPER and GarageBand import/play verification for the canonical slide backing track;
- canonical Score IR authoring, Guitar Pro/MusicXML import, deterministic MusicXML/MIDI export, guided editing, and bounded playback;
- score-derived no-guitar backing and BOSS RC-3 drum-loop export;
- independently validated `guitar-dsp.preset` v1 producer with a shared 199-byte fixture;
- deterministic versioned bundle preparation and verification, with tag-triggered publication automation (not yet exercised on a public release).

Remaining evidence and candidate integrations include:

- actual slide, wah, and E-Bow practice sessions with comparable recorded takes under #87, and additional real DAW/play-through verification where the generated assets are used;
- broader user-workflow compatibility observations from MuseScore, MusicXML, and Guitar Pro sources beyond deterministic fixtures;
- local recording references and calendar-compatible schedule export only when practice friction justifies them;
- first tagged GitHub Release publication when deliberately authorized and useful to consumers.

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
- static analysis and the existing consistent CI trust baseline delivered by #89; flake-first ownership, runner placement and cost reconciliation are separately tracked by #165.

Ordinary CI remains read-only and ephemeral. Generated binaries are not canonical source and should not be uploaded as ordinary Actions artifacts.

## Runtime options

The public core may remain a combination of:

- Markdown/YAML/JSON plus the packaged `guitarctl` CLI (historical scripts are compatibility shims);
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
- When should the already implemented versioned release machinery publish its first deliberately tagged public release?
