# `guitarctl`

`guitarctl` is the preferred command-line surface for repository workflows.

Install the project in editable mode while developing:

```bash
python -m pip install -e .
guitarctl --help
```

## Examples

```bash
guitarctl discover search \
  examples/discovery/slide-backing-track-request.json \
  catalogs/discovery/repository.json

guitarctl schedule propose examples/scheduling/v2-example-snapshot.json

guitarctl assess evaluate \
  examples/assessment/slide-reliable-context.json \
  templates/assessment-gate-set.json

guitarctl progression resolve progression-jazz-major-ii-v-i C
guitarctl progression fourths progression-jazz-major-ii-v-i --count 4
guitarctl progression generate examples/backing-tracks/funk-wah-request.json

guitarctl groove list
guitarctl groove show jazz-swing

guitarctl backing resolve examples/backing-tracks/jazz-blues-12-request.json
guitarctl backing generate

# Render imported Song IR to no-guitar practice MIDI at 75% tempo.
guitarctl backing render imported/song.json --tempo 75% --output practice/song-backing-075.mid

guitarctl midi generate \
  backing-tracks/slide-slow-blues/manifest.json \
  /tmp/slide-slow-blues.mid
guitarctl midi validate \
  backing-tracks/slide-slow-blues/manifest.json \
  /tmp/slide-slow-blues.mid
guitarctl midi generate-exercises

# Import MusicXML directly; Guitar Pro uses MuseScore conversion.
guitarctl score import scores/song.musicxml --output imported/song.json
guitarctl score tracks imported/song.json

# Guitar Pro formats: .gp, .gp3, .gp4, .gp5, .gpx
guitarctl score import scores/song.gp5 --output imported/song.json --musescore mscore

guitarctl validate public-boundary
```

Use an explicit workspace when invoking the installed command outside the repository root:

```bash
guitarctl --workspace /path/to/guitar-practice-system backing resolve \
  examples/backing-tracks/jazz-blues-12-request.json
```

Global options such as `--workspace` appear before the command. Package-native commands expose their own help, for example:

```bash
guitarctl progression generate --help
```

## Migration status

The musical core is package-native: discovery, scheduling v2, assessment, progression catalog operations, groove catalog operations, backing request resolution, backing generation, MIDI generation/validation, starter MIDI exercises, practice-progression generation, imported-score inspection, imported-score symbolic backing rendering, and RC-3 drum export do not require repository scripts at runtime. MusicXML import is direct; Guitar Pro import delegates only the source conversion step to a configured MuseScore executable. Audio rendering is isolated behind an application port with a bounded FluidSynth adapter.

The remaining compatibility-process commands are outside this generation subsystem, including scheduling v1, adaptive-session/evidence workflows, repository validation/export, and artifact-bundle tooling. Historical musical `scripts/*.py` and `tools/*.py` entrypoints remain compatibility shims while callers migrate.

## Score import boundary

`score import` accepts `.gp`, `.gp3`, `.gp4`, `.gp5`, `.gpx`, `.musicxml`, and `.xml` sources inside the explicit workspace. MusicXML is parsed directly. Guitar Pro sources are converted to MusicXML by a bounded MuseScore adapter using argv execution without shell interpolation; canonical Song data contains no MuseScore-specific state. `score tracks` reports stable track ids, inferred roles, and classification provenance. `backing render` consumes that canonical Song document, proportionally derives practice tempo, excludes guitar-role tracks by default, preserves ambiguous tracks, and writes deterministic MIDI plus a JSON provenance sidecar. Explicit `--include-track` and `--exclude-track` flags operate on stable track ids.

## Guitar Pro to RC-3 workflow

The repository flake provides MuseScore, FluidSynth, ffmpeg, and a default FluidR3 SoundFont. After `nix develop`, import once and derive practice artifacts from the canonical Song document:

```bash
guitarctl score import scores/song.gp5 --output imported/song.json
guitarctl score tracks imported/song.json
guitarctl backing render imported/song.json --tempo 75% --output practice/song-backing-75.mid
guitarctl drums export imported/song.json --tempo 75% --target boss-rc3

# Focused practice: 1-based inclusive playback bars
guitarctl backing render imported/song.json --tempo 60% --bars 42:58 --output practice/bars-42-58.mid
guitarctl drums export imported/song.json --tempo 60% --bars 42:58 --target boss-rc3

# Named sections come from explicit MusicXML rehearsal marks
guitarctl backing render imported/song.json --tempo 60% --section "Chorus" --output practice/chorus.mid
guitarctl drums export imported/song.json --tempo 60% --section "Chorus" --target boss-rc3
```

Without `--output`, the RC-3 command writes `generated/rc3/<source-id>-drums-<tempo>pct.wav`, the corresponding source MIDI, and a JSON provenance sidecar. `source-id` is derived from the imported source filename. Outside the flake, provide a SoundFont with `--soundfont PATH` or `GUITAR_SOUNDFONT`. Explicit output names must end in `.wav`.

The RC-3 path is full-song by default over the imported playback span. `--bars START:END` selects a 1-based inclusive structural playback range for both `backing render` and `drums export`; `--section NAME` selects a uniquely named MusicXML rehearsal section. Section lookup is case-insensitive but preserves the source rehearsal text in provenance; duplicate matching names fail as ambiguous and callers should use `--bars` instead. `--bars` and `--section` are mutually exclusive. The selected Song is remapped to position zero before tempo realization, MIDI rendering, and audio rendering. Bar boundaries come from score structure, so pickups, meter changes, and expanded repeats do not depend on silence or note density. Simple MusicXML forward/backward repeats are expanded before Song IR is built, including inherited tempo/meter state at repeat jumps. First/second endings and D.C./D.S./coda navigation currently fail closed rather than being silently ignored. Direct phrase-memory synchronization is intentionally outside this command.

## Musical generation boundaries

MIDI encoding and structural validation are pure package-domain operations over explicit manifests and byte strings. Groove and bass rules consume MIDI primitives without filesystem access. Backing request resolution consumes explicit groove/progression catalogs and returns a canonical `BackingTrackSpec`; generated-backing rendering consumes that spec and returns deterministic MIDI bytes. Imported-score `backing render` is a separate application use case over canonical Song IR, but it reuses the same pure MIDI primitives rather than introducing a second encoder.

`backing render` remains symbolic MIDI. Both score-derived commands may first apply a pure structural bar or rehearsal-section slice. `drums export --target boss-rc3` is a separate application boundary: it selects the requested drum stem, renders through `AudioRenderer`, validates 44.1 kHz / 16-bit linear PCM stereo WAV, and crops or zero-pads to the selected score-derived structural duration rather than detecting silence. It preserves the generated drum MIDI before audio rendering and writes renderer/SoundFont provenance beside the WAV. Practice-progression rules derive slow/medium/fast stages as pure domain data. Starter MIDI exercises are also pure byte generators. Application services own catalog loading, bounded manifest discovery, and artifact persistence through structured-document and binary-artifact ports.

Compatibility entrypoints are parity-tested while callers migrate. CI compares native and historical command JSON/text output as well as generated MIDI directories and byte streams.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.
