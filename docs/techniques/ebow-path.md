# E-Bow Guitar Path

## Goal

Develop reliable E-Bow control for sustained melodies, swells, harmonics, drones, counterlines, and layered arrangements. The technique should produce intentional attacks, stable sustain, clean string transitions, and expressive dynamics without relying on effects to hide activation noise or pitch instability.

## Baseline recording

Record one dry or minimally processed take containing:

1. Four sustained notes in normal mode, each held for eight beats.
2. Four sustained notes in harmonic mode.
3. Four adjacent-string changes and two non-adjacent changes.
4. A short melody of four to eight bars.
5. One uninterrupted textural layer over a simple drone or backing track.

For each section, note the largest audible issue:

- delayed or inconsistent activation
- abrupt attack
- excessive volume bloom
- string-transition transient
- unstable sustain
- pitch or vibrato drift
- harmonic-mode squeal or collapse
- noise floor
- masking from effects

The recording may remain local or externally linked. Store only a stable identifier and observations in the technique evidence table.

## Operating model

The E-Bow creates a feedback loop between its magnetic field and one string. The main control variables are:

- longitudinal position relative to the pickup and string hot spot
- lateral alignment over one string
- height and contact pressure against the guide grooves
- time allowed for activation
- pickup selection and gain
- left-hand pitch, vibrato, and damping
- movement before, during, and after the note

The central skill is not merely making a string sustain. It is controlling when the note appears, how it grows, how it changes strings, and how it leaves.

## Signal-chain and gain model

Default starting chain:

```text
guitar -> light compression or clean gain -> modulation -> delay/reverb -> amp/interface
```

A compressor is optional. It can smooth activation and sustain, but it can also raise noise and make uncontrolled blooms harder to hear.

### Trade-offs

| Choice | Benefit | Risk | Default |
|---|---|---|---|
| Neck pickup | Easier activation, rounder sustain | Can become woolly | Start here |
| Bridge pickup | More definition and harmonics | Less forgiving hot spot | Add later |
| Clean tone | Exposes dynamics and noise | Requires precise activation | Primary diagnostic tone |
| Mild gain | Faster activation and stronger sustain | More hiss and abrupt bloom | Musical-context option |
| Compression | More even sustain | Raises noise and hides poor hand control | Use lightly and compare bypassed |
| Delay/reverb | Creates depth and masks transitions musically | Can conceal attacks, releases, and pitch drift | Add after dry control |
| Noise gate | Reduces idle noise | Can cut slow activation or note tails | Avoid unless tuned carefully |

Check gain at the loudest harmonic-mode bloom, not only at the initial note level.

## Progression

### Phase 1 — activation map

Focus:

- Find the reliable activation zone for each string.
- Learn the difference between no activation, stable activation, and runaway bloom.
- Keep the E-Bow aligned without pressing hard into the strings.

Practice:

1. Select one string and one fretted note.
2. Place the E-Bow silently, then move slowly through the activation zone.
3. Repeat from heel-side and bridge-side approaches.
4. Map the hot spot for all six strings using the same pickup and gain.

Gate:

- Eight of ten notes activate within a predictable time window.
- The player can stop before an uncontrolled volume spike.
- Adjacent strings remain quieter than the target string.

### Phase 2 — controlled attack and release

Focus:

- Suppress unwanted onset transients.
- Choose whether the note fades in or appears quickly.
- End the note deliberately rather than simply lifting the device.

Practice:

- Activate before opening the fretting-hand mute for a soft swell.
- Place directly in the hot spot for a faster attack.
- Compare release by fretting-hand mute, E-Bow removal, and volume control.
- Record attacks and releases without delay or reverb.

Gate:

- Three attack shapes are repeatable: soft swell, medium onset, and fast onset.
- Releases do not leave uncontrolled open-string ringing.
- Peak level remains consistent across three passes.

### Phase 3 — stable sustain and dynamics

Focus:

- Hold a note without drift in volume or pitch.
- Shape crescendos and decrescendos using position, gain interaction, or volume control.
- Maintain relaxed left-hand vibrato.

Practice:

- Hold notes for four, eight, and sixteen beats.
- Crescendo for four beats, hold for four, decrescendo for four.
- Compare no vibrato, narrow vibrato, and wider vibrato.

Gate:

- Sustain remains stable for at least eight beats.
- Dynamic changes are gradual rather than accidental jumps.
- Vibrato does not interrupt activation or destabilize pitch.

### Phase 4 — normal and harmonic modes

Focus:

- Treat normal and harmonic modes as different instruments.
- Control activation delay and level difference between modes.
- Avoid relying on harmonic mode merely for novelty.

Practice:

- Play the same note and phrase in both modes.
- Match perceived peak level as closely as practical.
- Use harmonic mode for selected arrivals rather than entire exercises.
- Move slowly enough to distinguish stable harmonic activation from squeal or collapse.

Gate:

- Both modes activate predictably across at least three strings.
- Harmonic mode does not clip or dominate the mix unintentionally.
- Mode choice has an audible arrangement purpose.

### Phase 5 — adjacent-string transitions

Focus:

- Move laterally while preserving damping and level.
- Prevent the outgoing and incoming strings from sounding as an uncontrolled double stop.
- Coordinate fretting-hand note timing with E-Bow movement.

Practice:

1. Alternate strings 2 and 3 on whole notes.
2. Repeat on half notes.
3. Use one-beat silence between strings, then remove the silence.
4. Add simple two-note melodies across adjacent strings.

Gate:

- Three consecutive transitions have no dominant scrape, burst, or unintended double activation.
- Incoming notes activate in time with the phrase.
- Outgoing strings stop intentionally.

### Phase 6 — non-adjacent transitions and register changes

Focus:

- Cross one or more strings without triggering them.
- Preserve timing during longer physical movement.
- Use silence as part of the phrase when necessary.

Practice:

- Alternate strings 2 and 4, then 1 and 3, then 3 and 5.
- Compare silent repositioning with sustained overlap created through delay or looping.
- Build four-bar phrases with one deliberate register jump.

Gate:

- Intermediate strings do not produce prominent transient notes.
- Repositioning lands inside the intended rhythmic window.
- Register changes support the phrase rather than sounding like recovery from a mistake.

### Phase 7 — melody and counterline

Focus:

- Preserve contour, intonation, and rhythm.
- Use E-Bow sustain to connect notes selectively rather than making every note legato.
- Leave space for the primary guitar, vocal, or melody role.

Practice:

- Sing or play a short melody normally, then reproduce it with E-Bow.
- Restrict the first version to one string.
- Add one string change and one intentional rest.
- Write a counterline using fewer notes than the main melody.

Gate:

- Melody remains identifiable without effects.
- Counterline avoids competing continuously with the main part.
- Phrase endings are clear.

### Phase 8 — drones and pedal tones

Focus:

- Sustain a harmonically useful note beneath changing chords.
- Control intonation and volume over long durations.
- Recognize when the drone becomes harmonically intrusive.

Practice:

- Sustain root, fifth, and modal colour tones over a two- or four-chord progression.
- Fade out before incompatible harmony, then re-enter deliberately.
- Compare static drone, pulsed swell, and octave-register variants.

Gate:

- Drone remains in tune and below the focal part.
- Entries and exits align with harmonic changes.
- The selected pitch remains intentional across the complete form.

### Phase 9 — layered arrangement

Focus:

- Separate layers by register, rhythm, mode, tone, and stereo position.
- Avoid stacking indistinguishable sustained parts.
- Commit only parts that improve the arrangement.

Suggested layer roles:

1. Low or mid-register normal-mode drone.
2. Sparse upper-register harmonic accents.
3. Countermelody with clear rests.
4. Optional delayed or reversed texture derived from a recorded take.

Gate:

- Each layer has a distinct role.
- Muting any layer creates a clear and justifiable loss.
- Combined sustain does not mask the primary guitar or vocal range.

## Practice sessions

### 15-minute diagnostic

- 4 min activation map and peak-level check
- 4 min attack/release control
- 4 min adjacent-string transitions
- 3 min recorded sustained phrase

### 30-minute development

- 5 min dry activation and noise check
- 8 min current transition or mode drill
- 7 min melody or counterline
- 8 min backing-track take
- 2 min evidence note

### 45-minute arrangement session

- 5 min setup and level check
- 10 min current technical constraint
- 10 min one complete melodic take
- 15 min drone/counterline or layered arrangement experiment
- 5 min mute-test review and next target

Stop or reduce gain when sustained level becomes physically uncomfortable, clips the input, or causes uncontrolled feedback.

## Backing-track and arrangement scenarios

### 1. Ambient modal bed

Planned asset ID: `ebow-ambient-bed`.

Specification:

- 4/4 or free-time grid at 54-72 BPM
- sustained root/fifth foundation
- sparse percussion or no drums in the first variant
- slow harmonic movement, one chord every two to four bars
- clear space in the upper-mid register
- long loop boundaries without abrupt tails

Use for:

- activation and long-note stability
- normal/harmonic mode contrast
- register changes
- drones and sparse countermelodies

### 2. Song-arrangement counterline bed

Specification:

- verse/chorus or A/B form
- bass, restrained drums, and simple keys or rhythm guitar
- explicit gaps for E-Bow responses
- section markers for different layer roles

Use for:

- counterlines between vocal phrases
- changing from drone to melodic role
- arrangement-level bypass decisions
- two or three overdubs with distinct functions

### 3. Existing slide drone context

The modal-drone concept from the slide path can also validate E-Bow sustain. Reuse the same backing asset where the musical role is compatible instead of duplicating nearly identical tracks.

## Song and sound-design use cases

Select legally sourced passages or self-created references that expose:

- sustained melody without pick attack
- harmonic-mode accents
- slow string transitions
- drone beneath changing harmony
- counterline between vocal or guitar phrases
- layered ambient guitar arrangement

For each use case, record:

- section or time range
- normal or harmonic mode
- pickup and gain context
- attack and release strategy
- delay/reverb role
- whether the E-Bow is foreground, counterline, drone, or texture

Song completion remains separate from E-Bow technique mastery.

## Quality gates

| Dimension | Gate |
|---|---|
| Activation | Notes enter within the intended time window without searching audibly for the hot spot. |
| Sustain | Level and pitch remain controlled for the required duration. |
| Attack/release | Onsets and endings match phrase intent and avoid uncontrolled transients. |
| String transitions | Incoming and outgoing strings are controlled; intermediate strings do not dominate. |
| Dynamics | Crescendos, swells, and harmonic blooms are deliberate and remain below clipping. |
| Intonation/vibrato | Pitch remains credible during long sustain and vibrato does not break activation. |
| Noise | Hiss, handling noise, and effect tails remain below the musical part or are identified as gear faults. |
| Arrangement | Each E-Bow layer has a distinct role and leaves space for focal parts. |
| Repeatability | Three isolated passes succeed in two sessions. |
| Musical context | Two uninterrupted recordings demonstrate different roles, such as melody plus drone or counterline. |

## Maintenance

- Active development: every two weeks.
- Stable technique: monthly.
- Before recording: check battery, activation, peak level, noise, and one string transition.

Regression check:

1. Activate one note on each of four strings.
2. Hold one normal-mode and one harmonic-mode note for eight beats.
3. Perform two adjacent and two non-adjacent transitions.
4. Record one eight-bar melody or counterline over a backing track.

Regress only the failed dimension where practical.

## Completion boundary

The documented path is complete when activation, attack/release, both modes, transitions, melody, drones, layering, signal-chain trade-offs, backing contexts, quality gates, and maintenance are defined.

Personal completion still requires a baseline sustained-melody recording and successful musical-context evidence.