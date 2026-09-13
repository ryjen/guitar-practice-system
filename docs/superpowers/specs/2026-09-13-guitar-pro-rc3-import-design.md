# Guitar Pro to RC-3 Practice Pipeline Design

**Issue:** #108

## Goal

Import Guitar Pro scores into a stable internal song representation, inspect and classify tracks, derive slowed no-guitar backing and drum-only symbolic stems, render audio through an explicit adapter boundary, and export a BOSS RC-3-compatible WAV. Full-song drums are the default; exact section/bar exports are secondary.

## Design principles

- `guitarctl` is the stable user interface.
- Guitar Pro and BOSS-specific details stay outside the canonical musical domain.
- Symbolic transforms happen before audio rendering; do not time-stretch rendered WAV when score/MIDI data is available.
- Imported metadata is untrusted input for paths, logs, and subprocess arguments.
- Heuristic role classification is non-destructive: ambiguous tracks remain included unless the user explicitly excludes them.
- Preserve source, classification, tempo-transform, renderer, and hardware-profile provenance.
- The RC-3 is the only initial hardware target, but the domain must not assume a single-track looper.

## Architecture

```text
Guitar Pro (.gp/.gp3/.gp4/.gp5/.gpx)
        |
        v
ScoreImporter port
        |
        +-- MuseScore conversion adapter -> MusicXML
        |
        v
Canonical Song IR
  - tracks / stable ids
  - role + classification provenance
  - notes/events sufficient for symbolic stems
  - tempo map
  - meter map
  - bars / sections / markers where available
        |
        +-- tempo-map transform
        +-- stem selector
             |-- backing (exclude guitar)
             `-- drums
                     |
                     v
              MIDI/symbolic artifacts
                     |
                     v
               AudioRenderer port
                     |
                     v
                  WAV audio
                     |
                     v
          HardwareExportProfile
                     |
                     v
                boss-rc3
```

## Canonical Song IR

The minimum IR for #108 is intentionally smaller than the full transcription model proposed by #95, but compatible with it.

Required records:

- `Song`: stable source identity, title, tracks, tempo map, meter map, optional sections/markers.
- `SongTrack`: deterministic track id, source name, role, classification provenance, instrument/program/percussion metadata, and symbolic events.
- `TrackRole`: `guitar`, `bass`, `drums`, `keys`, `other`, `unknown`.
- `Classification`: role, source (`explicit`, `instrument`, `midi`, `percussion`, `name-heuristic`, `unknown`), and confidence/category sufficient to distinguish source facts from guesses.
- `TempoPoint`: musical position plus BPM; practice transforms create a derived map and never mutate canonical tempo.
- `MeterPoint`: musical position plus numerator/denominator.

The IR must contain no filesystem paths to MuseScore/BOSS devices and no renderer subprocess state.

## Import boundary

`ScoreImporter` is an application port. The initial Guitar Pro path uses a bounded MuseScore adapter to convert supported Guitar Pro formats to MusicXML, then parses MusicXML into the Song IR.

The converter adapter:

- invokes a configured known executable with an argv array, never a shell command;
- writes only inside a bounded workspace/temp area;
- reports converter identity/version in provenance;
- treats score titles and track names as data, never path fragments;
- distinguishes conversion failure from MusicXML parse/validation failure;
- reports unsupported/lossy source features when detectable.

Tests must not require MuseScore to be installed: domain/parser tests use MusicXML fixtures and adapter command tests use a fake process runner. A bounded optional integration test may exercise MuseScore when available.

## Track-role classification

Classification precedence:

1. explicit user override;
2. source/importer instrument identity;
3. MIDI program/channel metadata;
4. percussion staff/channel semantics;
5. normalized track-name heuristic;
6. `unknown`.

A heuristic may suggest `guitar`, `bass`, `drums`, or `keys`, but uncertain/unknown tracks are included in backing output by default. `guitarctl score tracks` exposes role and provenance so the user can override misclassification by stable track id.

## Tempo transforms

Practice tempo is derived symbolic state:

- percentage tempo scales every tempo point proportionally;
- absolute BPM is accepted only for a single-tempo song;
- negative/relative forms may be added only with unambiguous semantics;
- the canonical imported tempo map is immutable;
- meter and event positions do not change when applying tempo scaling.

## Stem selection

Stem selection is pure domain behavior over Song IR:

- backing default: include all tracks except confidently classified/explicitly marked `guitar`;
- drums default: include only `drums`;
- explicit track-id include/exclude overrides are deterministic;
- ambiguous heuristic tracks are not silently removed.

The result is a symbolic stem request/artifact that can be serialized to MIDI without audio/filesystem authority in the domain layer.

## Audio rendering boundary

`AudioRenderer` is an application port consuming symbolic/MIDI bytes plus an explicit render profile and returning WAV bytes/artifact metadata.

The initial local adapter may use a SoundFont-capable renderer. It must record renderer identity/version and soundfont/instrument-set identity, invoke a known executable with argv (no shell interpolation), and preserve the source MIDI if rendering fails.

## BOSS RC-3 profile

`boss-rc3` validates/adapts already-rendered audio. Initial contract:

- WAV container;
- 44.1 kHz;
- 16-bit linear PCM;
- stereo;
- deterministic safe filename;
- exact intended full-song or selected bar/section duration;
- no silence-based trimming to determine loop boundaries.

Direct mutation/synchronization of RC-3 phrase-memory storage is not part of the first implementation. If added later, occupied memories may never be overwritten without explicit approval.

## Full-song and focused practice behavior

`guitarctl drums export SONG --target boss-rc3 --tempo 75%` exports the full song by default, preserving fills and arrangement.

Explicit `--section` or `--bars` exports use structural boundaries from the Song IR. Section artifacts may be generated opportunistically only when reliable source markers exist.

## CLI direction

```bash
guitarctl score import song.gp
guitarctl score tracks song

guitarctl backing render song --exclude guitar --tempo 75%
guitarctl drums export song --tempo 75% --target boss-rc3
```

Focused practice remains additive:

```bash
guitarctl practice render song --section chorus --tempo 70%
guitarctl practice render song --bars 42:58 --tempo 60%
```

## Error and security model

- reject unsupported input extensions and malformed MusicXML;
- distinguish source conversion, parse, classification, symbolic rendering, audio rendering, and hardware-profile errors;
- reject invalid tempo specifications;
- sanitize generated filenames independently from display metadata;
- prevent path traversal from score/track names;
- never execute source metadata as shell text;
- preserve original source and deterministic imported representation for replay/debugging;
- validate MIDI/audio artifacts before presenting them as usable.

## Delivery slices

1. **Import foundation:** minimum Song IR, role classification, MusicXML parser, Guitar Pro/MuseScore adapter boundary, `score import` / `score tracks` inspection.
2. **Symbolic practice stems:** tempo-map transforms, deterministic stem selection, no-guitar backing MIDI and drum-only MIDI.
3. **Audio rendering:** `AudioRenderer` port and one bounded local adapter with explicit renderer/soundfont provenance.
4. **RC-3 export:** WAV validation/adaptation profile, full-song default, exact section/bar export, end-to-end docs.

Each slice is independently reviewed and must keep repository-wide validation green before the next slice begins.

## Acceptance criteria

- Guitar Pro input enters the system only through an importer adapter boundary.
- Imported tracks expose stable ids, roles, and classification provenance.
- Ambiguous classifications remain non-destructive until explicitly overridden.
- Multi-tempo maps scale proportionally without mutating canonical source tempo.
- No-guitar backing and drum-only stems are symbolic/deterministic before audio rendering.
- Audio rendering is isolated behind an application port.
- RC-3 export validates 44.1 kHz / 16-bit PCM stereo WAV.
- Full-song drum export is the default; section/bar boundaries are structural, not silence-derived.
- RC-3 behavior remains isolated so future multitrack loopers can be added as new export profiles without changing Song IR.
- One documented end-to-end Guitar Pro -> slowed backing -> RC-3 workflow is verified.