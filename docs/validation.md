# Repository validation

The repository has one canonical fast validation command for source changes:

```bash
python scripts/validate_repo.py
```

Install the pinned development dependency before the first run:

```bash
python -m pip install -r requirements-dev.txt
```

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
