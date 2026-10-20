# Travelling Riverside Blues — video cue map and reference-form audit

**Status:** working shortened arrangement, **not** an exact Zeppelin transcription.  
**Reference:** Led Zeppelin, BBC Maida Vale recording, 24 June 1969; 1990 promo uses that performance.  
**Working key / meter / tempo:** G, 4/4, 108 quarter-note BPM. Guitar reference is often played in open G (DGDGBD), but the MIDI backing does not impose a guitar tuning.  
**Backline priority:** separately editable drums and bass; live guitar and vocals omitted.
**Variation revision:** occasional lead-in/lead-out quarter-note bass movement and
quarter-beat drum doubles are seeded and committed in the manifest, so section
timestamps do not change and the track can be overdubbed repeatedly.
This is original accompaniment movement, not a transcription.

## Verified structural observations versus unverified bar counts

- Led Zeppelin's official account describes a riff-driven spontaneous performance with overdubbed lead guitar; a fixed arrangement inferred from a generic 12-bar chart is not reliable.
- Independent published guitar descriptions identify a recurring **two-measure slide/riff figure** and distinguish it from the blues verse sequence. Riff returns are a distinct arranging role, not merely G7 for a fixed four bars.
- Published bass descriptions identify a recurring intro/return figure and more melodic movement through verse changes. A static root/fifth accompaniment is a convenient rehearsal scaffold, not a faithful recreation.
- Commercially published editions support G / 4/4 and multi-part guitar/voice scoring.
- **NOT established from authoritative, time-aligned listening:** the original's complete measure counts, beat-accurate section boundaries, pickup timing, tempo map, fills, and ending length. Any future exact-reference timecodes must carry a captured source version and evidence.

Sources: [official BBC session](https://www.ledzeppelin.com/show/maida-vale-bbc-studios-june-24-1969), [official promo](https://www.ledzeppelin.com/video/travelling-riverside-blues-promo), [fan guitar form description](https://musicnoteslib.com/tabs/Led_Zeppelin-Travelling_Riverside_Blues-513901.html), [fan bass form description](https://www.e-chords.com/bass/led-zeppelin/travelling-riverside-blues), [commercial G / 4/4 scoring metadata](https://www.musicnotes.com/sheetmusic/led-zeppelin/traveling-riverside-blues/MN0099563).

## Rehearsal / recording beat map (generated *from our own manifest*)

This table **does not give timestamps in the Zeppelin recording**. It gives positions on our fixed-tempo backing, useful for recording and cutting video. Count-in is two bars / `00:04.44`. Every 4/4 bar occupies `2.2222` seconds.

| Section marker | Musical bars | Bars | Backing start | Backing end | Recording role |
|---|---:|---:|---:|---:|---|
| INTRO-RIFF | 1–8 | 8 | 00:04.44 | 00:22.22 | riff intro, guitar pickup |
| VERSE-1 | 9–20 | 12 | 00:22.22 | 00:48.89 | vocal blues passage |
| RIFF-REFRAIN-1 | 21–28 | 8 | 00:48.89 | 01:06.67 | G vamp / response |
| VERSE-2 | 29–40 | 12 | 01:06.67 | 01:33.33 | vocal blues passage |
| RIFF-REFRAIN-2 | 41–48 | 8 | 01:33.33 | 01:51.11 | G vamp / response |
| SOLO-BLUES | 49–60 | 12 | 01:51.11 | 02:17.78 | solo changes |
| OUTRO-RIFF | 61–68 | 8 | 02:17.78 | 02:35.56 | closing riff |
| END | 69 | 0 | 02:35.56 | — | Trim or hold ending manually |

Approximate music duration: `02:31.11`; total timeline including count-in: `02:35.56` before note tails/reverb. Section lengths (8/12 bars) were *chosen* for an abbreviated video version, not counted from the source performance.

## Reference-to-cover alignment worksheet

Record these fields only after inspecting the same identified commercial release in a DAW. The version matters (1990 box-set audio, BBC Sessions mastering, and video edit may have different leading silence or timings).

| Reference cue | Reference timestamp | Reference musical bar / beat | Result / confidence |
|---|---|---|---|
| First complete two-bar riff phrase | **unmeasured** | **unmeasured** | awaiting A/B listening |
| First vocal entry | **unmeasured** | **unmeasured** | waiting |
| First blues-verse-to-riff return | **unmeasured** | **unmeasured** | waiting |
| Subsequent vocal return | **unmeasured** | **unmeasured** | waiting |
| Guitar solo starts/ends | **unmeasured** | **unmeasured** | waiting |
| Last riff / final resolution | **unmeasured** | **unmeasured** | waiting |

Do not promote fan-tab approximate cues to verified reference timing or copy note-for-note commercial riffs into this public repository. Private personal listening notes, reference audio, and any licensed score stay outside this public source tree.

## How to audit it efficiently in REAPER

1. Insert the exact reference recording on its own non-export track, with source version, duration and any offset noted.
2. Align the **first downbeat**, not just file start; mark recurring two-measure riff cycles and actual vocal/solo entrances. Use transient peaks for bass drum/snare, but confirm by ear.
3. Check whether quarter-note **108 BPM is a usable performance tempo**, rather than asserting the record has exactly that BPM. Mark any swing, half-time, pushes, pickups and tempo drift. Never force unstable source timing onto the grid without noting it.
4. Mark *actual* section transitions with time, bar, and confidence; compare the reference form against the video form in the table above. First decide whether to **cover the exact form** or retain the explicitly shortened arrangement.
5. Audition bass and drums without guitars: kick alignment, melodic bass contour in riff sections, section-based fills, and a real ending. Treat any generic generated notes as placeholders.
6. Generate the repository MIDI with `nix develop` and `guitarctl backing generate`; import and route drums/bass to separate instruments. Export stems aligned from project zero, with identical sample rate/length and two-bar count-in.
7. Lock an approved backing revision, record video/guitar/vocal to that **same** bounce, and retain the bounce hash plus tempo/section-map revision for synchronized overdubs.

## Acceptance / hold points

- [x] Independent references establish recurring riff-versus-verse arrangement contrast.
- [x] Original shortened G/108 source manifest explicitly declares distinct section roles.
- [x] Rehearsal timecodes are derived from the declared tempo and section lengths, not misrepresented as source timestamps.
- [ ] Reference audio/version established and measured cue timings recorded.
- [ ] Musical phrase and drum/bass changes audited against the chosen reference.
- [ ] Generated MIDI actually auditioned with selected DAW drum and bass instruments.
- [ ] Final stem exports and music-video sync independently listened through.

## Producer's decision

For a weekend music video, prioritize **a locked 2:36 original-style accompaniment** rather than a speculative five-minute transcription. A complete reference-cover recreation is a separate, evidence-gated arrangement task.
