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

guitarctl score init --title "Blue Thing" > blue-thing.score.json
guitarctl score form blue-thing.score.json \
  "intro:4 verse:12 verse:12 solo:24 outro:4" \
  --output blue-thing-formed.score.json
guitarctl score chords blue-thing-formed.score.json \
  "Em7 | A7 | Dmaj7 | Bm7" \
  --section Intro \
  --output blue-thing-harmony.score.json
guitarctl score validate blue-thing-harmony.score.json
guitarctl score show blue-thing-harmony.score.json
guitarctl score import song.musicxml --output song.score.json
guitarctl score tracks song.score.json

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

The musical core is package-native: discovery, scheduling v2, assessment, progression catalog operations, groove catalog operations, backing request resolution, backing generation, MIDI generation/validation, starter MIDI exercises, practice-progression generation, and canonical Score IR creation/import/authoring/inspection/validation do not require repository scripts at runtime.

The remaining compatibility-process commands are outside this generation subsystem, including scheduling v1, adaptive-session/evidence workflows, repository validation/export, and artifact-bundle tooling. Historical musical `scripts/*.py` and `tools/*.py` entrypoints remain compatibility shims while callers migrate.

## Score documents

`guitarctl score` is the single symbolic-score namespace. The deterministic core commands are:

- `score init --title <title>` — emit the smallest valid Score IR document; add `--output <path>` for an explicit atomic write.
- `score import <source> --output <path>` — import MusicXML or supported Guitar Pro input through the bounded conversion/import adapters.
- `score form <score> "intro:4 verse:12 ..." --output <path>` — replace section/bar structure while the score is still an empty draft; repeated section names receive deterministic numeric suffixes.
- `score chords <score> "C | Dm7 G7 | ..." --output <path>` — replace harmony across the whole score, or add `--section <label>` for one explicit section. Chords inside a bar are spaced evenly using that bar's active meter; an empty bar cell adds no new harmony event.
- `score show <score>` — emit the canonical Score IR document.
- `score tracks <score>` — inspect part/role/instrument metadata.
- `score validate <score>` — validate through the canonical Score IR contract and emit a machine-readable report.

All input/output paths are explicit and workspace-relative. Authoring transforms write a new target and leave the source unchanged. There is no implicit current score. `score render`, `score play`, and `score edit` are intentionally not registered until their bounded exporter/playback/editor work lands.

## Musical generation boundaries

MIDI encoding and structural validation are pure package-domain operations over explicit manifests and byte strings. Groove and bass rules consume MIDI primitives without filesystem access. Backing request resolution consumes explicit groove/progression catalogs and returns a canonical `BackingTrackSpec`; backing rendering consumes that spec and returns deterministic MIDI bytes.

Practice-progression rules derive slow/medium/fast stages as pure domain data. Starter MIDI exercises are also pure byte generators. Application services own catalog loading, bounded manifest discovery, and artifact persistence through structured-document and binary-artifact ports.

Compatibility entrypoints are parity-tested while callers migrate. CI compares native and historical command JSON/text output as well as generated MIDI directories and byte streams.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.
