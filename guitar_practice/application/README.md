# Application layer

Application code coordinates use cases against inward-facing domain rules and outward-facing ports. It may depend on `domain` and protocol definitions in this package; it must not depend on concrete CLI, filesystem, network, or AI provider implementations.

Non-deterministic systems enter through proposal-oriented ports and cannot directly mutate canonical state.
