# Repository validation

The repository has one canonical package-native fast validation command for source changes:

```bash
guitarctl validate repo
```

Install the pinned development dependency before the first run:

```bash
python -m pip install -r requirements-dev.txt
```

## Reproducible Nix validation

The same package-native fast gate is also a first-class flake check. On a system with Nix installed:

```bash
# Narrow, repeatable fast repository gate:
nix build --no-write-lock-file --no-link --print-build-logs \
  .#checks.x86_64-linux.repository-validation

# Full flake validation, including the existing toolchain smoke check:
nix flake check --no-write-lock-file --print-build-logs
```

The check runs the existing `guitarctl validate repo` implementation from a writable copy of the pinned flake source. It uses the flake-defined Python 3.12/Ruff environment and exports only a JSON validation report into its Nix output. It does **not** add a second Python test runner or replace the separate domain- and tool-integration checks.

During the additive qualification phase, the existing MusicXML CI workflow also invokes this flake check using its already-pinned Nix bootstrap. The existing `Validate Repository` and domain CI check identities, filters, trust boundaries and GitHub-hosted runner assignments are unchanged. This is not yet workflow consolidation or evidence of lower CI cost; those changes require the separate mapping and comparison recorded in #165.

The canonical command runs, in order:

1. Python bytecode compilation for `scripts/`, `tests/`, and `tools/`;
2. correctness-focused Ruff static analysis across those Python source directories;
3. the public repository boundary check;
4. the full unit-test suite.

Ruff is intentionally configured narrowly in `pyproject.toml`. The initial gate checks Pyflakes diagnostics and `E9` parser/runtime-syntax failures rather than introducing formatting or style-only churn.

Domain workflows continue to own their heavier acceptance checks. For example, MIDI validation still renders the backing-track catalog and verifies deterministic practice-bundle replay. The canonical validation command is the common fast trust gate, not a replacement for those domain checks.

## CI expectations

Repository-owned validation workflows should:

- use read-only repository permissions unless broader authority is explicitly required;
- cancel superseded runs for the same ref;
- pin third-party GitHub Actions by full commit SHA;
- enforce the public repository boundary when checked-out repository content is being validated;
- avoid ordinary GitHub Actions artifact storage for generated practice outputs.


## Process contract

All stable `guitarctl` operational commands follow the same process contract:

- `0` — success;
- `2` — CLI usage/argument error from argument parsing;
- `65` — invalid data or a validation failure;
- `69` — a required external/development dependency is unavailable;
- `70` — an unexpected internal/process error.

Machine-readable result data is written to stdout. Diagnostics and validation failures are written to stderr.

The historical scripts under `scripts/` are compatibility shims only. They may preserve historical direct-script exit behavior for old callers, but CI and documentation use `guitarctl`.


## Compatibility-shim removal policy

A historical script shim may be deleted only when all of these are true:

1. the corresponding package-native `guitarctl` command/use case exists;
2. parity tests cover the externally observable behavior that old callers depend on;
3. CI and user-facing documentation no longer execute or recommend the shim;
4. repository/package consumers do not import the shim for canonical behavior; and
5. any intentionally retained historical Python API is explicitly documented.

The operational shims remain classified in the command architecture until these conditions are satisfied. CI does not enumerate individual shim filenames; broad `scripts/**` / `tools/**` repository-validation triggers may still watch compatibility code without making workflow behavior depend on a shim path.
