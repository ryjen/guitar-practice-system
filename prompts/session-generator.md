# Session Generator Prompt

Use this prompt to generate a focused guitar practice session from reusable source records.

```text
You are helping generate concrete guitar practice material.

Frame the output as playable material, not generic advice. Preserve the technique-first model. Select only the musical dimensions that materially support the stated goal; omitted dimensions are unconstrained, not missing.

Input:
- Primary goal or largest audible problem: {{goal}}
- Technique IDs and current state: {{techniques}}
- Time available: {{duration}}
- Available gear / environment: {{gear_environment}}
- Relevant reusable records: {{warmups_progressions_rhythms}}
- Optional tonal, fretboard, ear, genre, and expression context: {{dimensions}}
- Song, passage, or backing-track context: {{musical_context}}
- Output target: {{output_target}}
- Constraints and explicit unknowns: {{constraints}}

Generate:
1. A short session title and one-sentence intent
2. A goal-directed warmup that prepares the main task, including duration, readiness cue, fatigue risk, and stop condition
3. The smallest useful set of selected dimensions and why each was chosen
4. A main playable fragment, exercise, or song-section task
5. Harmony and rhythm references, with session-specific key, tempo, voicing, grouping, or feel overrides clearly separated from reusable identity
6. Fretboard or ear targets only when they support the main goal
7. An expression plan covering only relevant phrasing, dynamics, articulation, sustain, and space
8. Explicit space constraints when phrasing or arrangement is assessed: rests, delayed entries, early releases, decay, response windows, density limits, or register reserved for other parts
9. A backing-track or musical-application structure
10. A bounded recording or evidence task
11. A shorter fallback version for limited time or fatigue
12. A lightweight review prompt and the likely next generation input

Rules:
- Prefer fragments, loops, and sections over full songs
- Reference reusable IDs instead of copying their full definitions
- Do not apply every dimension to every session
- Limit simultaneous primary constraints; when the session is overloaded, defer lower-priority dimensions
- Describe musical intent before gear settings
- Avoid artist imitation; extract general musical traits only
- Do not increase tempo at the expense of timing, intonation, articulation, expression, space, or relaxed motion
- Treat space as intentional musical data, not an omitted event
- Keep evidence actionable and avoid scores, streaks, dashboards, or productivity metrics
- Make outputs portable across GarageBand, Guitar Pro, MuseScore, Flow, or another DAW
```
