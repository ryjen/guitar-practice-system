# G Mixolydian — hear the flat seventh

## Practice intent

Establish **G** as the tonal centre and make the Mixolydian flat seventh (**F**) audible and deliberate rather than treating G Mixolydian as a C-major scale starting on G.

- **Session ID:** `session-g-mixolydian-flat-seventh`
- **Mode:** G Mixolydian
- **Tonal centre:** G
- **Pitch collection:** G A B C D E F
- **Interval formula:** 1 2 3 4 5 6 b7
- **Characteristic degree:** b7 — F
- **Tonic chord:** G / G7 — G B D, with F available as dominant colour
- **Supporting harmony:** `G | G | F | F`
- **Backing-track request:** `examples/backing-tracks/g-mixolydian-request.json`
- **Progression preset:** `progression-modal-mixolydian-i-bvii`
- **MIDI key signature:** C major
- **Target backing-track tempo:** 108 BPM
- **Meter:** 4/4

The C-major key signature describes the shared pitch collection for MIDI metadata. G remains the tonal centre.

## Hear before mapping

Use a G drone, looper, sustained G, or repeated low G.

1. Sing and play G.
2. Sing and play B, the major third.
3. Sing and play D, the fifth.
4. Sing **F**, the flat seventh, against the G drone.
5. Replace F with F# once to hear parallel G Ionian, then restore F.

**Ear cue:** the primary contrast is G Mixolydian's F natural against G Ionian's F#. If the ear starts hearing C as home, return to the G drone and a G-major triad before continuing.

## Fretboard map

Start from the G root on the low E string, 3rd fret, and use the nearby 3rd–5th fret region.

Mark only:

- G roots;
- G-major chord tones G, B, D;
- F natural as the characteristic tone.

Build short paths from a root or chord tone to F instead of running the entire scale. Then connect one adjacent region while retaining G as the audible centre.

CAGED, 3-notes-per-string, interval shapes, and horizontal single-string views are interchangeable navigation choices. Do not label a physical box itself as “Mixolydian”; the harmonic context and tonal centre create the mode.

## Timing realization

```yaml
rhythm_meter_id: rhythm-straight-4-4
timing:
  start: {bpm: 64, beat_unit: quarter}
  target: {bpm: 108, beat_unit: quarter}
  subdivision: {value: eighth, notes_per_beat: 2}
  click: {mode: every-beat, pulse_unit: quarter, accent: downbeat}
  strategy: ladder
  increment_bpm: 4
  clean_repetitions: 3
  max_failed_attempts: 2
  stop_condition: accumulating tension, loss of G tonal centre, or degraded muting
  final_check: 108 BPM over g-mixolydian-vamp-108 with one recorded musical-context take
```

Use the 4-BPM ladder only while the phrase remains relaxed and centred. The final 108-BPM pass is a musical-context check over the canonical backing-track realization, not a speed benchmark by itself.

## Phrase constraints

Over `G | G | F | F`:

1. Phrase one: use only G, B, and D.
2. Phrase two: repeat the contour but replace one chord tone with F.
3. Phrase three: land deliberately on F over the F chord, then resolve toward G or D when G returns.
4. Phrase four: use F as an upper or lower neighbour rather than a final destination.

Constraints:

- maximum six notes per phrase;
- leave at least one full beat empty after every response phrase;
- do not turn the F chord into a cadence toward C;
- vary attack or dynamics before adding note density;
- let the final G decay long enough to reinforce the tonic.

## Backing-track application

Resolve or render the checked-in request through the ordinary backing-track path:

```bash
python scripts/resolve_backing_track_request.py examples/backing-tracks/g-mixolydian-request.json
```

The deterministic form should resolve to:

```text
G | G | F | F
```

Use guitar alone, a G drone, a looper, or the generated MIDI. The backing track supplies context; it does not prove that the phrase actually sounds G-centred.

## Success cues

Review the take with concrete observations:

- Did G remain perceptually stable as home?
- Was F natural deliberately heard and used as b7 rather than merely included in a scale run?
- Could F natural be distinguished from F# against the same G tonic?
- Did chord-tone landings sound intentional?
- Did moving to another fretboard region preserve the same G-centred hearing?
- Did the accompaniment and guitar leave enough **space** for the flat-seventh colour to register?

Capture the largest audible defect and one next action.

## Real-session validation status

**Not yet validated by a real playing session.** The example is a bounded practice hypothesis. Play and record it before using it as the template for the remaining modes; repeated friction belongs in #85/#87, while one-off friction should remain a note rather than becoming new ontology.
