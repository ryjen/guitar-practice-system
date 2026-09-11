# Domain layer

The domain is the deterministic functional core: practice state, musical invariants, assessment/scheduling semantics, and other rules that should be reproducible from explicit inputs.

No domain module may depend on argument parsing, subprocesses, filesystem paths, network clients, clocks, environment variables, or presentation code. Those dependencies enter through application ports and adapters.
