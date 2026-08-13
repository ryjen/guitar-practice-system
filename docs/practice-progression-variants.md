# Practice Progression Variants

A single `BackingTrackRequest` can be expanded into a deterministic three-stage practice progression.

```text
BackingTrackRequest
      |
      v
PracticeProgression: tempo-space-v1
      |
      +-- slow   70% target tempo, full drum reference
      +-- medium 85% target tempo, one drum-gap bar per four
      +-- fast  100% target tempo, two drum-gap bars per four
```

The selected groove preset's minimum supported tempo is a hard floor. For example, a 96 BPM `funk-wah-16` request resolves to 75, 82, and 96 BPM because that preset's minimum is 75 BPM.

## Support reduction

The progression reduces **rhythmic reference**, not harmony. Medium and fast stages add a drum-only `GrooveSpec.bar_cycle` while bass, keys, and pads continue. This makes the player carry more internal time without removing harmonic context.

Whole-band gaps remain independent. If the source request already contains `arrangement.bar_cycle`, it is preserved in every stage.

```text
GrooveSpec.bar_cycle                  drum reference only
Practice progression added gap       drum reference only
BackingTrackSpec.arrangement.bar_cycle all accompaniment
```

If a groove preset already defines a drum bar cycle, the progression composes the two cycles using their least-common-multiple period. The combined cycle is bounded to 64 bars and fails closed if it would exceed that limit.

## Output

`generate_practice_progression.py` returns a `PracticeProgression` object containing the three resolved `BackingTrackSpec` values plus stage metadata.

```bash
python3 scripts/generate_practice_progression.py \
  examples/backing-tracks/funk-wah-request.json
```

To write manifests and render all MIDI files:

```bash
python3 scripts/generate_practice_progression.py \
  examples/backing-tracks/funk-wah-request.json \
  --output-dir /tmp/funk-wah-progression \
  --render-midi
```

The output directory contains `progression.json`, individual manifests under `manifests/`, and MIDI files under `generated/backing-tracks/`.

## Determinism

The `tempo-space-v1` profile is fixed:

| Stage | Tempo | Added drum gap |
|---|---:|---|
| slow | 70% of target, clamped to preset minimum | none |
| medium | 85% of target, clamped to preset minimum | bar 4 of each 4-bar cycle |
| fast | target tempo | bars 3-4 of each 4-bar cycle |

Tempo rounding uses integer arithmetic. Stage IDs, titles, output paths, groove expansion, and gap composition are deterministic.

The progression layer does not choose practice material, assess performance, or decide when a player should advance. It only transforms an already-valid request into reproducible practice variants.
