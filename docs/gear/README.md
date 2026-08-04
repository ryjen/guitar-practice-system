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

Every component reference uses one of these levels:

| Level | Meaning |
|---|---|
| Required | The setup cannot perform its stated function without this capability. |
| Preferred | Improves repeatability or musical fit but has a practical substitute. |
| Optional | Adds colour, convenience, or a production variant. |
| Avoid during diagnosis | Can conceal the defect currently being evaluated. |

A requirement describes a capability, not a brand. For example, `continuous filter pedal` is a capability; a particular wah model is an inventory item that may satisfy it.

## Inventory

Record owned or reliably available equipment before adding purchase candidates. Unknown values stay explicitly unknown rather than being inferred.

| ID | Category | Item | Capabilities | Constraints / condition | Status |
|---|---|---|---|---|---|
| `guitar-primary` | Guitar | Not yet recorded | pickup configuration unknown | tuning, strings, action, and setup pending | inventory required |
| `amp-primary` | Amp / modeler | Not yet recorded | clean and driven capability unknown | output and monitoring path pending | inventory required |
| `interface-primary` | Interface | Not yet recorded | input count and headroom unknown | DAW/monitoring routing pending | inventory required |
| `wah-primary` | Accessory / pedal | Not yet recorded | continuous filter sweep required for wah path | bypass type, sweep range, noise, and power pending | inventory required |
| `ebow-primary` | Accessory | Not yet recorded | normal/harmonic mode capability pending | battery and activation behaviour pending | inventory required |
| `slide-primary` | Accessory | Not yet recorded | material, length, internal diameter pending | finger fit and weight pending | inventory required |

Do not recommend replacements from this table alone. First record the actual item and an observed limitation against a technique or recording task.

## Inventory record

For each item, capture only useful operational data:

- stable ID and human-readable name
- category and ownership/availability
- capabilities it provides
- physical or software version where behaviour depends on it
- current condition
- known noise, reliability, latency, or compatibility constraints
- maintenance state
- linked setup IDs
- purchase date or price only when useful for warranty, replacement, or budgeting

Avoid copying complete manufacturer specifications that do not affect the practice system.

## Setup record

Use `templates/gear-setup.md` for a concrete setup. A setup should include:

- musical and diagnostic intent
- techniques and use cases supported
- component requirement levels
- ordered signal chain
- gain/headroom checkpoints
- instrument state
- effects that must be bypassed during diagnosis
- minimal, preferred, and recording variants
- troubleshooting observations

## Gain-staging model

Evaluate the chain from source to monitoring:

```text
guitar output
  -> dynamic/filter/gain pedals
  -> amp or amp model
  -> time/modulation effects
  -> interface input
  -> DAW channel/bus
  -> monitor/headphone output
```

At each stage:

1. Establish a representative loudest performance, not only an average note.
2. Leave headroom for resonant peaks, bends, harmonic-mode blooms, and stacked effects.
3. Compare bypassed and engaged level where the effect is not intended as a boost.
4. Diagnose clipping at the earliest stage where it occurs.
5. Record intentional boosts rather than normalizing them away.

Exact numerical targets depend on analog and digital equipment. The invariant is that no unintentional stage clips and the final monitoring level remains safe.

## Noise-management order

Diagnose noise before adding a gate:

1. Guitar controls, pickup selection, and orientation.
2. Cable and connector integrity.
3. Pedal power and grounding.
4. Gain accumulation and high-frequency boosts.
5. Interface input mode and level.
6. USB/computer/monitor ground paths.
7. Plugin or bus gain.
8. Environmental interference.

A noise gate is a last-mile control. It must not truncate E-Bow activation, slide sustain, wah tails, or deliberately quiet dynamics.

## Safety

- Set monitoring level from the loudest expected resonant or feedback condition.
- Treat wah toe peaks, E-Bow harmonic blooms, compressor makeup gain, and high-gain feedback as peak-level cases.
- Lower gain before troubleshooting unexpected feedback.
- Do not perform cable or power changes at unsafe amplifier/output levels.
- Capture hearing-comfort observations in the setup when a configuration produces narrow, aggressive resonances.

## Cross-layer links

Techniques, songs, and backing tracks reference stable setup IDs; they do not duplicate signal-chain details.

```text
technique -> gear setup
song use case -> technique + optional gear setup
backing track -> monitoring/recording setup
gear setup -> inventory items and capabilities
```

A setup may support several techniques. A technique may reference several setups, such as diagnostic, minimal, and recording variants.

## Change policy

Create a new setup version when the musical intent or chain topology changes materially. Small knob adjustments belong in evidence notes unless they reveal a repeatable operating range.

A purchase candidate belongs in the repository only after documenting:

- the current setup
- the observed limitation
- attempted no-cost configuration changes
- required capability
- acceptable substitutes
- expected effect on a technique or production task
