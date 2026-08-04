# Song Use-Case Layer

## Purpose

Songs and passages validate, motivate, and integrate technique work. They are not the primary curriculum and do not own technique progression or candidate discovery.

## Boundaries

Song use cases own:

- approved song and passage identity
- section boundaries and practice slices
- technique references
- prerequisites and difficulty
- genre, style, and arrangement context
- tuning, capo, meter, and tempo context
- gear-setup and backing-track references
- section and full-performance evidence
- maintenance state
- copyright-safe source references

Song use cases do not own:

- technique definitions or mastery state
- duplicated signal-chain settings
- backing-track MIDI or arrangement source
- recommendation search or candidate ranking
- complete unauthorized notation or tablature

The Discovery layer searches for and ranks possible use cases. A song enters this layer only after explicit approval.

## Genre and style taxonomy

Genre is a first-class catalog dimension. The initial canonical genres are:

- `80s-rock`
- `alt-rock`
- `blues`
- `country`
- `jazz`

Styles and substyles sit beneath a genre:

| Genre | Example styles / substyles |
|---|---|
| `80s-rock` | hard rock, glam metal, arena rock, melodic rock, shred, new-wave guitar |
| `alt-rock` | grunge, post-grunge, indie rock, shoegaze, noise rock, post-punk revival |
| `blues` | Delta, Chicago, Texas, electric blues, blues-rock, jump blues |
| `country` | country-rock, Bakersfield, classic country, western swing, chicken picking, modern country |
| `jazz` | blues-jazz, swing, bebop, modal, jazz-rock/fusion, chord melody |

A song may have one primary genre and multiple secondary genre/style tags. Canonical taxonomy remains small and human-reviewed; Discovery may suggest tags but cannot create canonical categories automatically.

## Lifecycle

1. `candidate`
2. `mapped`
3. `sections-in-progress`
4. `slow-clean-playthrough`
5. `target-tempo-playthrough`
6. `recorded`
7. `maintenance`
8. `retired`

A song may regress without changing linked technique states. Technique progress can continue when a song is paused or retired.

## Active-work limit

The default active limit is three songs or passages:

- one rhythm or accompaniment use case
- one melodic or lead use case
- one optional branch or experimental use case

Candidates do not count as active until a section is deliberately scheduled.

## Song record

Each record includes:

- stable ID
- title and artist/composer attribution
- musical role
- primary genre and secondary style tags
- arrangement/version reference
- tuning, capo, meter, and approximate target tempo
- prerequisite techniques
- gear setup IDs
- backing-track IDs or requirements
- section map
- evidence references
- status and maintenance cadence
- licensed notation/tab reference where applicable

## Section-level mapping

| Section | Time/bar reference | Technique IDs | Difficulty | Target tempo | Dominant defect | Evidence state |
|---|---|---|---|---|---|---|
| Intro | | | | | | |
| Verse | | | | | | |
| Chorus | | | | | | |
| Bridge | | | | | | |
| Solo/lead | | | | | | |
| Outro | | | | | | |

Section boundaries may use timestamps, rehearsal marks, or bar ranges from a licensed source. Do not reproduce complete copyrighted notation.

## Completion gates

A section is ready when:

- structure and fingering are stable
- it succeeds three consecutive times without stopping
- linked timing and articulation gates pass
- transitions into and out of the section are tested
- one evidence recording exists

A song reaches `recorded` when:

- the complete structure is memorized or reliably followed
- transitions are stable
- one uninterrupted full take exists
- mistakes do not derail recovery
- repeatability-affecting tone and arrangement decisions are documented

Song completion demonstrates technique use in one context; it does not imply transferable mastery.

## Musical vocabulary index

Records may expose reusable vocabulary such as syncopated rhythm, palm-muted accents, expressive bends, vibrato, slide phrasing, rhythmic wah, E-Bow counterlines, hybrid-picked double-stops, chord-tone fills, jazz comping, voice leading, and chord melody.

Store vocabulary as technique references or controlled tags so use cases remain searchable by transferable skill.

## Evidence and maintenance

Recommended evidence sequence:

1. baseline section take
2. first clean isolated section
3. first joined transition
4. slow full-form take
5. target-tempo full take
6. best retained take
7. maintenance check

Raw recordings remain outside Git unless an explicit storage policy says otherwise.

Suggested maintenance cadence:

- newly recorded: weekly for two to four weeks
- stable repertoire: every two to four weeks
- deeply retained: quarterly or before performance/recording

Regress only the affected section or quality dimension where practical.

## Copyright boundary

Allowed repository content includes attribution, short section/time references, harmonic and structural analysis, technique observations, original exercises, personal evidence notes, and links to licensed sources.

Do not commit unauthorized complete tablature, notation, lyrics, isolated stems, or reconstructed backing tracks that substantially reproduce a copyrighted recording.

## Selection policy

Concrete use cases are intentionally deferred. Add one only when:

- Discovery or a human identifies a useful candidate
- the candidate is explicitly approved
- a technique needs musical validation
- source and copyright boundaries are clear
- it fits within the active-work limit
- a section-level outcome is defined
- it does not create redundant backlog work

The catalog may remain empty until those conditions are met.
