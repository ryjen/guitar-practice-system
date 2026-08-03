# Technique Catalog

Techniques are the primary unit of progression in the guitar practice system. Songs, gear setups, and backing tracks provide context; they do not own technique mastery.

## Lifecycle

| State | Meaning | Minimum evidence |
|---|---|---|
| `discovered` | The technique is identified but not assessed. | None |
| `baseline-recorded` | A representative first take exists. | One dated recording and observations |
| `developing` | Focused exercises are being used against specific audible defects. | Recent isolated evidence |
| `reliable-isolation` | The technique passes its isolated quality gates consistently. | Three consecutive clean repetitions in at least two sessions |
| `reliable-context` | The technique remains credible in a musical phrase, backing track, or song section. | At least two musical-context recordings |
| `maintained` | The technique has remained reliable across scheduled regression checks. | Two successful checks separated by the defined cadence |

A state is descriptive rather than aspirational. Regress the state when evidence no longer supports it.

## Quality model

Raw tempo is optional. Every technique defines only the dimensions that matter to its musical purpose:

- **Timing** — placement against pulse, subdivision, groove, and transitions
- **Intonation** — pitch-centre accuracy for bends, slide, fretless-like effects, and sustained notes
- **Articulation** — attack, release, muting, separation, and unwanted transients
- **Dynamics** — deliberate control of level, emphasis, and phrase shape
- **Physical tension** — no unnecessary gripping, shoulder tension, or loss of motion economy
- **Repeatability** — quality survives repeated takes rather than appearing once by chance
- **Musical context** — the technique supports a phrase or arrangement rather than only an exercise

A technique may add dimensions such as pedal synchronization, sustain stability, string noise, or harmonic clarity.

## Evidence rules

Evidence records should be lightweight links, not large repository assets by default.

Each record includes:

- date
- context: isolated, backing track, song section, or full take
- tempo or feel when relevant
- recording location or stable identifier
- gear-setup reference when it materially affects the result
- observations grounded in what is audible
- one next target, preferably the largest audible defect

Do not promote a technique based only on a best take. Promotion requires repeatability across sessions.

## Maintenance and regression

Each reliable technique defines:

- a maintenance cadence
- a short representative regression check
- failure conditions
- the state to return to when the check fails

A regression check should usually take under five minutes. Failed checks create a focused practice target; they are not treated as general failure.

## Catalog

| Technique | Branch | Current state | Primary dimensions | Document |
|---|---|---|---|---|
| Slide foundations | Core | `discovered` | intonation, muting, vibrato, tension | [`slide-foundations.md`](slide-foundations.md) |

Planned catalog entries include rhythmic wah, expressive wah, E-Bow activation and layering, hybrid picking, bend intonation, vibrato, and muted rhythm articulation.

## Adding a technique

1. Copy [`../../templates/technique.md`](../../templates/technique.md).
2. Give it a stable lowercase identifier.
3. Define a musical purpose before exercises.
4. Select only relevant quality dimensions.
5. Add at least one isolated and one musical-context use case.
6. Define evidence and maintenance rules before marking it reliable.
