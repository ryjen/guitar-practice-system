# Deterministic Scheduling Core

## Purpose

Scheduling consumes **approved progression state** plus explicit constraints and produces an auditable schedule proposal. It does not evaluate evidence or decide whether a technique should be promoted or regressed.

```text
approved state snapshot + explicit constraints + injected clock
    -> due/block/recovery projection
    -> deterministic ranking
    -> bounded schedule proposal
    -> explicit approval elsewhere
```

## State snapshot

`templates/scheduling-state.json` is the implementation-neutral exchange contract. It carries:

- `snapshot_version` and `ruleset_version`
- injected `generated_at`, `effective_date`, and timezone
- active-work and weekly budget constraints
- practice goals
- progression items with approved state revisions
- maintenance intervals and dates
- explicit self-reported load
- dependency requirements
- append-only schedule history

The scheduler never reads ambient time in domain logic.

## Deterministic ordering

Eligible targets are ordered by:

1. maintenance due before not due;
2. explicit missed-session catch-up before ordinary work;
3. explicit numeric priority;
4. greater overdue age;
5. older last-practice date;
6. stable target ID.

This is intentionally transparent. There is no hidden score or inferred weakness.

## Eligibility

A target may be excluded because it is:

- paused or retired;
- blocked by an explicit dependency;
- inside a recovery window;
- at its per-target weekly repetition limit;
- a new inactive item while active-work capacity is full;
- unable to fit in the remaining weekly session/minute budget.

Maintenance work may remain eligible even when active-work capacity is full because it is preserving already-approved state rather than starting new active work.

## Maintenance and long-term state

Maintenance is due only when both an explicit interval and a last verified date exist. Missing history stays unknown; it is not treated as overdue.

The projection exposes:

- maintenance due date
- overdue days
- catch-up status
- dependency blockers
- eligibility and deterministic exclusion reasons

`plateau_observed` may be carried as explicit state but is never assigned a cause by the scheduler.

## Recovery and load

Normal and high-load recovery spacing are configured separately. High load is used only when explicitly supplied by the player; the scheduler does not infer fatigue, pain, or readiness.

## Missed sessions

A `missed` history event marks the target for catch-up ordering during the current week. Catch-up does not override hard constraints such as recovery, dependencies, repetition caps, or total budget.

## Pause/resume and dependencies

Paused and retired items are excluded without losing history. Resume is represented by a later state snapshot where approved state and `active` status have changed explicitly.

Dependencies specify target IDs and acceptable approved states. When a prerequisite reaches an acceptable state in a later snapshot, the dependent item becomes eligible without any evidence reinterpretation by scheduling.

## Replay, timezone, and DST

The state snapshot records an offset-aware `generated_at`, local `effective_date`, timezone identifier, and week-start convention. Domain calculations use the supplied local date. The same snapshot and ruleset produce the same proposal regardless of the machine running the evaluator.

DST conversion from an instant into the supplied local date belongs to the caller that constructs the snapshot; the scheduler does not consult the host timezone database during proposal generation.

## Approval, staleness, and idempotency

A proposal returns:

- deterministic `proposal_id`
- source `snapshot_version`
- deterministic `application_key`
- `stale_when_snapshot_version_changes: true`

`application_status()` reports:

- `applicable`
- `stale`
- `already-applied`

Actual state mutation remains outside the scheduler. An approval layer must reject stale proposals and treat an already-used application key idempotently.

## Relationship to assessment

Assessment owns evidence interpretation rules and progression-transition proposals. Scheduling consumes the resulting **approved state** and optional proposal reference only. It must not inspect assessment gate results to create its own promotion or regression decision.

## Example

```bash
python scripts/scheduling_core.py examples/scheduling/weekly-progression.json
```

The example demonstrates maintenance priority, missed-session catch-up, active capacity, a dependency that has become unlocked, and a paused technique.
