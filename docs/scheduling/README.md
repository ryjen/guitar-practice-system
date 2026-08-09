# Deterministic Scheduling and Progression Contract

## Purpose

The scheduling contract turns an explicit, versioned practice-state snapshot into a reproducible schedule proposal. It does not mutate canonical state and it does not reinterpret evidence.

The same snapshot, state revision, ruleset version, clock value, and timezone must produce the same proposal.

## Contract

The v1 exchange schema is:

- [`contracts/scheduling/v1/scheduling.schema.json`](../../contracts/scheduling/v1/scheduling.schema.json)

It defines five record families:

1. `schedule-snapshot`
2. `schedule-proposal`
3. `schedule-approval`
4. `completion-record`
5. `schedule-event`

The reference implementation is [`scripts/scheduling.py`](../../scripts/scheduling.py).

## Snapshot semantics

A scheduling snapshot is immutable input for one proposal attempt. It carries:

- `snapshot_id`
- canonical `state_revision`
- `ruleset_version`
- generated timestamp
- effective local date and IANA timezone
- session duration and minimum block duration
- active-work capacity
- explicit self-reported load state
- weekly session/minute/repetition budgets
- current work items and prerequisite relationships

A work item records only supplied scheduling facts:

- lifecycle state
- explicit priority
- target minutes
- prerequisite state requirements
- maintenance interval and last verification date
- last-practiced timestamp and minimum recovery window
- current weekly repetition count
- explicit missed-session flag

## Lifecycle states

- `candidate` — may be proposed only when active-work capacity is available
- `active` — ordinary development work
- `verified` — no routine development work unless maintenance becomes due
- `maintenance` — maintenance work; scheduled when due
- `paused` — retained in state but excluded from scheduling
- `retired` — retained for history but excluded from scheduling

Changing lifecycle state is a separate approved state mutation. Proposal generation never activates, pauses, resumes, verifies, or retires an item.

## Deterministic ordering

Eligible work is sorted by this explicit tier order:

1. due maintenance
2. explicitly missed work
3. active work
4. candidate work

Within due maintenance, more-overdue work sorts first, then explicit priority, then item ID.

Within all other tiers, lower numeric priority sorts first, then item ID.

There is no hidden score.

## Maintenance due state

When a maintenance interval is present:

```text
next_due_date = last_verified_date + maintenance_interval_days
```

- If no prior verification date exists, maintenance is due.
- If the effective date is before `next_due_date`, maintenance is not due.
- On or after `next_due_date`, maintenance is due and `overdue_days` is explicit.
- An item already in `maintenance` without an interval is treated as explicitly due.

## Prerequisites

Each prerequisite names another work item plus the exact states that satisfy the relationship.

An item is excluded with `prerequisite-blocked` when any prerequisite is not currently in one of its declared satisfying states.

Dependencies are evaluated from the supplied snapshot only. A schedule proposal cannot unlock its own prerequisites.

## Active-work capacity

The snapshot must not contain more `active` items than `max_active_items`.

Candidate proposals use only the remaining capacity:

```text
candidate_slots = max_active_items - active_item_count
```

Selecting a candidate in a proposal consumes a proposal-local slot, but does not change canonical lifecycle state.

## Recovery and load

Each work item may specify `min_recovery_hours` and `last_practiced_at`.

Under normal load, the configured recovery window is used directly. Under explicit `self_reported_load: high`, the reference ruleset doubles the recovery window and caps the proposed session duration at `high_load_max_minutes`.

This is a scheduling constraint, not a diagnosis or inferred readiness judgment.

## Missed-session recovery

`missed: true` places otherwise eligible work ahead of ordinary active priority. All other constraints still apply:

- prerequisites
- recovery
- repetition caps
- weekly budget
- active capacity

Missed work does not bypass safety or capacity rules.

## Weekly budgets

The v1 snapshot carries:

- maximum sessions
- completed sessions
- maximum minutes
- completed minutes
- maximum repetitions of the same target

When the session or minute budget is exhausted, the proposal is `no-op` with an explicit conflict reason.

A target at its weekly repetition cap is excluded before ranking.

## Proposal semantics

A proposal contains:

- stable deterministic `proposal_id`
- input snapshot/state/ruleset identity
- effective date and expiry date
- selected work with allocated minutes and reason codes
- excluded work with reason codes
- conflicts
- `requires_approval: true`

Proposal IDs are hashes of canonical proposal inputs and results. Generating a proposal twice from the same snapshot produces the same record.

A proposal with no selected work has `status: no-op`.

## Approval and stale-state checks

Approval is a separate command boundary.

Before approval, compare the proposal with current canonical scheduling state. The reference `check-approval` operation rejects a proposal when any of these change:

- snapshot identity
- state revision
- ruleset version
- effective date

A no-op proposal cannot be approved as practice work.

Example:

```bash
python scripts/scheduling.py propose examples/scheduling/example-snapshot.json > /tmp/proposal.json
python scripts/scheduling.py check-approval /tmp/proposal.json examples/scheduling/example-snapshot.json
```

## Completion and events

The exchange schema includes implementation-neutral records for:

- approved proposal identity
- actual completion time and completed item IDs
- session completion or missed-session events
- pause/resume events

Completion records describe what happened; they do not directly assert assessment outcomes or progression transitions.

## Assessment boundary

Scheduling consumes approved progression/evidence state. It does not evaluate quality gates, reinterpret recordings, or decide promotion/regression from evidence.

Assessment owns those decisions and supplies approved state back into later scheduling snapshots.

## Time and replay

- Domain behavior uses the supplied `generated_at` value rather than ambient current time.
- `effective_date` must match `generated_at` in the declared IANA timezone.
- Replay uses the same snapshot, ruleset version, and supplied clock.
- Proposal expiry is the effective local date in v1.

## Fixtures

[`examples/scheduling/fixtures.json`](../../examples/scheduling/fixtures.json) covers:

- normal active work
- maintenance due state
- blocked prerequisites
- dependency unlocking
- missed-session recovery
- pause and resume
- weekly budget exhaustion

The tests also cover stale proposals, recovery windows, load caps, repetition caps, active capacity, and timezone validation.
