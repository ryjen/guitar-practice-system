# Deterministic Catalog Discovery

## Purpose

Discovery in the public core means reproducible search, filtering, normalization, and ranking over explicit catalogs. It helps locate songs, techniques, exercises, warmups, theory topics, backing tracks, gear setups, or practice-session candidates without mutating canonical state.

## Mental model

```text
explicit request + explicit catalog + versioned ranking rules
  -> filter
  -> normalize
  -> deterministic score/order
  -> candidate set
  -> human decision
  -> approved domain record or action
```

The same request, catalog version, and ranking rules must produce the same candidate ordering.

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

A request contains only relevant explicit constraints:

- target type
- goal or problem statement
- genre and style
- technique IDs or musical vocabulary
- instrument and available gear IDs
- tuning, meter, tempo range, and difficulty
- available practice time
- arrangement role
- approved technique states and maintenance needs
- active-work capacity
- environment constraints
- source/licensing requirements

## Candidate contract

Each candidate includes:

- stable ephemeral candidate ID
- target type and identity
- matched and unmet constraints
- deterministic per-dimension scores or ordering reasons
- prerequisites and declared difficulty
- required and preferred capabilities
- source/provenance references
- licensing or copyright notes
- conflicts with active work, gear, or time
- proposed next action

Candidate IDs are not domain IDs. A candidate becomes a persistent record only after approval.

## Ranking

Ranking rules must be explicit, versioned, and inspectable. A default ordering may consider:

1. hard-constraint satisfaction
2. fit to the stated goal
3. technique or learning value declared in catalog metadata
4. compatibility with current gear and environment
5. prerequisite fit
6. active-work capacity and redundancy
7. declared effort or difficulty
8. stable tie-break key

Do not hide trade-offs inside an undocumented score. Candidate output should retain enough information to reproduce why one item sorted ahead of another.

## Provenance

Catalog records distinguish:

- repository-owned metadata
- imported external metadata with source reference
- user-supplied metadata
- unresolved fields

Unknown values remain unknown. The public core must not infer missing gear, technique usage, tempo, tuning, difficulty, or stylistic fit.

## Approval boundary

Discovery may:

- search and filter
- normalize catalog records
- compute documented deterministic rankings
- explain matched and unmet constraints
- produce a draft candidate record

Discovery may not, without explicit approval:

- add or activate a song
- change technique state
- schedule practice
- mark evidence complete
- create purchase requirements
- alter canonical genre or style taxonomy

## Local repository adapter

The repository adapter searches versioned catalog data and applies deterministic normalization/ranking rules.

Example:

```bash
python scripts/discovery_catalog.py search \
  examples/discovery/slide-backing-track-request.json \
  catalogs/discovery/repository.json
```

Tests should prove stable ordering, hard-constraint filtering, unknown-field handling, and tie-breaking.

## Practice-session candidates

A session request may include:

- 15, 30, 45, or 60 minutes
- available instrument and gear
- explicit active technique priorities
- approved evidence or maintenance state
- genre or creative intent
- quiet/headphone/acoustic-only constraints

A deterministic session candidate may contain:

- warmup
- primary technique block
- optional theory or ear-training block
- musical or backing-track application
- evidence task
- shorter fallback variant

The selection rationale must come from declared rules and inputs, and completion never updates progress automatically.

## Failure modes

- **Unstable ordering:** require stable tie-break rules and versioned fixtures.
- **Unknown metadata treated as false:** preserve `unknown` explicitly.
- **Catalog bloat:** return a bounded candidate set.
- **Gear mythology:** use declared capability metadata only.
- **Copyright leakage:** store metadata and lawful references, not protected full material.
- **State leakage:** discovery remains read-only until a separate approved action applies a candidate.
