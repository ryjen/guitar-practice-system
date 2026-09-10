# `guitarctl`

`guitarctl` is the preferred command-line surface for repository workflows.

Install the project in editable mode while developing:

```bash
python -m pip install -e .
guitarctl --help
```

During migration, commands delegate to the existing implementation scripts so behavior stays compatible:

```bash
guitarctl discover search \
  examples/discovery/slide-backing-track-request.json \
  catalogs/discovery/repository.json

guitarctl schedule propose \
  examples/scheduling/v2-example-snapshot.json

guitarctl backing generate -- --help
guitarctl midi workflow -- --help
guitarctl midi generate -- --help
guitarctl export -- --help
```

`--` may be used before legacy arguments when an underlying script has option names that would otherwise be ambiguous during migration.

## Stability

`guitarctl` is the stable interface. `scripts/*.py` and `tools/*.py` are implementation details/compatibility entrypoints and may be reorganized as their logic moves into `guitar_practice.domain`, `guitar_practice.application`, and adapters.

Automation should target `guitarctl`, not individual Python files.

See [`architecture/cli-architecture.md`](architecture/cli-architecture.md) for dependency rules and the AI proposal boundary.
