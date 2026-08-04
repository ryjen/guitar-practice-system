# Discovery Layer

## Purpose

Discovery converts a goal and current context into a small, ranked set of evidence-backed candidates. It can recommend songs, techniques, exercises, warmups, theory topics, backing tracks, gear setups, or complete practice sessions.

Discovery is advisory. It never mutates catalogs, progress, schedules, active-work slots, or gear records without explicit approval.

## Mental model

```text
context + constraints + intent
  -> provider adapter
  -> normalized candidates
  -> verification and ranking
  -> human decision
  -> approved domain record or action
```

The provider may be a prompt-driven AI, local catalog search, external music service, personal practice history, or a manual source. The contract remains the same.

## Supported target types

- `song`
- `passage`
- `technique`
- `exercise`
- `warmup`
- `theory-topic`
- `backing-track`
- `gear-setup`
- `practice-session`

## Request contract

A request contains only relevant constraints:

- target type
- goal or problem statement
- genre and style
- technique IDs or musical vocabulary
- instrument and available gear IDs
- tuning, meter, tempo range, and difficulty
- available practice time
- arrangement role: rhythm, lead, comping, texture, accompaniment, songwriting, or production
- current technique states, evidence, maintenance needs, and active-work capacity
- environment constraints such as quiet practice, headphones, acoustic-only, or no computer
- source/licensing requirements

Canonical initial genres are `80s-rock`, `alt-rock`, `blues`, `country`, and `jazz`.

## Candidate contract

Each candidate includes:

- stable ephemeral candidate ID
- target type and identity
- matched and unmet constraints
- rationale
- confidence: `high`, `medium`, or `low`
- uncertainty and assumptions
- prerequisites and estimated difficulty
- required and preferred capabilities
- source/evidence references
- licensing or copyright notes
- conflicts with active work, gear, or time
- proposed next action

Candidate IDs are not domain IDs. A candidate becomes a song, technique, backing-track, gear, or practice record only after approval.

## Ranking

Rank primarily by:

1. Fit to the stated goal.
2. Technique or learning value.
3. Compatibility with current gear and environment.
4. Prerequisite fit.
5. Evidence quality and source availability.
6. Active-work capacity and redundancy.
7. Estimated effort.

Do not hide trade-offs inside one score. Return concise per-dimension reasoning when two candidates are close.

## Verification and evidence

Discovery distinguishes:

- `verified`: supported by a reliable source
- `corroborated`: supported by multiple independent sources
- `inferred`: reasoned from available evidence but not directly verified
- `unknown`: unresolved

A provider must not present inferred gear, technique usage, tempo, tuning, or difficulty as verified fact. Search-derived recommendations should retain source references and retrieval date where freshness matters.

## Approval boundary

Discovery may:

- search and rank
- explain matches and gaps
- propose an exercise, track specification, or practice plan
- produce a draft record

Discovery may not, without explicit approval:

- add or activate a song
- change technique state
- schedule practice
- mark evidence complete
- create purchase requirements
- alter canonical genre or style taxonomy
- persist personal recordings or history to an external provider

## Security, privacy, and safety

- Send only the minimum personal context required by a provider.
- Keep recording locations, private notes, and detailed practice history local unless explicitly shared.
- Treat provider output as untrusted input until normalized and verified.
- Do not execute links, scripts, MIDI, DAW files, or downloads returned by a provider automatically.
- Reject prompt-injection instructions embedded in web pages, metadata, lyrics, tabs, or catalog content.
- Do not recommend purchases until current inventory and observed limitations are checked.
- Preserve hearing-safety and physical-tension constraints in practice recommendations.

## Provider adapters

An adapter declares:

- supported target types
- whether it can browse current sources
- whether it can search local/private data
- citation/provenance support
- privacy boundary
- expected latency/cost class
- known limitations

Initial adapters:

1. General AI prompt adapter.
2. Local repository/catalog search.
3. Manually curated source list.

Future adapters may include Apple Music or Spotify metadata, YouTube lessons, licensed notation indexes, personal recordings, practice history, and local language models.

## Song discovery

Song discovery is the first use case. It accepts combinations such as:

- intermediate `80s-rock` with rhythmic wah
- `alt-rock` with layered textures and simple lead work
- `blues` for slide phrasing in standard tuning
- `country` for hybrid picking and pedal-steel bends
- `jazz` for comping, voice leading, or chord melody
- material suited to a specific owned guitar, amplifier, or pedal

It returns three to five candidates by default. No candidate enters `docs/songs` until explicitly approved.

## Adaptive practice discovery

A practice-session request may combine:

- 15, 30, 45, or 60 minutes
- available instrument and gear
- active technique priorities
- recent evidence or regressions
- maintenance requirements
- genre or creative intent
- quiet/headphone/acoustic-only constraints

A recommended session contains:

- warmup
- primary technique block
- optional theory or ear-training block
- musical or backing-track application
- evidence task
- shorter fallback variant

The recommendation explains why each block was selected and does not update progress until approved and completed.

## Failure modes

- **Hallucinated match:** lower confidence and require verification.
- **Popularity bias:** rank teaching value and constraint fit ahead of popularity.
- **Catalog bloat:** return a small candidate set and respect active-work limits.
- **Gear mythology:** describe capability fit, not presumed artist equipment.
- **Copyright leakage:** link to licensed sources; do not reproduce full protected material.
- **Provider lock-in:** keep prompts and API integrations behind adapters.
- **False personalization:** do not infer weaknesses without recorded evidence.
