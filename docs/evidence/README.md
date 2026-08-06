# Practice Evidence and Feedback Loop

## Purpose

Practice evidence is the system's lightweight feedback loop. It records enough context to decide what to practise next without turning music into a metrics dashboard.

Evidence supports decisions; it does not automatically change technique or song state.

## Evidence types

- `baseline` — first representative recording or observation
- `isolated-check` — short focused technique test
- `musical-context` — performance over a backing track, groove, or arrangement
- `full-take` — uninterrupted section or complete performance
- `maintenance` — periodic regression check

## Record contract

Each record contains:

- stable evidence ID
- date
- target type and target ID
- evidence type
- context: tempo, tuning, meter, gear setup, backing track, environment
- relevant quality observations
- largest audible defect
- next practice action
- media reference or an explicit `none`
- privacy classification

Quality dimensions are optional and qualitative:

- timing
- intonation
- articulation and muting
- dynamics
- phrasing and space
- physical tension
- consistency
- recovery after mistakes

Use only dimensions that matter to the current target. Do not invent numeric scores merely to fill fields.

## Reliability gate

A technique may be considered `reliable` only when:

1. its own technique document's quality gates are satisfied;
2. at least one recent `isolated-check` exists;
3. at least one recent `musical-context` or `full-take` exists;
4. no unresolved safety or physical-tension concern is recorded;
5. the state change is explicitly approved.

The validator reports eligibility only. It never writes `reliable`, `mastered`, maintenance dates, or progress state.

## Maintenance intervals

Use maintenance intervals as defaults, not hard truths:

- developing technique: 7–14 days
- reliable technique: 21–45 days
- maintained song or full arrangement: 30–60 days
- physically demanding or fragile work: shorter interval when evidence justifies it

A maintenance check becomes due from an explicit `maintenance_interval_days` and the latest qualifying evidence date. Missing history means `unknown`, not overdue.

## Weekly workflow

1. Record one short baseline or maintenance take for the highest-priority target.
2. Capture one isolated check and one musical-context check when practical.
3. Note only the relevant quality dimensions.
4. Select one largest audible defect.
5. Write one next action small enough for the next session.
6. Review maintenance due dates.
7. Approve any progress-state change separately.

A week with only one useful recording is still valid. Consistency of use matters more than record volume.

## Regression handling

A regression is explicit, not inferred from a missing recording. Mark `regression_observed: true` only when a current take is materially worse than a comparable prior take and state the comparison basis.

Regression should:

- create a maintenance recommendation;
- preserve the prior evidence history;
- not demote state automatically;
- identify the largest audible defect and next action.

## Media and privacy

Large audio and video files stay outside Git by default. Store only a reference and minimal metadata.

Allowed media references include:

- relative paths outside tracked media directories
- private cloud or local-library identifiers
- deliberately public URLs
- `none` when no recording was retained

Do not commit credentials, signed URLs, private sharing tokens, home filesystem paths containing personal names, or embedded media. External providers receive no recording or private note without explicit approval.

## Review principle

The record should answer:

> What changed, what is the largest audible defect, and what is the smallest useful next action?
