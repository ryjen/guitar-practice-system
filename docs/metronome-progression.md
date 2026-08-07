# Metronome and Tempo Progression

## Purpose

Metronome use is a concrete realization of the existing Rhythm dimension. It is not a separate curriculum and it does not replace drum loops, backing tracks, recordings, or musical-context checks.

A useful timing realization always states:

- tempo and beat unit
- meter and grouping
- subdivision or notes per beat
- click mode and pulse unit
- progression strategy
- repetitions or duration
- rest, stop, and fallback rules
- the quality gate being protected

`80 BPM` is incomplete. In 6/8 it may mean a dotted-quarter pulse or an eighth-note pulse. In 7/8 it must also state the grouping.

## Ownership and precedence

1. An approved session override owns today's realization.
2. A song section or backing track owns its canonical performance realization.
3. A technique or exercise may provide safe defaults and progression guidance.
4. A rhythm definition provides reusable meter, grouping, pulse, and feel guidance.
5. A conservative system fallback is used only when no more specific source exists.

A slow practice realization never rewrites a song's canonical target tempo. Evidence records what happened; it does not silently promote mastery or mutate targets.

## Default progression

1. **Learn / inspect** — establish counting, fingering, synchronization, muting, and relaxed motion.
2. **Slow / diagnostic** — expose uneven timing, excess movement, poor articulation, and tension.
3. **Medium / working** — build repeatability and endurance.
4. **Target / musical** — perform at the tempo and feel required by the use case.
5. **Stretch / exposure** — use brief work above target; never treat it as mastery evidence by itself.
6. **Internal-clock validation** — reduce click density or move to a drum loop, backing track, or recorded context take.

Very slow practice is not automatically correct for every fast technique. When extreme slowing changes the required mechanics, use short loops, bounded bursts, hands-separated work, or a tempo pyramid instead.

## Progression strategies

### Ladder

Increase by 2–5 BPM after clean repetitions. Repeat at the same tempo after a minor defect. Reduce by about 5 BPM or shorten the loop after repeated defects.

### Tempo pyramid

Rise through two or three steps, drop one step, then rise again. This reduces the tendency to equate every repetition with a new maximum.

### Burst

Play a short fragment at target speed, recover, then repeat. Use this when slow motion no longer resembles the target mechanics.

### Subdivision progression

Keep the pulse stable while moving from quarter notes to eighths, triplets, or sixteenths. BPM and subdivision must be recorded together.

### Loop expansion

Practise the failing transition, then one beat, one bar, and a longer phrase. Increase context before increasing speed when the problem is coordination rather than raw motion.

### Sparse-click validation

Keep the tempo stable while reducing click density: every beat, backbeat, half-note, one click per bar, gap click, then count-in followed by silence.

## Default adaptive rules

- Three clean repetitions with stable timing and no material tension permit an in-session increase.
- A minor defect repeats the current realization.
- Repeated or major defects reduce tempo, shorten the loop, or simplify articulation.
- Persistent failure changes strategy rather than repeatedly forcing the same failed attempt.
- Pain, fatigue, or accumulating tension stops the drill.
- Target-tempo success requires later-session and musical-context verification before promotion.

The three-clean-repetition rule controls only an in-session step. Existing multi-session quality gates remain authoritative.

## Conservative starting guidance

| Practice category | Initial realization | Main concern |
|---|---|---|
| Goal-directed warmup | 50–70 BPM, quarter or eighth notes | readiness and relaxation |
| Scales, CAGED, modes | about 60 BPM, eighth notes | evenness and accents |
| Alternate or hybrid picking | about 60 BPM, eighth notes | synchronization and string crossing |
| Legato | about 55 BPM | volume balance and muting |
| Sweep or economy motion | 40–60 BPM or bounded bursts | motion path and note separation |
| Chord changes | explicit beats or bars per change | transition quality and harmonic rhythm |
| Rhythm guitar | slow, medium, then target | groove, muting, dynamics, endurance |
| Slide, wah, E-Bow, phrasing | context-specific | placement, sustain, dynamics, and space |
| Compound or odd meter | explicit beat unit and grouping | pulse and accent structure |

These values are defaults for generated plans, not universal achievement thresholds.

## Click modes

- every beat
- accented downbeat
- backbeat on 2 and 4
- half-note or half-time pulse
- one click per bar
- off-beat click
- silent-bar or gap click
- count-in followed by silence
- additive grouping accents such as `2+2+3`

Sparse, off-beat, and gap modes test the internal clock and are not beginner defaults.

## Worked example: straight 4/4

```yaml
rhythm_meter_id: rhythm-straight-4-4
timing:
  start: {bpm: 60, beat_unit: quarter}
  target: {bpm: 90, beat_unit: quarter}
  subdivision: {value: eighth, notes_per_beat: 2}
  click: {mode: every-beat, pulse_unit: quarter, accent: downbeat}
  strategy: ladder
  increment_bpm: 3
  clean_repetitions: 3
  max_failed_attempts: 2
  stop_condition: accumulating tension or degraded muting
  final_check: 90 BPM with backbeat click, then one recorded backing-track take
```

## Worked example: grouped 7/8

```yaml
rhythm_meter_id: rhythm-7-8-2-2-3
timing:
  start: {bpm: 80, beat_unit: eighth}
  target: {bpm: 100, beat_unit: eighth}
  grouping: [2, 2, 3]
  subdivision: {value: eighth, notes_per_beat: 1}
  click:
    mode: additive-accents
    pulse_unit: eighth
    accent_pattern: [strong, weak, strong, weak, strong, weak, weak]
  strategy: loop-expansion
  clean_repetitions: 3
  final_check: one click per grouped pulse, then a recorded musical phrase
```
