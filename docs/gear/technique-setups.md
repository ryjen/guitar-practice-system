# Technique-Specific Gear Setups

These are capability-based starting points. Replace inventory placeholders with actual owned equipment before treating exact settings as repeatable presets.

## `slide-diagnostic`

**Intent:** Expose pitch, fret contact, muting, attack, and release problems.

**Supports:** Slide phases 1–4 and baseline recording.

| Role | Capability | Requirement |
|---|---|---|
| Guitar | Stable tuning and usable action | required |
| Slide | Secure fit without squeezing | required |
| Gain | Clean or edge-of-breakup | preferred |
| Time effects | Bypassed or minimal | avoid during diagnosis |
| Tuner/reference | Stable pitch reference | required |

```text
guitar -> tuner/reference check -> clean amp/model -> interface/monitoring
```

Key parameters:

- Use the existing guitar setup first.
- Increase action or string gauge only after fret contact is demonstrated as a persistent limitation.
- Keep delay and reverb low enough that attacks, releases, and sympathetic strings remain audible.
- Use a pickup position that exposes articulation; do not select solely for sustain.
- Set gain from the loudest slide attack and vibrato peak.

Variants:

- **Minimal:** guitar, slide, clean amp.
- **Preferred:** tuner, clean/edge tone, simple recording path.
- **Recording:** subtle compression and ambience after a dry control take passes.

## `slide-musical`

**Intent:** Support sustained melody and blues/roots-rock phrasing without masking intonation.

```text
guitar -> optional light compression -> edge-of-breakup gain -> short delay/reverb -> interface/amp
```

- Compression is optional and light.
- Delay repeats must not turn string-transition noise into a rhythmic layer.
- Reverb supports sustain but should preserve pitch centre.
- Open-tuning variants record the tuning and string-tension implications explicitly.

## `wah-diagnostic`

**Intent:** Compare parked positions, rhythmic movement, bypass level, and resonant peaks.

| Role | Capability | Requirement |
|---|---|---|
| Wah | Continuous heel-to-toe sweep | required |
| Gain | Clean or mild drive | required |
| Meter/recording | Detect clipping and level jumps | preferred |
| Delay/reverb | Minimal | avoid during diagnosis |

Default chain:

```text
guitar -> wah -> gain -> amp/model -> interface/monitoring
```

Checks:

1. Compare bypass, heel, midpoint, and toe at performance attack level.
2. Record whether the wah is before or after gain.
3. Reduce upstream gain if toe-down peaks clip or become painfully narrow.
4. Confirm pedal power and cable noise before changing technique.
5. Match engaged/bypassed level unless a boost is intentional.

Variants:

- **Before gain:** default, touch-responsive, more pronounced sweep.
- **After gain:** deliberate filter/sound-design option.
- **Rhythm:** clean tone, controlled compression after timing is audible.
- **Lead:** mild or driven gain with peak-level check.

## `ebow-diagnostic`

**Intent:** Expose activation time, attack/release, bloom, string transitions, and noise.

```text
guitar -> clean amp/model -> interface/monitoring
```

| Role | Capability | Requirement |
|---|---|---|
| Guitar | Stable pickup output and tuning | required |
| E-Bow | Reliable battery and operating mode | required |
| Compression | Bypassed for baseline | avoid during diagnosis |
| Gate | Bypassed | avoid during diagnosis |
| Delay/reverb | Bypassed or minimal | avoid during diagnosis |

Checks:

- Start with the pickup that activates most reliably, often the neck position, then document the actual result.
- Set level from the loudest harmonic-mode bloom.
- Verify battery state before interpreting inconsistent activation as technique failure.
- A gate must not cut the activation ramp or release tail.
- Compare dry control with any compressor, gain, delay, or reverb added later.

## `ebow-layered-recording`

**Intent:** Record distinct drone, melody, counterline, and harmonic-accent layers.

```text
guitar -> optional light compression/gain -> modulation (optional) -> delay/reverb -> interface -> DAW
```

- Separate layers by role, register, timing, and effects rather than adding volume.
- Keep a dry or lightly processed source when practical.
- Check cumulative low-mid and upper-mid masking.
- Mute-test every layer before retaining it.
- Avoid a shared gate that truncates quiet entries across several layers.

## `country-clean-diagnostic`

**Intent:** Expose hybrid-picking balance, string separation, muting, alternating bass, and bend intonation.

```text
guitar -> clean amp/model -> interface/monitoring
```

| Role | Capability | Requirement |
|---|---|---|
| Guitar | Clear pickup response | required |
| Pick/fingers | Comfortable hybrid-picking access | required |
| Compressor | Bypassed or very light | avoid masking dynamics |
| Ambience | Bypassed or short room | optional |

- Bridge or combined pickup positions are common starting points, not requirements.
- Do not use treble boost to substitute for a clean attack.
- Compression may improve consistency but can exaggerate pick/finger noise and flatten accents.
- Set level from snapped dyads and pedal-steel bends, not only normal picking.

## `country-clean-musical`

**Intent:** Support country-rock rhythm, fills, double-stops, and pedal-steel bends.

```text
guitar -> optional light compressor -> clean/edge amp -> optional slapback/room -> interface/amp
```

- Short ambience must leave rhythmic gaps audible.
- Compression supports sustain and balance only after the dry gate passes.
- Record pickup selection and tone-control intent rather than assuming a Telecaster-style configuration.

## `hard-rock-rhythm`

**Intent:** Produce tight palm-muted rhythm and defined chord attacks without excess saturation.

```text
guitar -> optional gate/boost -> driven amp/model -> cabinet/IR -> interface/monitoring
```

| Role | Capability | Requirement |
|---|---|---|
| Guitar | Stable tuning and suitable pickup output | required |
| Gain stage | Controlled distortion | required |
| Gate | Fast enough not to truncate intended sustain | optional |
| Boost/EQ | Tighten low end or level | optional |

Checks:

- Reduce gain until chord detail and muting differences remain audible.
- Diagnose low-frequency blur before adding more gate or treble.
- Match cabinet/IR level and avoid clipping after the amp model.
- Test noise with hands muting the strings to separate playing noise from system noise.
- Record tuning and string tension when they affect attack or pitch stability.

## `backing-track-monitoring`

**Intent:** Hear backing tracks and guitar clearly while recording without printing accidental monitor effects.

```text
DAW backing buses -> monitor mix
instrument -> interface input -> armed DAW track -> monitor mix
```

- Document direct versus software monitoring.
- Keep input latency low enough for the technique under test.
- Separate monitoring effects from printed effects when practical.
- Leave headroom on the backing bus and master for the live guitar.
- Check mono compatibility when practice depends on hearing rhythmic placement rather than stereo width.
- Store interface channel, input mode, sample rate, buffer, and monitor path only when they materially affect repeatability.

## Troubleshooting matrix

| Symptom | Likely layer | First checks |
|---|---|---|
| Slide notes rattle against frets | instrument/setup or pressure | pressure, slide fit, action, string gauge |
| Wah toe position clips | gain staging | upstream gain, pedal placement, interface peak |
| Wah adds hiss when stationary | pedal/power/gain | power, cable, gain accumulation, pot condition |
| E-Bow activation is inconsistent | battery/position/pickup/gain | battery, hot spot, pickup, gain |
| E-Bow tails disappear | gate/compressor/monitoring | gate release, threshold, plugin chain |
| Country snap is painfully bright | technique/EQ/compression | attack force, pickup, treble, compressor |
| Hard-rock rhythm is undefined | excess gain/low end/muting | reduce gain, tighten bass, inspect muting |
| DAW timing feels late | monitoring latency | direct monitoring, buffer, plugin latency |

## Completion boundary

The gear-layer documentation is structurally complete when:

- inventory and requirement-level models exist
- actual owned gear can be recorded without changing the schema
- slide, wah, E-Bow, country clean, hard-rock rhythm, and backing-track monitoring setups exist
- gain, noise, safety, and troubleshooting rules are defined
- cross-layer references use stable setup IDs

Issue-level completion still requires replacing inventory placeholders with the current real gear. New purchases must not be recommended before that inventory pass.
