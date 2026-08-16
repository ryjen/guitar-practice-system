# D Dorian — hear the natural sixth

## Practice intent

Establish **D** as the tonal centre and make the Dorian natural sixth (**B**) audible and deliberate rather than treating D Dorian as a C-major scale starting on D.

- **Session ID:** `session-d-dorian-natural-sixth`
- **Mode:** D Dorian
- **Tonal centre:** D
- **Pitch collection:** D E F G A B C
- **Interval formula:** 1 2 b3 4 5 6 b7
- **Characteristic degree:** natural 6 — B
- **Tonic chord:** Dm — D F A
- **Supporting harmony:** `Dm | Dm | G | G`
- **Backing-track request:** `examples/backing-tracks/d-dorian-request.json`
- **Progression preset:** `progression-modal-dorian-i-iv`
- **MIDI key signature:** C major
- **Target backing-track tempo:** 96 BPM
- **Meter:** 4/4

The C-major key signature describes the shared pitch collection for MIDI metadata. It does **not** make C the tonal centre. Keep D perceptually anchored throughout the exercise.

## Hear before mapping

Use a D drone, looper, sustained D, or repeated low D.

1. Sing and play D.
2. Sing and play F, the minor third.
3. Sing and play A, the fifth.
4. Sing **B** against the D drone and notice the brighter minor colour.
5. Replace B with Bb once, then restore B.

**Ear cue:** the important contrast is D Dorian's B natural against D Aeolian's Bb. If B sounds like an arbitrary C-major passing note rather than colour belonging to D, re-establish the D drone before continuing.

## Fretboard map

Start from the D root on the A string, 5th fret, and work in one compact surrounding region before connecting positions.

Mark only:

- D roots;
- Dm chord tones D, F, A;
- B natural as the characteristic tone.

Do not begin by running a seven-note box. First locate root → b3 → 5, then add B. After the sound is stable, connect one adjacent region using a D, F, A, or B as the linking tone.

Alternative views are valid: CAGED, 3-notes-per-string, interval shapes, or a horizontal single-string map. The tonal centre and target degrees stay unchanged when the fretboard representation changes.

## Timing realization

```yaml
rhythm_meter_id: rhythm-straight-4-4
timing:
  start: {bpm: 60, beat_unit: quarter}
  target: {bpm: 96, beat_unit: quarter}
  subdivision: {value: eighth, notes_per_beat: 2}
  click: {mode: every-beat, pulse_unit: quarter, accent: downbeat}
  strategy: ladder
  increment_bpm: 4
  clean_repetitions: 3
  max_failed_attempts: 2
  stop_condition: accumulating tension, loss of D tonal centre, or uncontrolled string noise
  final_check: 96 BPM over d-dorian-vamp-96 with one recorded musical-context take
```

At slow tempo, test pitch choice and articulation rather than speed. At medium tempo, preserve even eighth-note placement. At target tempo, stop thinking in scale order and phrase against the vamp.

## Phrase constraints

Over `Dm | Dm | G | G`:

1. Phrase one: use only D, F, and A.
2. Phrase two: keep the same contour but introduce B once as a deliberate colour tone.
3. Phrase three: land on B over G, then resolve to A or D when Dm returns.
4. Phrase four: answer with fewer notes than phrase three.

Constraints:

- maximum six notes per phrase;
- leave beat four empty in at least every second bar;
- do not end every phrase on B;
- let one note decay fully before the next phrase;
- avoid repeatedly resolving toward C.

The aim is for B to sound intentional while **D remains home**.

## Backing-track application

Resolve or render the checked-in request through the ordinary backing-track path:

```bash
python scripts/resolve_backing_track_request.py examples/backing-tracks/d-dorian-request.json
```

The deterministic form should resolve to:

```text
Dm | Dm | G | G
```

Use guitar alone, a D drone, a looper, or the generated MIDI. The MIDI is a practice realization, not evidence that the modal centre is perceptually successful.

## Success cues

A useful take should make these questions answerable without a proficiency score:

- Did D still sound like home after several bars?
- Was B natural deliberately heard and targeted rather than merely passed through?
- Could B natural be distinguished from Bb by ear against the same D tonal centre?
- Did phrases resolve intentionally to D, F, A, or B?
- Did position changes preserve the same D-centred hearing?
- Did the arrangement leave enough **space** for B and the phrase endings to register?

Capture the largest audible defect and one next action.

## Real-session validation status

**Not yet validated by a real playing session.** Do not treat this worked example as proven practice material until it has been played, recorded, and reviewed. Feed repeated friction into #85/#87; do not expand the schema for one-off inconvenience.
