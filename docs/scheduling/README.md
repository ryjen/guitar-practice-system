# Deterministic Scheduling and Progression Contract

## Purpose

The scheduling contract turns explicit, versioned practice state into a reproducible schedule proposal. It does not mutate canonical state, evaluate evidence, or reinterpret progression quality.

The same snapshot, state revision, ruleset version, supplied clock, and timezone must produce the same proposal.

## Current contract

The current normalized exchange contract is **scheduling/v2**:

- [`contracts/scheduling/v2/scheduling.schema.json`](../../contracts/scheduling/v2/scheduling.schema.json)
- [`scripts/scheduling_v2.py`](../../scripts/scheduling_v2.py)
- [`examples/scheduling/v2-example-snapshot.json`](../../examples/scheduling/v2-example-snapshot.json)

The original [`scheduling/v1`](../../contracts/scheduling/v1/scheduling.schema.json) contract remains available as a historical compatibility baseline. V1 used scheduling-specific lifecycle states. V2 supersedes that model by using the same canonical progression states as the deterministic assessment core and representing active scheduling membership separately.

## Normalized v2 records

A v2 snapshot keeps separate facts separate:

| Record | Responsibility |
|---|---|
| `practiceGoal` | Explicit goals, goal priority, and target membership |
| `activeWorkItem` | Which development items are currently active, their local priority, target duration, recovery window, and missed status |
| `maintenanceRule` | Maintenance interval, priority, target duration, and recovery window |
| `dependency` | Explicit prerequisite item and satisfying progression states |
| `progressionProjection` | Approved canonical state plus provenance/history references used by scheduling |
| `scheduleConstraint` | Session duration, active capacity, load spacing, and weekly budgets |
| `schedule-proposal` | Deterministic selected/excluded work and reasons |
| `approved-schedule` | Approval record for a proposal |
| `completion-record` | What scheduled work was actually completed |
| `schedule-event` | Append-only scheduling events |

This separation prevents a mastery/progression state from being confused with the question of whether an item is currently in the active practice set.

## Canonical progression states

Scheduling v2 uses the same progression state vocabulary as assessment:

```text
discovered
  -> developing
  -> reliable-isolation
  -> reliable-context
  -> maintained
```

Lifecycle states:

```text
paused
retired
```

The scheduling tests assert that the scheduling state set exactly matches the assessment evaluator's supported state set.

### Active work is separate

An item may be in `discovered`, `developing`, `reliable-isolation`, or `reliable-context` while either being present or absent from `active_work`.

Only items explicitly present in `active_work` are considered for ordinary development scheduling. `maintained` items are scheduled only through maintenance rules. `paused` and `retired` items are excluded.

Adding or removing active work is an explicit state-management action outside proposal generation.

## Snapshot identity and provenance

A scheduling snapshot is immutable input for one proposal attempt and carries:

- `snapshot_id`
- canonical `state_revision`
- `ruleset_version`
- generated timestamp
- effective local date and IANA timezone
- normalized goals, active work, maintenance rules, dependencies, and progression projections
- explicit scheduling constraints

Each progression projection carries its own `state_revision` and may retain supporting assessment proposal IDs, last meaningful practice/verification dates, weekly repetition count, and plateau-observation references.

Those references provide provenance. They are not converted into hidden scores or new evidence by scheduling.

## Active-work capacity

`active_work` is explicit input. The snapshot fails validation when:

```text
len(active_work) > constraints.max_active_items
```

An active-work record must:

- reference an existing progression item;
- reference an active goal that targets that item;
- refer to a development progression state rather than `maintained`, `paused`, or `retired`.

The scheduler does not implicitly activate another item to fill unused capacity.

## Goals and priority

Active work references an explicit goal. Ordering for ordinary development work is:

1. missed-session tier before ordinary active work;
2. lower numeric goal priority;
3. lower numeric active-work priority;
4. stable item ID tie-break.

There is no opaque aggregate score.

## Maintenance due state

A maintained item is eligible only when it has a maintenance rule.

```text
next_due_date = last_verification_date + interval_days
```

- No prior verification date means the maintenance check is due.
- Before `next_due_date`, it is `not-due`.
- On or after `next_due_date`, it is `due` with explicit `overdue_days`.
- Maintained items without a rule are excluded with `maintenance-rule-missing` rather than guessed.

Due maintenance sorts before development work. More-overdue maintenance sorts first, then explicit maintenance priority, then item ID.

## Dependencies

A dependency record names:

- the scheduled item;
- the prerequisite item;
- the exact progression states that satisfy the dependency.

The scheduler evaluates dependencies from the supplied canonical projection only. A proposal cannot unlock its own prerequisite.

Approved progression changes from assessment become visible only in a later scheduling snapshot/state revision.

## Recovery and self-reported load

Active-work and maintenance records provide explicit minimum recovery windows. The progression projection provides the last-practiced timestamp.

Under `self_reported_load: normal`, the configured recovery window is used directly.

Under `self_reported_load: high`, the v2 reference ruleset:

- doubles the explicit recovery window;
- caps proposed session duration at `high_load_max_minutes`.

This is only a deterministic response to supplied state. It is not a diagnosis or inferred readiness judgment.

## Missed-session recovery

`activeWorkItem.missed: true` puts otherwise eligible work ahead of ordinary active work.

Missed work still obeys:

- prerequisites;
- recovery windows;
- weekly repetition caps;
- session/minute budgets;
- minimum block size.

## Weekly budgets

The schedule constraint carries:

- maximum sessions;
- completed sessions;
- maximum minutes;
- completed minutes;
- maximum repetitions of the same target.

When weekly session or minute capacity is exhausted, the proposal is a `no-op` with explicit conflict reasons.

A target already at its repetition cap is excluded before ranking.

## Proposal ordering

Eligible work is sorted by the explicit tier order:

1. due maintenance;
2. missed active development work;
3. ordinary active development work.

Allocated minutes are bounded by the session and weekly budgets. Partial allocations are marked with `partial-time-allocation`.

Selected records identify whether the work is `development` or `maintenance`.

## Proposal identity and approval

A proposal contains:

- deterministic `proposal_id`;
- snapshot/state/ruleset identity;
- effective date and expiry date;
- selected work with reason codes;
- excluded work with reason codes;
- conflicts;
- `requires_approval: true`.

Proposal generation is read-only.

Before applying a proposal, `check-approval` compares it to current scheduling state. A proposal becomes stale when any of these change:

- snapshot identity;
- state revision;
- ruleset version;
- effective date.

A `no-op` proposal cannot be approved as practice work.

## Completion and events

The exchange contract includes implementation-neutral records for:

- approved schedule identity;
- actual completion time and completed item IDs;
- proposal creation/approval/rejection;
- session completion/missed events;
- active-work additions/removals.

Completion records describe what happened. They do not assert assessment outcomes or directly change progression state.

## Assessment boundary

Assessment owns deterministic evidence-gate evaluation and progression transition proposals.

Scheduling consumes only approved progression projections and their provenance references. It does not:

- evaluate quality gates;
- reinterpret observations;
- promote or regress progression state;
- assign causes to plateau observations.

## Time and replay

- Domain behavior uses supplied `generated_at`, never ambient current time.
- `effective_date` must match `generated_at` in the declared IANA timezone.
- Replay uses the same snapshot, ruleset version, and clock.
- Proposal expiry is the effective local date in v2.
- Canonical state changes require a new state revision before another proposal is approved.

## Example

```bash
python scripts/scheduling_v2.py propose \
  examples/scheduling/v2-example-snapshot.json \
  > /tmp/schedule-v2.json

python scripts/scheduling_v2.py check-approval \
  /tmp/schedule-v2.json \
  examples/scheduling/v2-example-snapshot.json
```

The example schedules due E-Bow maintenance before active slide development without changing either item's canonical progression state.

## Fixtures and tests

[`examples/scheduling/v2-fixtures.json`](../../examples/scheduling/v2-fixtures.json) covers:

- normal progression;
- maintenance due state;
- blocked prerequisites;
- dependency unlocking after an approved progression change;
- missed-session recovery;
- pause and resume;
- weekly budget exhaustion.

The v2 tests additionally cover:

- exact state-vocabulary alignment with assessment;
- explicit active-work/progression separation;
- invalid active membership;
- active-goal requirements;
- active-capacity validation;
- high-load recovery/session caps;
- repetition caps;
- deterministic replay;
- stale proposal rejection;
- timezone validation.
