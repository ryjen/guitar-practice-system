# Reference Conventions

## Purpose

Markdown remains the source of truth, but reusable concepts need stable references so exercises, sessions, songs, backing tracks, gear setups, and evidence do not duplicate definitions.

## Identifier format

Use stable lowercase kebab-case IDs.

A domain prefix is recommended for new reusable concepts when the ID may appear outside a typed field or collide with another domain:

- `progression-jazz-ii-v-i`
- `rhythm-seven-eight-223`
- `warmup-slide-intonation-low-fatigue`
- `gear-slide-clean-delay`
- `backing-track-e-dorian-seven-eight`
- `session-expressive-dorian-call-response`

Existing stable IDs remain valid. Do not rename an established ID merely to add a prefix. For example, an existing technique ID such as `slide-single-note-intonation` remains canonical after these conventions are adopted.

Typed fields provide namespace context, so both of these are unambiguous:

```markdown
- **Technique ID:** `slide-single-note-intonation`
- **Progression ID:** `progression-jazz-ii-v-i`
```

IDs describe identity, not mutable state. Do not encode tempo, progress state, dates, file locations, or session-specific settings unless they are intrinsic to the concept.

## Reference rules

1. Define shared musical information once and reference its ID elsewhere.
2. Prefer an explicit relative Markdown link when a canonical document exists.
3. Keep a plain ID beside the link when the reference may later be machine-validated.
4. A missing optional reference means unconstrained or not applicable, not unknown.
5. Record explicit unknowns separately when uncertainty matters.
6. Do not copy complete chord progressions, rhythm definitions, gear chains, or technique quality gates into every consumer.
7. Consumer documents may override realization details without changing the referenced identity.
8. Do not write session-specific overrides back into the reusable source unless they redefine the concept itself.

## Reference shape

```markdown
- **Technique IDs:** `bend-intonation`, `wide-controlled-vibrato`
- **Progression ID:** `progression-a-dorian-vamp`
- **Rhythm ID:** `rhythm-seven-eight-223`
- **Gear setup ID:** `gear-atmospheric-lead`
```

When a local file exists:

```markdown
- **Progression:** [`progression-jazz-ii-v-i`](../progressions/jazz-ii-v-i.md)
```

## Identity versus realization

- A progression owns abstract harmonic movement; a backing track or session chooses key, voicings, tempo, and arrangement unless those are intrinsic to the progression.
- A rhythm owns meter, grouping, groove intent, and reusable space behaviour; an exercise or session chooses actual tempo and note material.
- A warmup owns preparation logic and safety boundaries; a session chooses the target task, duration, and adaptation.
- A technique owns progression and quality gates; a song section supplies musical context.

A consumer override does not create a new reusable identity. Create a new ID only when the musical meaning, grouping, function, or preparation logic changes materially.

## Lifecycle

- IDs remain stable after use.
- Display titles may change when meaning is unchanged.
- Material meaning changes require a new ID and an explicit relationship.
- Deprecated concepts retain their IDs and are marked explicitly.
- Renames require an explicit compatibility note or alias until all references are migrated.

## Validation boundary

Do not add a schema or database yet. Introduce lightweight checks only after real records reveal repeated broken links, duplicate IDs, or inconsistent fields.
