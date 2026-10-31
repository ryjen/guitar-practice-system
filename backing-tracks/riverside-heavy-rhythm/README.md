# Riverside heavy rhythm — G / 92 BPM

An **original alternate** to the shorter Riverside video bed, taking
broad rhythm-section inspiration from John Bonham's powerful backbeat,
subtle snare ghosts, kick-foot accents and tom/foot triplets, and from John
Paul Jones's interplay with the drums, melodic bass movement and
unobtrusive chord-tone approaches. This does **not** transcribe, sample
or recreate any specific Led Zeppelin recording or groove.

## Rendering

```bash
guitarctl backing generate
guitarctl midi validate \
  backing-tracks/riverside-heavy-rhythm/manifest.json \
  generated/backing-tracks/riverside-heavy-rhythm-g-92.mid
```

The CLI's deterministic Type-1 MIDI contains **Conductor**, **Drums** and
**Bass** tracks. The manifest remains the source of truth. A two-bar count-in
precedes the seven named, 68-bar video-form sections.

## Drum production

Use a roomy acoustic kit in REAPER or another DAW, or replace the General
MIDI drum SoundFont used for auditioning. Put reverb/room on the kit bus
rather than baking it into the MIDI. The primary snare on beats 2/4 stays
loud; ghost snare notes are intentionally soft. Quiet the hats before
reducing kick/snare weight. The 3-hit `triplet_step` groups are on exact
triplet subdivisions, not straight eighths.

## Bass production

Use a rounded clean electric bass with gentle saturation and dynamic
control; the extra melodic notes are meant to weave around guitar/vocals,
not bury them. Bass accompaniment is intentionally edited bar by bar
via `bass_riffs`, with the standard generator supplying unadorned bars.
Tone, compression, stereo placement and final loudness require DAW audition.

## Qualification

Human audition, chosen reference source/tempo matching, and physical
BOSS RC-3 transfer remain outside repository MIDI-structure tests.
