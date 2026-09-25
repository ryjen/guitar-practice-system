# Domain layer

The domain is the deterministic functional core: practice state, musical invariants, assessment/scheduling semantics, and other rules that should be reproducible from explicit inputs.

No domain module may depend on argument parsing, subprocesses, filesystem paths, network clients, clocks, environment variables, or presentation code. Those dependencies enter through application ports and adapters.

## Symbolic score contract

`score.py` defines the pure, deterministic Score IR contract: schema/version checks, exact musical-time invariants, parts/events, guitar pitch-position coherence, form/harmony, provenance, and canonical JSON serialization. Importers, exporters, CLI handlers, filesystem access, playback processes, and hardware concerns stay outside the domain module. See `docs/architecture/score-ir.md`.

[executed on device: 2f3498544c93 (a7fd9f41-8002-4c03-ac43-498109dd9775)]