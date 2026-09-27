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
guitarctl backing render generated/song.score.json \
  --tempo 75% \
  --output generated/practice/song-backing-75.mid

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

guitarctl score notes song.score.json guitar-1 \
  --input notes.json \
  --output song-with-notes.score.json

guitarctl score voicing song-with-notes.score.json guitar-1 \
  --input voicing.json \
  --output song-with-voicing.score.json

guitarctl score rhythm song-with-voicing.score.json guitar-1 \
  --input rhythm.json \
  --output song-with-rhythm.score.json

guitarctl score technique song-with-rhythm.score.json guitar-1 \
  --input technique.json \
  --output song-with-expression.score.json

guitarctl drums export song.score.json \
  --tempo 75% \
  --target boss-rc3

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

The musical core is package-native: discovery, scheduling v2, assessment, progression catalog operations, groove catalog operations, backing request resolution/generation, Score IR-derived backing rendering, MIDI generation/validation, starter MIDI exercises, practice-progression generation, canonical Score IR creation/import/authoring/inspection/validation, and RC-3 drum export do not require repository scripts at runtime.

The remaining compatibility-process commands are outside this generation subsystem, including scheduling v1, adaptive-session/evidence workflows, repository validation/export, and artifact-bundle tooling. Historical musical `scripts/*.py` and `tools/*.py` entrypoints remain compatibility shims while callers migrate.

## Score documents

`guitarctl score` is the single symbolic-score namespace. The deterministic core commands are:

- `score init --title <title>` — emit the smallest valid Score IR document; add `--output <path>` for an explicit atomic write.
- `score import <source> --output <path>` — import MusicXML or supported Guitar Pro input through the bounded conversion/import adapters.
- `score form <score> "intro:4 verse:12 ..." --output <path>` — replace section/bar structure while the score is still an empty draft; repeated section names receive deterministic numeric suffixes.
- `score chords <score> "C | Dm7 G7 | ..." --output <path>` — replace harmony across the whole score, or add `--section <label>` for one explicit section. Chords inside a bar are spaced evenly using that bar's active meter; an empty bar cell adds no new harmony event.
- `score notes <score> <part-id> --input <notes.json> --output <path>` — replace note events for one explicit part while preserving non-note events. The input document contains only a `notes` array of Score IR note fields; `kind: "note"` and user provenance are supplied when omitted.
- `score voicing <score> <part-id> --input <voicing.json> --output <path>` — apply string/fret positions to existing notes. Each patch selects exactly one note by current location + voice + pitch; missing or ambiguous selectors fail closed, and Score IR validates the resulting position against declared guitar tuning.
- `score rhythm <score> <part-id> --input <rhythm.json> --output <path>` — relocate, resize, or revoice exactly selected untied notes. All selectors resolve against the pre-edit score, duplicate targets fail closed, and the output is re-sorted and fully Score IR-validated.
- `score technique <score> <part-id> --input <technique.json> --output <path>` — patch `articulations`, structured `techniques`, and/or `dynamics` on exactly selected notes without changing pitch, position, or timing. Omitted fields are preserved; empty articulation/technique arrays and `dynamics: null` explicitly clear those optional fields. Duplicate note targets fail closed.
- `score show <score>` — emit the canonical Score IR document.
- `score tracks <score>` — inspect part/role/instrument metadata.
- `score validate <score>` — validate through the canonical Score IR contract and emit a machine-readable report.

All input/output paths are explicit and workspace-relative. Authoring transforms write a new target and leave the source unchanged. There is no implicit current score. `score render`, `score play`, and `score edit` are intentionally not registered until their bounded exporter/playback/editor work lands.

## Musical generation boundaries

MIDI encoding and structural validation are pure package-domain operations over explicit manifests and byte strings. Groove and bass rules consume MIDI primitives without filesystem access. Backing request resolution consumes explicit groove/progression catalogs and returns a canonical `BackingTrackSpec`; backing rendering consumes that spec and returns deterministic MIDI bytes. Score-derived `backing render` instead consumes canonical Score IR through immutable realization and Score IR-to-MIDI domain layers; authoritative guitar parts are excluded by default while inferred guitar roles remain non-destructive.

Practice-progression rules derive slow/medium/fast stages as pure domain data. Starter MIDI exercises are also pure byte generators. Application services own catalog loading, bounded manifest discovery, and artifact persistence through structured-document and binary-artifact ports.

Compatibility entrypoints are parity-tested while callers migrate. CI compares native and historical command JSON/text output as well as generated MIDI directories and byte streams.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.


## Score-derived practice artifacts

Imported or authored Score IR can be realized without mutating canonical state:

```bash
guitarctl backing render generated/song.score.json \
  --tempo 75% \
  --output generated/practice/song-backing-75.mid

guitarctl drums export generated/song.score.json \
  --tempo 75% \
  --target boss-rc3
```

Both commands support explicit part overrides and structural `--bars` / `--section` selection where the form can be sliced safely. See [Guitar Pro to practice backing and BOSS RC-3](workflows/guitar-pro-rc3.md) for the complete workflow and artifact/provenance contracts.


### Note authoring input

`score notes` consumes an explicit JSON object rather than a shell-specific note mini-language:

```json
{
  "notes": [
    {
      "location": {"bar": 1, "beat": [1, 1]},
      "duration": [1, 8],
      "voice": 1,
      "pitch": {"step": "E", "alter": 0, "octave": 4}
    }
  ]
}
```

The source score and input document are read-only; the command writes a new validated Score IR document to the required `--output` path. Existing rests in the selected part are preserved. Later voicing/rhythm/technique commands target existing notes through explicit canonical selectors rather than array indexes.


### Voicing authoring input

Voicing patches do not address notes by array index. Each selector describes the current canonical note identity:

```json
{
  "positions": [
    {
      "selector": {
        "location": {"bar": 1, "beat": [1, 1]},
        "voice": 1,
        "pitch": {"step": "E", "alter": 0, "octave": 4}
      },
      "position": {"string": 2, "fret": 5}
    }
  ]
}
```

A selector must resolve exactly one note in the named part. The source score and voicing input remain unchanged; the required output is independently validated before persistence.


### Rhythm authoring input

Rhythm patches select the current note state and describe only the timing fields that change:

```json
{
  "rhythm": [
    {
      "selector": {
        "location": {"bar": 2, "beat": [1, 1]},
        "voice": 1,
        "pitch": {"step": "G", "alter": 0, "octave": 4}
      },
      "location": {"bar": 2, "beat": [3, 2]},
      "duration": [1, 8]
    }
  ]
}
```

At least one of `location`, `duration`, or `voice` is required. Selectors are resolved before any patch is applied, so moving one note cannot change the identity used by another patch. The first deterministic slice rejects tied note segments; edit or replace the complete tie chain explicitly rather than silently breaking playback semantics.
