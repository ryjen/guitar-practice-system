# Practice Session Workflow

## Purpose

Define the canonical end-to-end process for conducting a guitar practice session with this system.

The session is a closed feedback loop:

```text
select target
  -> realize today's constraints
  -> prepare
  -> capture baseline
  -> isolate the largest defect
  -> reintegrate in musical context
  -> add one controlled challenge
  -> capture verification take
  -> record evidence
  -> assess
  -> schedule the next action
```

The workflow is deliberately deterministic and observation-driven. Missing information remains unknown. A good take does not automatically imply mastery, and a scheduler does not reinterpret evidence.

Use [`../templates/practice-session.md`](../templates/practice-session.md) to capture the concrete session realization.

## 1. Select one primary target

Choose one primary objective and, when useful, one secondary constraint.

Examples:

- slide intonation, with intentional space as the secondary constraint
- wah timing, with sixteenth-note subdivision control
- E-Bow string changes, with dynamic swells
- hybrid picking, with clean string separation

Prefer one strong target over several weak targets. Optional musical dimensions are constraints, not a checklist that must all be active.

Record:

- primary musical goal
- largest known audible problem
- target duration
- stop condition

## 2. Resolve today's realization

Turn reusable technique, rhythm, harmony, gear, and backing-track references into concrete settings for this session.

At minimum, specify the settings that matter to the target:

- technique or exercise ID
- instrument and relevant gear setup
- tuning when relevant
- tempo and beat unit
- subdivision and click behavior
- meter/grouping when relevant
- harmonic/progression context
- backing track or musical-context reference
- expression/space constraint when relevant
- duration or repetition bound
- evidence goal

Do not silently infer omitted settings. Omitted dimensions remain unconstrained.

### Timing realization

A tempo value alone is incomplete. When timing matters, resolve:

- BPM
- beat unit
- subdivision
- click mode
- meter/grouping
- progression strategy, when applicable

Use the repository timing/metronome guidance for slow-to-working-to-target progression.

## 3. Prepare with a task-specific warmup

Warm up for the actual task rather than performing an unrelated generic routine.

Preparation may include:

- low-intensity mechanical activation
- rhythmic orientation
- reference-pitch or interval listening
- fretboard location checks
- articulation preparation
- a short version of the target movement

Keep preparation bounded. If the warmup exposes pain, unusual fatigue, or loss of control, reduce the session load or stop according to the session's explicit stop condition.

## 4. Capture a pre-drill baseline

Before substantial correction work, record one short uninterrupted baseline that represents the current state of the target.

A baseline should be:

- short and bounded
- representative of the target
- captured with enough context to reproduce
- performed without repeated restart attempts

Record the realization used, especially tempo, gear/setup, backing track or reference, and variant.

The baseline exists to answer:

> What is the largest audible defect right now?

Do not turn the baseline into a score.

## 5. Isolate the largest defect

Reduce the task until the primary defect can be practised without unrelated complexity.

Examples:

- intonation problem -> one string, two positions, drone/reference pitch, no vibrato
- muting problem -> adjacent-string transitions at low speed
- wah timing problem -> one chord, one subdivision, fixed movement range
- E-Bow transition problem -> two strings, dry signal, controlled activation/release

Change as few variables as possible.

### Metronome progression

When timing or mechanical speed is relevant, use a bounded progression rather than increasing BPM automatically.

Typical rule:

```text
clean x3       -> increase 3-5 BPM
minor defect   -> repeat
repeated error -> reduce about 5 BPM
mechanics fail -> simplify the task
```

Tempo progression may also use:

- subdivision changes
- tempo pyramids
- bounded speed bursts
- loop expansion
- sparse/backbeat/off-beat click validation

Extremely slow playing is preparation, not proof that fast mechanics will transfer unchanged.

## 6. Reintegrate the technique into musical context

After isolated improvement, restore enough musical context to test whether the improvement survives real playing demands.

Possible context includes:

- chord progression
- backing track
- song section
- rhythmic groove
- phrase/space constraint
- role within an arrangement

This distinguishes two different claims:

- **isolated competence** — the movement works under reduced conditions
- **musical-context competence** — the movement remains credible while harmony, groove, phrasing, transitions, and attention compete for resources

Do not treat isolated success as musical-context verification.

## 7. Add one controlled challenge

Only after the primary objective is reasonably stable, change one deliberate variable.

Examples:

- 60 BPM -> 65 BPM
- normal click -> backbeat click
- one neck position -> adjacent-position movement
- straight eighths -> triplets
- glass slide -> brass slide
- dry signal -> intended musical effect chain

Avoid changing instrument, tempo, gain, tuning, articulation, and musical context simultaneously. If several variables change, the resulting evidence cannot identify what caused improvement or regression.

## 8. Capture a comparable verification take

Finish with another bounded uninterrupted take that is meaningfully comparable with the baseline.

Keep the important comparison variables stable unless the session explicitly tested one of them.

Good comparison:

```text
baseline:     same guitar / same slide / 60 BPM / 12-bar blues
verification: same guitar / same slide / 60 BPM / 12-bar blues
```

Poor comparison:

```text
baseline:     clean Strat / 50 BPM
verification: driven PRS / 90 BPM / different slide / different backing track
```

A verification take answers whether the session change survived an end-to-end performance, not whether the player produced a single best moment.

## 9. Record lightweight evidence

Record only information that can support later assessment or the next practice decision.

Useful evidence includes:

- recording reference
- attempted realization
- highest clean realization when relevant
- what remained credible
- largest audible defect
- timing observations
- pitch/intonation observations
- articulation/noise observations
- dynamics/phrase/space observations
- physical tension or fatigue
- next explicit action

Separate observation from interpretation. Prefer statements such as `low-position arrivals were consistently sharp` over vague labels such as `bad slide technique`.

## 10. Run deterministic assessment

Assessment evaluates the evidence against explicit versioned gates. It does not infer missing facts.

Possible gate outcomes include:

- `pass`
- `fail`
- `unknown`
- `blocked`
- `not-applicable`

Assessment may propose a progression transition, but canonical progression changes remain explicit and approval-gated.

A single successful take should not silently become mastery. Repetition, recency, cross-session evidence, or musical-context verification may be required by the relevant gate definition.

## 11. Hand approved state to scheduling

Scheduling consumes approved progression state. It does not decide whether the evidence was correct.

The scheduler may determine:

- whether the target remains active
- when maintenance is due
- when verification should recur
- whether a missed session creates catch-up work
- whether active-work capacity is already full
- which bounded practice item is due next

This preserves the ownership boundary:

```text
session evidence
  -> deterministic assessment
  -> approved progression state
  -> deterministic scheduling
```

## Recommended session shape

A practical 40-minute example:

| Phase | Approximate time |
| --- | ---: |
| Resolve target/setup | 2 min |
| Task-specific preparation | 5 min |
| Baseline | 3 min |
| Isolated work | 12 min |
| Musical-context work | 10 min |
| Controlled challenge | 4 min |
| Verification take | 2 min |
| Evidence/review | 2 min |

These are guidelines, not required durations. Delete phases that do not serve the target.

## Minimal session rule

When time is short, preserve the feedback loop rather than merely shortening the exercise list:

```text
target -> brief baseline -> isolate -> musical check -> evidence -> next action
```

A ten-minute session that produces a credible observation and next action is more useful to the system than forty minutes of unrecorded repetition.

## Worked example: slide intonation

**Target:** slide intonation and muting in standard tuning  
**Context:** 12-bar blues in A  
**Secondary constraint:** two-bar phrase followed by two-bar response space

1. Prepare with sustained reference pitches, fret-to-fret movement, and light muting checks.
2. Record a 30-second baseline at 60 BPM.
3. Identify the largest defect; assume low-position arrival pitch is sharp.
4. Isolate one string and two positions against a drone at 50-60 BPM without vibrato.
5. Progress only after clean repeated arrivals.
6. Return to the 12-bar blues at the original 60 BPM.
7. Add one challenge, such as adjacent-string movement.
8. Record a comparable verification take.
9. Capture the observed change, remaining defect, fatigue, and next action.
10. Let the assessment gate determine whether the evidence is sufficient for a progression proposal; let scheduling determine when the target should return.

## Principle

The canonical session loop is:

> **Plan -> observe -> isolate -> reintegrate -> verify -> record -> assess -> schedule.**

The purpose is not to maximize exercise volume. It is to produce reliable musical improvement and enough explicit evidence to decide what should happen next.
