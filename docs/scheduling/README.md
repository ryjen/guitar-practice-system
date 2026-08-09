# Deterministic Scheduling and Progression Contract

## Purpose

The scheduling contract turns an explicit, versioned practice-state snapshot into reproducible schedule and long-term progression projections. It does not mutate canonical state and it does not reinterpret evidence.

The same snapshot, state revision, ruleset version, clock value, and timezone must produce the same outputs.

## Contract

The v1 exchange schema is:

- [`contracts/scheduling/v1/scheduling.schema.json`](../../contracts/scheduling/v1/scheduling.schema.json)

It defines six record families:

1. `schedule-snapshot`
2. `schedule-proposal`
3. `progression-projection`
4. `schedule-approval`
5. `completion-record`
6. `schedule-event`

Reference implementations:

- [`scripts/scheduling.py`](../../scripts/scheduling.py) — schedule selection and stale-approval checks
- [`scripts/scheduling_projection.py`](../../scripts/scheduling_projection.py) — approved long-term state and goal projection

## Snapshot semantics

A scheduling snapshot is immutable input. It carries snapshot/state/ruleset identity, generated timestamp, effective local date and IANA timezone, session limits, active-work capacity, explicit self-reported load, weekly budgets, current work items, prerequisites, and optional practice goals.

A work item records only supplied facts. The v1 contract supports:

- lifecycle state and explicit priority
- optional musical dimension
- optional approved assessment-transition proposal reference
- target and maintenance realizations, including timing/metronome references
- maintenance interval and last verification date
- last-practiced timestamp and minimum recovery window
- weekly repetition count and explicit missed-session flag
- explicit plateau observation without assigning a cause

These additional fields are projection metadata only; they do not alter the deterministic schedule ranking rules.

## Lifecycle states

- `candidate` — may be proposed only when active-work capacity is available
- `active` — ordinary development work
- `verified` — no routine development work unless maintenance becomes due
- `maintenance` — maintenance work; scheduled when due
- `paused` — retained in state but excluded from scheduling
- `retired` — retained for history but excluded from scheduling

Changing lifecycle state is a separate approved state mutation. Proposal generation never activates, pauses, resumes, verifies, or retires an item.

## Deterministic ordering

Eligible work is sorted by:

1. due maintenance
2. explicitly missed work
3. active work
4. candidate work

Within due maintenance, more-overdue work sorts first, then explicit priority, then item ID. Within all other tiers, lower numeric priority sorts first, then item ID. There is no hidden score.

## Maintenance due state

When a maintenance interval is present:

```text
next_due_date = last_verified_date + maintenance_interval_days
```

If no prior verification date exists, maintenance is due. Before the due date it is not due; on or after the date it is due with explicit `overdue_days`. An item already in `maintenance` without an interval is explicitly due.

## Prerequisites and active capacity

Each prerequisite names another work item plus exact states satisfying the relationship. An item is blocked when any prerequisite is unsatisfied. Dependencies are evaluated from the supplied snapshot only; a proposal cannot unlock its own prerequisites.

The snapshot cannot contain more active items than `max_active_items`. Candidate selection consumes only proposal-local remaining capacity and does not mutate canonical lifecycle state.

## Recovery, load, missed work, and weekly budgets

Each work item may specify `min_recovery_hours` and `last_practiced_at`. Under explicit high load, v1 doubles the supplied recovery window and caps proposal duration at `high_load_max_minutes`. This is a constraint, not an inferred readiness judgment.

`missed: true` moves otherwise eligible work ahead of ordinary active priority without bypassing prerequisites, recovery, repetition caps, weekly budget, or capacity.

Weekly budget fields cover maximum/completed sessions, maximum/completed minutes, and per-target repetition caps. Exhausted budgets produce a deterministic no-op or exclusion reason.

## Schedule proposal semantics

A proposal contains stable input identity, expiry, selected and excluded work with reason codes, conflicts, and `requires_approval: true`. Proposal IDs are hashes of canonical inputs and results. Replaying the same snapshot produces the same record.

Approval is separate. `check-approval` rejects changed snapshot identity, state revision, ruleset version, effective date, or a no-op proposal.

```bash
python scripts/scheduling.py propose examples/scheduling/example-snapshot.json > /tmp/proposal.json
python scripts/scheduling.py check-approval /tmp/proposal.json examples/scheduling/example-snapshot.json
```

## Long-term progression projection

`progression-projection` is deliberately separate from schedule selection. It exposes the current approved scheduling view without changing ranking behavior.

Each item projection includes:

- lifecycle state and optional dimension
- optional approved assessment-transition proposal reference
- due state and overdue days
- blocked, paused, retired, and missed status
- explicit plateau observation
- target and maintenance realizations

This allows a regression or plateau in one dimension to be represented without erasing unrelated state elsewhere in the system.

Generate it with:

```bash
python scripts/scheduling_projection.py examples/scheduling/projection-snapshot.json
```

## Weekly and monthly goals

Optional goals belong to the snapshot and are explicit counters, not inferred behavior. A goal includes target item, `weekly` or `monthly` period, target sessions, and completed sessions for the caller-defined current period.

The projection reports remaining sessions and completion state. Goals are reporting/progression metadata in v1 and do **not** introduce hidden ranking weight into schedule selection.

## Completion and events

The exchange schema includes implementation-neutral records for approvals, actual completion, session completion/missed events, and pause/resume events. Completion records describe what happened; they do not assert assessment outcomes.

## Assessment boundary

Scheduling consumes approved progression/evidence state. It does not evaluate quality gates, reinterpret recordings, diagnose causes, or decide promotion/regression. Assessment owns those decisions and supplies approved state into later scheduling snapshots.

## Time and replay

- Domain behavior uses supplied `generated_at`, not ambient current time.
- `effective_date` must match `generated_at` in the declared IANA timezone.
- Replay uses the same snapshot, ruleset version, and supplied clock.
- Proposal expiry is the effective local date in v1.

## Fixtures

[`examples/scheduling/fixtures.json`](../../examples/scheduling/fixtures.json) covers normal work, maintenance, blocked/unlocked dependencies, missed sessions, pause/resume, and exhausted budgets.

[`examples/scheduling/projection-snapshot.json`](../../examples/scheduling/projection-snapshot.json) covers dimension/provenance metadata, realizations, plateau state, blocked work, and weekly/monthly goals.
