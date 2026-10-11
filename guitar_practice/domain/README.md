# Domain layer

The domain is the deterministic functional core: practice state, musical invariants, assessment/scheduling semantics, and other rules that should be reproducible from explicit inputs.

No domain module may depend on argument parsing, subprocesses, filesystem paths, network clients, clocks, environment variables, or presentation code. Those dependencies enter through application ports and adapters.

## Symbolic score contract

`score.py` defines the pure, deterministic Score IR contract: schema/version checks, exact musical-time invariants, parts/events, guitar pitch-position coherence, form/harmony, provenance, and canonical JSON serialization. Importers, exporters, CLI handlers, filesystem access, playback processes, and hardware concerns stay outside the domain module. See `docs/architecture/score-ir.md`.


## DSP preset contract

`dsp_preset.py` defines the pure producer-side contract for
`guitar-dsp.preset` v1. It validates bounded explicit delay configuration
and emits canonical wire JSON without importing DSP source, hardware, Score
IR, or practice-state semantics. Device transport remains outside the domain.
