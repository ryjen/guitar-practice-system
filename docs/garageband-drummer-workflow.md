# GarageBand Drummer Workflow

## Purpose

Use GarageBand drummer as a fast backing-track scaffold, not as the canonical source.

The source should be a drummer spec that maps sections to feel, energy, complexity, fills, and arrangement cues.

## Section mapping

| Song section | Drummer role | Typical settings |
|---|---|---|
| Intro | establish pulse, leave space | low complexity, low-mid loudness, minimal fills |
| Verse | support riff or vocal pocket | steady groove, limited cymbals, sparse fills |
| Pre-chorus | build tension | slightly higher loudness, more tom/cymbal movement |
| Chorus | release energy | louder, more open, stronger backbeat |
| Bridge | change texture | reduced kit, halftime, tom groove, or sparse pulse |
| Outro | repeat / deconstruct | either build or strip down |

## Workflow

1. Draft a song-structure spec
2. Create drummer settings per section
3. Build sections in GarageBand
4. Add bassline or chord vamp
5. Record guitar fragments over the scaffold
6. Export useful bounces or MIDI-like notes
7. Keep the Markdown spec as source

## Practical constraints

- Name sections clearly in GarageBand
- Use arrangement markers when possible
- Keep first versions short: 8 to 32 bars
- Avoid perfecting drums before the guitar idea works
- Record rough guitar early

## Drummer spec fields

See [`templates/garageband-drummer-spec.md`](../templates/garageband-drummer-spec.md).

Minimum useful fields:

- tempo
- time signature
- feel
- section list
- drummer energy per section
- complexity per section
- fill density
- kick/snare notes
- cymbal/tom notes

## Example use

Start with a post-punk bass groove:

- 142 BPM
- straight eighths
- tight kick/snare lock
- sparse verse
- open chorus
- bridge with tom pulse

Then record wah accents and delay hooks over it.
