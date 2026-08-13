# ii–V–I through the circle of fourths

## Reusable progression

- **ID:** `progression-jazz-major-ii-v-i`
- **Catalog:** `catalogs/progressions/catalog.json`
- **Intent:** hear and connect predominant, dominant, and tonic motion
- **Tonal-centre behaviour:** functional
- **Abstract Roman numerals:** `ii7 | V7 | Imaj7`
- **Catalog realization:** `ii7 | V7 | Imaj7 | Imaj7`
- **Harmonic functions:** predominant | dominant | tonic | tonic
- **Bars:** four in the executable practice realization

The first three bars define the harmonic identity. The repeated tonic bar gives time to hear resolution, inspect guide tones, leave space, and prepare the next key. The reusable identity does not own a key, tempo, fretboard position, or voicing.

Resolve one key directly:

```bash
python3 scripts/progression_catalog.py resolve progression-jazz-major-ii-v-i C
```

## Traversal strategy

- **Canonical order:** C, F, B♭, E♭, A♭, D♭, G♭, B, E, A, D, G
- **Enharmonic alias:** F♯ may be supplied as the start key and normalizes to the G♭ position
- **Relationship:** each new tonic is a fourth above the previous tonic, with the G♭/B boundary using the practical enharmonic spelling above
- **Initial scope:** four adjacent keys per session
- **Expansion:** add keys only after voice leading remains controlled

Generate the first four tonic positions:

```bash
python3 scripts/progression_catalog.py fourths \
  progression-jazz-major-ii-v-i \
  --start-key C \
  --count 4
```

The traversal resolver is bounded to one through twelve positions and may start anywhere in the canonical sequence. It wraps deterministically.

## Reference realization

| Tonic | ii7 | V7 | Imaj7 | Imaj7 |
|---|---|---|---|---|
| C | Dm7 | G7 | Cmaj7 | Cmaj7 |
| F | Gm7 | C7 | Fmaj7 | Fmaj7 |
| B♭ | Cm7 | F7 | B♭maj7 | B♭maj7 |
| E♭ | Fm7 | B♭7 | E♭maj7 | E♭maj7 |

A committed backing-track request for the first position is available at `examples/backing-tracks/ii-v-i-c-request.json`. It uses the same progression preset, so the concrete chord list is resolved rather than duplicated.

## Practice session

- **Primary goal:** hear guide-tone resolution while moving through four keys
- **Duration:** 20 minutes
- **Tempo:** 60 BPM for isolated voicing work; the committed swing backing-track request uses 80 BPM to remain inside the validated groove range
- **Meter:** 4/4
- **Harmonic rhythm:** one chord per bar; repeat tonic for a fourth bar
- **Fretboard view:** nearest available shell voicings; CAGED labels optional
- **Ear targets:** sing thirds and sevenths before playing
- **Technique target:** clean chord changes with minimal hand movement

### Warmup

1. Play and sing the third and seventh of each chord in C.
2. Resolve the guide tones from G7 to Cmaj7.
3. Repeat in F without changing register unless necessary.

**Readiness cue:** the dominant seventh resolves downward and the leading tone resolves upward without searching.

## Expression and space

- Leave beat four empty after each tonic chord.
- Do not fill the gap with a pickup until the basic voice leading is reliable.
- On the second pass, answer each chordal statement with one short single-note phrase.
- Maximum four notes in each response.

The silence makes the tonic resolution audible and creates a clear boundary before the next key.

## Evidence

Record one uninterrupted four-key pass.

Review:

- Did the guide tones resolve clearly?
- Did the fourths traversal remain audible rather than feeling like unrelated shapes?
- Did the empty fourth beat clarify the cadence?
- What was the largest audible defect?

## Variants

- Reverse through fifths.
- Use minor ii–V–i.
- Use shell voicings only.
- Improvise using only thirds and sevenths.
- Increase harmonic rhythm to two chords per bar only after the slow version remains musical.
