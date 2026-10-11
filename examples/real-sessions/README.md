# M3 Real-Session Run Sheets

Status: pre-session plans only. These files intentionally contain no claimed observations, takes, gate outcomes, or progression decisions.

These sheets make issue #87 executable without creating a new practice model. They specialize the canonical practice-session workflow and template for the three required M3 techniques:

- slide — slide-m3-session.md
- wah — wah-m3-session.md
- E-Bow — ebow-m3-session.md

Use them in that order unless the deterministic schedule gives a concrete reason to change it.

## Before playing

1. Regenerate or verify the canonical backing MIDI:

    guitarctl backing generate

2. Use one stable guitar/effect setup for the complete baseline-to-verification comparison.
3. Choose a local recording reference before starting. The recording itself does not belong in the public repository.
4. Stop or simplify if pain, unusual fatigue, or loss of physical control appears.
5. Do not fill an observation field before hearing it in the session.

## Evidence boundary

After playing, capture only observed facts. The blank evidence fields in each run sheet map to templates/practice-session.md and templates/evidence.json.

For the one #87 session chosen for the complete deterministic lifecycle:

    session observation
      -> evidence record
      -> guitarctl evidence feedback
      -> guitarctl assess evaluate
      -> explicit human approval or rejection
      -> guitarctl schedule propose

The commands do not decide whether a take was good. Missing facts remain unknown, and an assessment proposal does not become canonical progression state without an explicit human decision.

## Completion boundary

These run sheets remove preparation friction only. They do not satisfy any #87 checkbox until the corresponding guitar session has actually been played and the observations have been recorded.
