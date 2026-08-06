# Adaptive Practice Sessions

Adaptive session discovery converts explicit current context into an advisory practice plan. It does not diagnose unrecorded weaknesses, schedule work, or update progress.

## Request

Required:

- `duration_minutes`: `15`, `30`, `45`, or `60`
- at least one of `priorities`, `maintenance_due`, or `active_techniques`

Optional:

- `environment`: `normal`, `quiet`, `headphones`, `acoustic-only`, or `no-computer`
- `available_gear`
- `available_backing_tracks`
- `desired_genres`
- `theory_focus`
- `max_active_techniques`
- `evidence`, keyed by technique ID

Evidence may include `largest_audible_defect`. The planner treats that as an explicit observation, not an independently verified diagnosis.

## Selection order

1. A maintenance-due, priority, or active technique with explicit defect evidence.
2. The first maintenance-due technique.
3. The first stated priority.
4. The first active technique.

The request is rejected when the active technique count exceeds `max_active_techniques`.

## Recommendation

Every recommendation contains:

- one focus technique
- warmup
- primary technique work
- optional theory support for sessions of 30 minutes or longer
- musical application
- a short evidence task
- a shorter fallback duration
- rationale for each block
- warnings where context is incomplete or incompatible

Block durations sum exactly to the requested duration. The evidence block is never silently removed to fit time.

## Environment behavior

- `quiet`: prefer unplugged, very low-volume, or muted-string work; avoid feedback-dependent tasks.
- `headphones`: use direct monitoring and conservative listening level.
- `acoustic-only`: replace pedal-dependent application with mechanics, articulation, or phrasing preparation and warn when the selected focus requires electric capability.
- `no-computer`: avoid DAW requirements; use amp, looper, metronome, or offline material.

## Approval and state

Recommendations are drafts. They require approval before use and may not mutate:

- schedules
- progress or mastery
- maintenance state
- active-work state
- evidence records

Completion and evidence review remain separate actions.

## Usage

```bash
python scripts/adaptive_session.py examples/discovery/adaptive-session-request.json
```

## Dependency on the feedback loop

Issue #12 will add richer evidence capture and maintenance rules. Until then, the planner accepts only explicitly supplied evidence and maintenance state. Missing evidence produces a warning and never becomes an inferred weakness.
