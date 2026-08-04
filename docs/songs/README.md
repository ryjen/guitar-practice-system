# Song Use-Case Layer

## Purpose

Songs and passages validate, motivate, and integrate technique work. They are not the primary curriculum and do not own technique progression.

This layer answers questions such as:

- Which technique does this section exercise?
- Which gear setup and backing context support it?
- What evidence shows the section or full song is playable?
- Which completed songs need maintenance?

## Boundaries

Song use cases own:

- song and passage identity
- section boundaries and practice slices
- technique references
- prerequisites and difficulty
- tuning, capo, and tempo context
- gear-setup references
- backing-track references
- section and full-performance evidence
- maintenance state
- copyright-safe source references

Song use cases do not own:

- the definition or mastery state of a technique
- duplicated signal-chain settings
- backing-track MIDI or arrangement source
- complete unauthorized notation or tablature

## Lifecycle

Use these states independently for each song:

1. `candidate`
2. `mapped`
3. `sections-in-progress`
4. `slow-clean-playthrough`
5. `target-tempo-playthrough`
6. `recorded`
7. `maintenance`
8. `retired`

A song may regress without changing the state of its linked techniques. Likewise, technique progress can continue even when a song is paused or retired.

## Active-work limit

The default active limit is three songs or passages:

- one rhythm or accompaniment use case
- one melodic or lead use case
- one optional branch or experimental use case

This is configurable, but increasing it should be deliberate. Candidates do not count as active until a section is scheduled for practice.

## Song record

Each record should include:

- stable ID
- title and artist/composer attribution
- musical role
- style and arrangement reference
- tuning, capo, meter, and approximate target tempo
- prerequisite techniques
- gear setup IDs
- backing-track IDs or requirements
- section map
- evidence references
- status and maintenance cadence
- licensed notation/tab reference where applicable

## Section-level mapping

Map sections instead of treating the song as one task.

| Section | Time/bar reference | Technique IDs | Difficulty | Target tempo | Dominant defect | Evidence state |
|---|---|---|---|---|---|---|
| Intro | | | | | | |
| Verse | | | | | | |
| Chorus | | | | | | |
| Bridge | | | | | | |
| Solo/lead | | | | | | |
| Outro | | | | | | |

Section boundaries may use timestamps, rehearsal marks, or bar ranges from a licensed source. Avoid reproducing full copyrighted notation.

## Completion gates

A section is ready when:

- its structure and fingering are stable
- it can be played three times consecutively without stopping
- timing and articulation meet the linked technique gates
- transitions into and out of the section are tested
- one evidence recording exists

A song reaches `recorded` when:

- the complete structure is memorized or reliably followed
- transitions are stable
- one uninterrupted full take exists
- mistakes do not derail recovery
- tone and arrangement decisions are documented only where they affect repeatability

Song completion does not imply technique mastery. The song demonstrates technique use in one musical context.

## Musical vocabulary index

Songs may expose reusable vocabulary such as:

- syncopated rhythm
- palm-muted accents
- expressive bends
- vibrato control
- slide phrasing
- rhythmic or parked wah
- E-Bow drones and counterlines
- hybrid-picked double-stops
- chord-tone fills
- open-string articulation

Store these as technique references or vocabulary tags so the repository can find several use cases for the same transferable skill.

## Evidence

Recommended evidence sequence:

1. baseline section take
2. first clean isolated section
3. first joined transition
4. slow full-form take
5. target-tempo full take
6. best retained take
7. maintenance check

Raw recordings remain outside Git unless an explicit storage policy says otherwise. Store stable references and concise observations.

## Maintenance rotation

Completed songs should not remain permanently active.

Suggested cadence:

- newly recorded: weekly for two to four weeks
- stable repertoire: every two to four weeks
- deeply retained: quarterly or before performance/recording

A failed maintenance take should regress the affected section or dimension, not erase unrelated progress.

## Copyright boundary

Allowed repository content includes:

- song and artist attribution
- short section/time references
- harmonic and structural analysis
- technique observations
- original exercises
- personal evidence notes
- links or citations to licensed sources

Do not commit unauthorized complete tablature, notation, lyrics, isolated stems, or reconstructed backing tracks that substantially reproduce a copyrighted recording.

## Selection policy

Concrete song use cases are intentionally deferred. Add one only when:

- a technique needs musical validation
- the source and copyright boundary are clear
- the song fits within the active-work limit
- a section-level practice outcome is defined
- adding it will not create a redundant backlog entry

The catalog may remain empty until those conditions are met.
