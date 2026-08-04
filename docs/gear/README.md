# Gear Layer

## Purpose

The gear layer records what is available, how it is connected, and which repeatable setups support a technique, song use case, backing track, or recording task. It must not make technique progress depend on buying a specific product.

The repository stores intent, capabilities, constraints, and sensitive parameters. Exact knob positions are supporting evidence, not the model itself, because rooms, instruments, interfaces, monitoring levels, firmware, and plugins change the result.

## Boundaries

Gear owns:

- physical instruments and setup state
- pickups, strings, action, tuning, and maintenance notes
- pedals, accessories, amplifiers, plugins, interfaces, and monitoring
- signal-chain order and routing
- reusable presets and technique-specific setups
- gain staging, noise diagnosis, feedback risk, and hearing-level checks

Gear does not own:

- technique progression or quality gates
- song completion state
- backing-track arrangement or MIDI source
- purchasing recommendations before the current inventory and actual limitation are documented

## Requirement levels

| Level | Meaning |
|---|---|
| Required | The setup cannot perform its stated function without this capability. |
| Preferred | Improves repeatability or musical fit but has a practical substitute. |
| Optional | Adds colour, convenience, or a production variant. |
| Avoid during diagnosis | Can conceal the defect currently being evaluated. |

Requirements describe capabilities rather than brands.

## Current inventory

Unknown model details remain explicitly unconfirmed rather than inferred.

### Guitars and bass

| ID | Instrument | Configuration | Strings / setup notes | Primary uses |
|---|---|---|---|---|
| `guitar-prs-se-custom-blue` | Blue PRS SE Custom | Dual-coil humbuckers with Les Paul-like and Strat-like switching/voicing | Usually D'Addario or Ernie Ball .010 set | Main versatile electric; rock, slide, wah, E-Bow |
| `guitar-gretsch-hollowbody` | Gretsch hollow-body, exact model unconfirmed (`A55` or similar) | Stock pickups | Flatwound strings | Clean, roots, E-Bow, ambient and country-adjacent textures |
| `guitar-fender-strat-white` | White Fender Stratocaster | Custom Tex-Mex pickups | Usually D'Addario or Ernie Ball .010 set | Country clean, wah, slide, clean and edge-of-breakup work |
| `guitar-kramer-striker` | Kramer Striker | Quad-core pickup configuration; Floyd Rose tremolo | Usually D'Addario or Ernie Ball .010 set | Hard-rock rhythm and lead, tremolo use |
| `guitar-takamine-nylon` | Takamine electric-acoustic classical | Acoustic-electric | Nylon strings | Classical, fingerstyle, and nylon acoustic layers |
| `guitar-fender-acoustic-steel` | Fender acoustic-electric, exact model unconfirmed | Acoustic-electric | Steel strings | Acoustic rhythm, songwriting, and backing-track layers |
| `bass-squier` | Fender Squier bass | Exact model and pickup configuration unconfirmed | String type/gauge unconfirmed | Bass parts and backing-track production |

### Amplification

| ID | Item | Role | Notes |
|---|---|---|---|
| `amp-fender-deluxe-reverb` | Fender Deluxe Reverb | Main guitar amplifier | Primary clean and edge-of-breakup platform |
| `amp-fender-bassman` | Fender Bassman, exact model unconfirmed | Bass amplifier | Primary bass amplification |
| `amp-fender-practice-25` | Smaller Fender 25-watt practice amp, exact model unconfirmed | Low-volume practice | Portable/quiet practice option |

### Pedals and accessories

The pedals were supplied in amp-to-guitar order. The resulting normal guitar-to-amp chain is:

```text
guitar
  -> Boss compressor
  -> Vox wah
  -> Boss noise suppressor
  -> Boss Blues Driver
  -> Boss chorus
  -> Boss digital delay
  -> Boss looper
  -> amplifier
```

This records the current physical order, not a universal recommendation. Technique-specific setups may bypass pedals or test alternate placement deliberately.

| ID | Item | Capabilities / notes |
|---|---|---|
| `pedal-boss-compressor` | Boss compressor | Dynamic control; use lightly after dry diagnostics |
| `pedal-vox-wah` | Vox wah | Continuous filter control for wah path |
| `pedal-boss-noise-suppressor` | Boss noise suppressor | Current placement after wah and before drive; bypass during sustain diagnostics |
| `pedal-boss-blues-driver` | Boss Blues Driver | Edge-of-breakup and driven gain |
| `pedal-boss-chorus` | Boss chorus, exact model unconfirmed | Modulation and layered textures |
| `pedal-boss-digital-delay` | Boss digital delay, exact model unconfirmed | Delay and spatial support |
| `pedal-boss-looper` | Boss compact looper, exact model unconfirmed | End-of-chain practice loops and layered parts |
| `accessory-ebow-1990s` | Standard 1990s E-Bow | Normal/harmonic sustain modes; check battery before recording |
| `slide-brass` | Brass slide | Heavier attack and sustain |
| `slide-glass` | Glass slide | Smoother/lighter response |
| `slide-ring` | Small ring slide | Mixed fretting/slide use |
| `pick-dunlop-teardrop-060` | Dunlop teardrop 0.60 mm picks | Primary flatpick |

### Recording and monitoring

| ID | Item | Notes |
|---|---|---|
| `interface-focusrite` | Focusrite mid-range preamp/audio interface, exact model unconfirmed | Primary instrument/microphone input and DAW interface |
| `mic-live` | Live microphone, exact model unconfirmed | Amp/acoustic capture and audio-to-MIDI experiments where supported |
| `daw-garageband` | GarageBand | Fast arrangement and MIDI workflow |
| `daw-reaper` | REAPER | Flexible recording, editing, routing, and backing-track workflow |
| `monitor-studio` | Studio monitors, exact model unconfirmed | Main speaker monitoring |
| `headphones-shure` | Shure headphones, exact model unconfirmed | Headphone monitoring |

## Setup record

Use `templates/gear-setup.md` for a concrete setup. A setup includes:

- musical and diagnostic intent
- techniques and use cases supported
- component requirement levels
- ordered signal chain
- gain/headroom checkpoints
- instrument state
- effects bypassed during diagnosis
- minimal, preferred, and recording variants
- troubleshooting observations

## Gain-staging model

Evaluate the chain from source to monitoring:

```text
guitar output
  -> compressor / wah / noise control / gain
  -> modulation / delay / looper
  -> amp or interface
  -> DAW channel/bus
  -> monitor/headphone output
```

At each stage:

1. Establish a representative loudest performance, not only an average note.
2. Leave headroom for wah peaks, bends, E-Bow harmonic blooms, and stacked effects.
3. Compare bypassed and engaged level where the effect is not intended as a boost.
4. Diagnose clipping at the earliest stage where it occurs.
5. Record intentional boosts rather than normalizing them away.

## Noise-management order

Diagnose noise before increasing suppression:

1. Guitar controls, pickup selection, and orientation.
2. Cable and connector integrity.
3. Pedal power and grounding.
4. Compressor, wah, and gain accumulation.
5. Noise-suppressor threshold and release.
6. Amplifier or interface input level.
7. USB/computer/monitor ground paths.
8. Plugin or bus gain.
9. Environmental interference.

The noise suppressor must not truncate E-Bow activation, slide sustain, wah tails, or quiet dynamics.

## Safety

- Set monitoring level from the loudest expected resonant or feedback condition.
- Treat wah toe peaks, E-Bow harmonic blooms, compressor makeup gain, and high-gain feedback as peak cases.
- Lower gain before troubleshooting unexpected feedback.
- Do not perform cable or power changes at unsafe amplifier/output levels.
- Record hearing-comfort concerns when a setup produces narrow, aggressive resonances.

## Cross-layer links

```text
technique -> gear setup
song use case -> technique + optional gear setup
backing track -> monitoring/recording setup
gear setup -> inventory items and capabilities
```

A setup may support several techniques. A technique may reference diagnostic, minimal, musical, and recording variants.

## Change and purchase policy

Create a new setup version when musical intent or chain topology changes materially. Small knob adjustments belong in evidence notes unless they reveal a repeatable operating range.

A purchase candidate belongs in the repository only after documenting:

- the current setup
- the observed limitation
- attempted no-cost configuration changes
- required capability
- acceptable substitutes
- expected effect on a technique or production task
