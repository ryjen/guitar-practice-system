# Groove Engine and MIDI Backing Tracks

The backing-track manifests are the public `BackingTrackSpec`: they describe tempo,
meter, harmony, sections, track roles, provenance, and output paths. Drum tracks may
also provide an explicit `groove` object. The groove engine validates that object and
renders deterministic General MIDI drum events before the existing Type 1 MIDI
workflow writes the final artifact.

## Design goals

- **Beat first:** timing, subdivision, accents, and pocket are explicit rather than
  hidden inside an opaque generation step.
- **Deterministic:** the same manifest and seed produce the same MIDI.
- **Editable:** output remains ordinary Type 1 MIDI for import into a DAW.
- **Backward compatible:** manifests without `groove` continue to use the legacy
  deterministic drum renderer.
- **Bounded integration:** an external planner or supervisor gateway can propose a
  manifest or groove object, but this repository owns validation and rendering.

## GrooveSpec

A groove is attached to a drum track:

```json
{
  "name": "Drums",
  "role": "drums",
  "channel": 9,
  "groove": {
    "subdivision": 16,
    "swing": 0.0,
    "humanize_ms": 5,
    "velocity_variance": 4,
    "seed": 112,
    "count_in": "click",
    "instruments": {
      "kick": {
        "steps": [0, 6, 8, 14],
        "velocity": 104,
        "accent_steps": [0],
        "accent_velocity": 112
      },
      "snare": {
        "steps": [4, 12],
        "velocity": 108
      },
      "closed_hat": {
        "steps": [0, 2, 4, 6, 8, 10, 12, 14],
        "velocity": 72
      },
      "open_hat": {
        "steps": [],
        "velocity": 78,
        "variation": {
          "every_bars": 4,
          "steps": [14]
        }
      }
    }
  }
}
```

For 4/4 at sixteenth-note subdivision there are 16 steps per bar. Other supported
meters derive their step count from the meter and subdivision, so 7/8 at sixteenth
subdivision has 14 steps.

### Timing controls

| Field | Meaning |
|---|---|
| `subdivision` | Grid resolution: quarter, eighth, sixteenth, or thirty-second notes |
| `swing` | Delay applied to odd grid steps, from `0.0` straight to `0.5` maximum |
| `humanize_ms` | Seeded timing jitter, capped at 30 ms |
| `velocity_variance` | Seeded velocity jitter, capped at 24 MIDI velocity units |
| `seed` | Reproducibility seed |
| `count_in` | `click`, `groove`, or `none` |

Humanization is intentionally bounded. It should add feel without turning timing
practice into an unstable target.

### Bar variation

Each instrument may replace its normal steps at a fixed interval:

```json
{
  "steps": [],
  "velocity": 108,
  "variation": {
    "every_bars": 8,
    "steps": [0]
  }
}
```

This is sufficient for controlled open-hat changes, crashes, and short tom fills
without requiring a separate arrangement language.

## Generate the catalog

From the repository root:

```bash
python3 scripts/generate_backing_tracks.py
```

The generator:

1. discovers every `backing-tracks/*/manifest.json`;
2. validates the backing-track and groove contracts;
3. renders groove-aware drums where requested;
4. delegates remaining tracks to the existing deterministic MIDI workflow;
5. validates the generated Type 1 MIDI; and
6. writes artifacts under `generated/backing-tracks/`.

Generated MIDI remains a build artifact rather than committed source.

## Reproducible CI artifact bundle

CI packages the generated MIDI with the ordinary public source metadata required to
inspect and reproduce it. Reproduce the same bundle locally from a clean checkout:

```bash
python3 scripts/build_practice_artifacts.py \
  --source-sha "$(git rev-parse HEAD)" \
  --output-dir generated/practice-artifacts
```

The bundle contains:

- generated Type 1 MIDI under `generated/backing-tracks/`;
- backing-track manifests and groove catalog data;
- public backing-track/groove contracts;
- a freshly validated practice-cockpit export;
- `provenance.json` with the source SHA, Python runtime, generator-source hashes, and
  SHA-256 hashes for the payload; and
- `SHA256SUMS` covering the payload and provenance manifest.

The bundle deliberately excludes wall-clock timestamps from deterministic content.
CI builds the bundle twice from the same revision and requires byte-for-byte equality
before uploading it as a workflow artifact. Uploaded CI bundles are retained for 14
days; tagged long-lived distribution belongs to the separate release workflow.

## External supervisor boundary

The integration point is declarative data, not execution authority:

```text
practice intent
    |
external planner / supervisor
    |
BackingTrackSpec + GrooveSpec
    |
schema + domain validation
    |
deterministic groove renderer
    |
Type 1 MIDI
```

A future supervisor gateway therefore only needs to produce a candidate spec. It does
not need filesystem, shell, DAW, or MIDI-device authority. The public engine rejects
invalid meters, unsupported instruments, invalid steps, excessive humanization, and
out-of-range MIDI values before an artifact is emitted.

Planning implementations, personalization, assessment-driven adaptation, and remote
gateway policy remain outside this public repository.
