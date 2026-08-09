# Deterministic Assessment Core

## Purpose

Assessment converts explicit practice evidence into auditable gate outcomes and a proposed progression transition. It does not interpret recordings, infer hidden causes, or mutate canonical state.

The core contract is:

```text
explicit evidence + immutable gate version + current state
    -> per-gate outcomes
    -> transition proposal
    -> explicit approval elsewhere
```

## Evidence layers

Keep these concepts separate:

1. **Evidence reference** — a stable record of a practice attempt or observation source.
2. **Explicit observation** — a supplied fact such as `timing_gate: pass` or `physical_stop: false`.
3. **Interpretation** — explanatory metadata that is never authoritative for gates.
4. **Recommendation** — advisory next action that is never authoritative for gates.
5. **Gate result** — deterministic evaluation of fields explicitly named by a gate.
6. **Approved canonical finding** — state accepted by an explicit state-application workflow.

Confidence, interpretation, recommendation, prose notes, and unspecified fields never become evidence merely because they are present.

## Gate outcomes

Each gate resolves to exactly one outcome:

- `pass` — supplied inputs satisfy the gate.
- `fail` — supplied inputs explicitly contradict the gate.
- `unknown` — required evidence is missing, stale, insufficient, or conflicting.
- `not-applicable` — the gate does not apply to the requested transition.
- `blocked` — an explicit blocking observation is present.

`unknown` is intentionally distinct from `fail`.

## Versioning

Gate sets are immutable once used. A gate set has:

- stable `id`
- integer `revision`
- ordered gate definitions

Changing a rule requires a new revision. Replaying the same assessment request with the same gate set produces the same proposal identifier, ruleset fingerprint, and gate results. Re-evaluating under another revision creates a distinct proposal and preserves the earlier result.

## Supported deterministic rules

The initial reference evaluator deliberately supports only two transparent rule types:

### `observation-equals`

Evaluates one explicit observation field against an expected value.

If no qualifying observation exists, the outcome is `unknown`. If qualifying observations conflict, the outcome is also `unknown`.

### `evidence-count`

Requires a minimum number of qualifying evidence records and, independently, a minimum number of distinct sessions. This prevents several attempts in one session from masquerading as repeatability across sessions.

Both rules may use `max_age_days` to enforce recency.

## Transition model

The reference lifecycle is:

```text
discovered
  -> developing
  -> reliable-isolation
  -> reliable-context
  -> maintained
```

`paused` and `retired` are explicit lifecycle states. Regression proposals may move only to a valid earlier state; they do not erase unrelated dimension history.

Assessment validates whether a requested transition is supported. It never applies it.

## Stale state and idempotency

Every request supplies `state_revision`. Every proposal returns:

- the same `state_revision`
- deterministic `proposal_id`
- deterministic `application_key`
- `stale_when_state_revision_changes: true`

A state-application layer must reject the proposal if canonical state has changed since assessment. Reusing the same application key against the same state revision must be idempotent.

## Example

```bash
python scripts/assessment_core.py \
  examples/assessment/slide-reliable-context.json \
  templates/assessment-gate-set.json
```

The fixture requires:

- two isolated checks from two different sessions
- one musical-context take
- explicit passing timing observations
- no explicit physical stop condition

All are supplied directly; the evaluator does not derive them from audio or prose.

## Integration boundary

Assessment owns evidence-gate evaluation and transition proposals. Scheduling consumes approved state and does not reinterpret evidence.

The assessment core intentionally does not own:

- schedule generation or maintenance due dates
- recording/audio/video interpretation
- natural-language diagnosis
- opaque scores
- inferred causes or readiness
- autonomous canonical state mutation
- medical conclusions
