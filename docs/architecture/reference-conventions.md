# Reference Conventions

## Purpose

Markdown remains the source of truth, but reusable concepts need stable references so exercises, sessions, songs, backing tracks, gear setups, and evidence do not duplicate definitions.

## Identifier format

Use lowercase kebab-case IDs with a domain prefix:

- `technique-slide-intonation`
- `song-people-get-ready-jeff-beck`
- `progression-jazz-ii-v-i`
- `rhythm-seven-eight-223`
- `warmup-slide-intonation-low-fatigue`
- `gear-slide-clean-delay`
- `backing-track-e-dorian-seven-eight`
- `session-expressive-dorian-call-response`

IDs describe identity, not mutable state. Do not encode tempo, progress state, dates, or file locations unless they are intrinsic to the concept.

## Reference rules

1. Define shared musical information once and reference its ID elsewhere.
2. Prefer an explicit relative Markdown link when a canonical document exists.
3. Keep a plain ID beside the link when the reference may later be machine-validated.
4. A missing optional reference means unconstrained or not applicable, not unknown.
5. Record explicit unknowns separately when uncertainty matters.
6. Do not copy complete chord progressions, rhythm definitions, gear chains, or technique quality gates into every consumer.
7. Consumer documents may override realization details without changing the referenced identity.

## Reference shape

Use concise lists in Markdown:

```markdown
- **Technique IDs:** `technique-bend-intonation`, `technique-wide-vibrato`
- **Progression ID:** `progression-a-dorian-vamp`
- **Rhythm ID:** `rhythm-seven-eight-223`
- **Gear setup ID:** `gear-atmospheric-lead`
```

When a local file exists:

```markdown
- **Progression:** [`progression-jazz-ii-v-i`](../progressions/jazz-ii-v-i.md)
```

## Identity versus realization

A reusable object owns identity and general structure. A consumer may supply realization details:

- A progression owns abstract harmonic movement; a backing track chooses key, voicings, tempo, and arrangement.
- A rhythm owns meter, grouping, and groove intent; an exercise chooses tempo and note material.
- A warmup owns preparation logic; a session chooses duration and target task.
- A technique owns progression and quality gates; a song section supplies musical context.

## Relationship direction

Prefer references from the consuming artifact to the reusable definition. Reverse indexes may be generated or maintained manually only when they materially improve navigation.

## Lifecycle

- IDs should remain stable after use.
- Rename display titles freely when meaning is unchanged.
- If meaning changes materially, create a new ID and record the relationship.
- Mark deprecated concepts explicitly; do not silently reuse their IDs.

## Validation boundary

Do not add a schema or database yet. Introduce lightweight checks only after several real records reveal repeated broken links, duplicate IDs, or inconsistent fields.
