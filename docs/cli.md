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

guitarctl groove list
guitarctl progression list
guitarctl validate public-boundary
```

Use an explicit workspace when invoking the installed command outside the repository root:

```bash
guitarctl --workspace /path/to/guitar-practice-system schedule propose \
  examples/scheduling/v2-example-snapshot.json
```

Global options such as `--workspace` appear before the command. Package-native commands expose their own help, for example:

```bash
guitarctl discover search --help
```

## Migration status

`discover search` is package-native. Other commands currently pass through one registered compatibility-process adapter so behavior remains stable while their implementation moves into package layers.

Compatibility commands require a workspace containing their registered repository script. They never dispatch arbitrary shell commands. `schedule legacy ...` is explicitly deprecated and exists only for v1 compatibility.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details or compatibility entrypoints and may be reorganized as logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Shells, CI, services, and other external callers should target `guitarctl` rather than individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency and migration rules.
