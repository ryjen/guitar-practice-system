# Backing-Track Presets and Arrangement Form

Backing-track manifests can compose a named drum groove with independent
arrangement-level form controls. The split is deliberate:

```text
BackingTrackSpec
├── sections / harmony
├── arrangement          whole-accompaniment timing/form
└── tracks
    ├── drums
    │   └── GrooveSpec   drum timing, feel, accents, fills
    ├── bass
    └── keys / pads
```

The backing-track layer owns composition of those pieces. Groove rendering remains
focused on drums and the low-level MIDI workflow remains unaware of preset catalogs.

## Referencing a groove preset

A drum track may reference one stable public catalog ID instead of embedding the
full `GrooveSpec`:

```json
{
  "name": "Drums",
  "role": "drums",
  "channel": 9,
  "groove_preset": "alt-rock"
}
```

At generation time the backing-track engine:

1. looks up the preset in `catalogs/grooves/catalog.json`;
2. verifies that the preset meter exactly matches the backing track;
3. expands it to an isolated ordinary `GrooveSpec`;
4. validates the expanded spec through the groove engine; and
5. renders deterministic Type 1 MIDI.

A track may define either `groove` or `groove_preset`, never both. Preset references
are only valid on drum tracks. Unknown IDs and meter mismatches fail closed.

The reference is intentionally small. A caller that needs to alter a preset can
resolve it, modify the resulting `GrooveSpec`, and submit the explicit groove rather
than relying on hidden override semantics.

## Arrangement-wide bar cycles

`GrooveSpec.bar_cycle` affects drums only. Whole-band gaps belong to the backing-track
form instead:

```json
{
  "arrangement": {
    "bar_cycle": {
      "length": 4,
      "mute_bars": [2, 3]
    }
  }
}
```

Cycle indexes are zero-based and start at the first musical bar after count-in. The
example therefore produces:

```text
count-in | band | band | gap | gap | band | band | gap | gap | ...
            0      1      2     3      0      1      2     3
```

During a muted arrangement bar, every accompaniment track is silent: groove-aware
drums, legacy drums, bass, keys, pads, and other rendered roles. Conductor metadata
and section markers remain intact so the file still has deterministic form and DAW
navigation.

This makes full-band gap practice distinct from drum-only gap practice:

| Control | Scope | Typical use |
|---|---|---|
| `groove.bar_cycle` | drums only | remove the rhythmic reference while harmony continues |
| `arrangement.bar_cycle` | all accompaniment | call/response, internal time, deliberate full-band space |

## Canonical generator

Generate the full committed catalog with:

```bash
python3 scripts/generate_backing_tracks.py
```

`generate_backing_tracks.py` routes manifests through `backing_track_engine.py`, which
is the composition boundary for preset resolution and arrangement form. Existing
manifests without these fields keep their prior deterministic behavior.

The lower-level `midi_workflow.py` and `groove_engine.py` remain usable independently
for their narrower contracts.

## Supervisor gateway boundary

A future supervisor gateway only needs declarative authority to choose or construct:

```text
preset ID + tempo + harmony + arrangement form
                     |
                     v
               BackingTrackSpec
                     |
              validate / resolve
                     |
              deterministic MIDI
```

The gateway does not need filesystem, shell, MIDI-device, or DAW authority. The
public engine owns preset lookup, meter compatibility, structural validation, and
rendering behavior.
