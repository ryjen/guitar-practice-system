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

The musical core is package-native: discovery, scheduling v2, assessment, progression catalog operations, groove catalog operations, backing request resolution, backing generation, MIDI generation/validation, starter MIDI exercises, practice-progression generation, and imported-score inspection do not require repository scripts at runtime. MusicXML import is direct; Guitar Pro import delegates only the source conversion step to a configured MuseScore executable.

The remaining compatibility-process commands are outside this generation subsystem, including scheduling v1, adaptive-session/evidence workflows, repository validation/export, and artifact-bundle tooling. Historical musical `scripts/*.py` and `tools/*.py` entrypoints remain compatibility shims while callers migrate.

## Score import boundary

`score import` accepts `.gp`, `.gp3`, `.gp4`, `.gp5`, `.gpx`, `.musicxml`, and `.xml` sources inside the explicit workspace. MusicXML is parsed directly. Guitar Pro sources are converted to MusicXML by a bounded MuseScore adapter using argv execution without shell interpolation; canonical Song data contains no MuseScore-specific state. `score tracks` reports stable track ids, inferred roles, and classification provenance so later backing/stem commands can remain non-destructive around ambiguous tracks.

## Musical generation boundaries

MIDI encoding and structural validation are pure package-domain operations over explicit manifests and byte strings. Groove and bass rules consume MIDI primitives without filesystem access. Backing request resolution consumes explicit groove/progression catalogs and returns a canonical `BackingTrackSpec`; backing rendering consumes that spec and returns deterministic MIDI bytes.

Practice-progression rules derive slow/medium/fast stages as pure domain data. Starter MIDI exercises are also pure byte generators. Application services own catalog loading, bounded manifest discovery, and artifact persistence through structured-document and binary-artifact ports.

Compatibility entrypoints are parity-tested while callers migrate. CI compares native and historical command JSON/text output as well as generated MIDI directories and byte streams.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.
