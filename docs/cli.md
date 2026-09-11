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

guitarctl schedule propose \
  examples/scheduling/v2-example-snapshot.json

guitarctl assess evaluate \
  examples/assessment/slide-reliable-context.json \
  templates/assessment-gate-set.json

guitarctl progression resolve progression-jazz-major-ii-v-i C
guitarctl progression fourths progression-jazz-major-ii-v-i --count 4

guitarctl groove list
guitarctl groove show jazz-swing

guitarctl backing resolve \
  examples/backing-tracks/jazz-blues-12-request.json

guitarctl midi generate \
  backing-tracks/slide-slow-blues/manifest.json \
  /tmp/slide-slow-blues.mid

guitarctl midi validate \
  backing-tracks/slide-slow-blues/manifest.json \
  /tmp/slide-slow-blues.mid

guitarctl validate public-boundary
```

Use an explicit workspace when invoking the installed command outside the repository root:

```bash
guitarctl --workspace /path/to/guitar-practice-system backing resolve \
  examples/backing-tracks/jazz-blues-12-request.json
```

Global options such as `--workspace` appear before the command. Package-native commands expose their own help, for example:

```bash
guitarctl backing resolve --help
```

## Migration status

The following commands are package-native and do not require repository scripts at runtime:

- `discover search`
- `schedule propose`
- `schedule check-approval`
- `assess evaluate`
- `progression validate`
- `progression list`
- `progression show`
- `progression resolve`
- `progression fourths`
- `groove validate`
- `groove list`
- `groove show`
- `backing resolve`
- `midi generate`
- `midi validate`

`progression generate`, bulk `backing generate`, and `midi generate-exercises` remain in the generation subsystem while their application orchestration is extracted behind the same domain/application boundaries.

Former Python entrypoints remain compatibility shims while existing callers migrate. Remaining commands pass through the registered compatibility-process adapter until their cohesive subsystem is extracted.

Compatibility commands require a workspace containing their registered repository script. They never dispatch arbitrary shell commands. `schedule legacy ...` is explicitly deprecated and exists only for v1 compatibility.

## Musical generation boundaries

MIDI encoding and structural validation are pure package-domain operations over explicit manifests and byte strings. Filesystem persistence is handled through the binary-artifact adapter. This separation keeps deterministic rendering reusable from CLI, tests, and other trusted callers without giving the domain filesystem authority.

Groove parsing/rendering and bass accompaniment are package-domain rules. Groove owns deterministic rhythmic realization and catalog validation; bass depends on groove and MIDI primitives for kick-locked and walking patterns.

Backing request resolution and arrangement rendering are also package-domain operations. Request resolution consumes explicit groove and progression catalogs and returns a canonical `BackingTrackSpec`. Arrangement rendering consumes that spec plus the groove catalog and returns deterministic MIDI bytes. Catalog/file loading remains application-side.

Compatibility entrypoints are parity-tested while callers migrate. MIDI output must remain byte-identical, groove catalog output must remain text-identical, and backing request resolution must produce the same JSON through the historical script and native `guitarctl` command.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.
