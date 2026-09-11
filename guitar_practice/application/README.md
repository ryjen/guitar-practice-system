# Application layer

Application code coordinates deterministic use cases against inward-facing domain rules and outward-facing ports. It may depend on `domain` and protocol definitions in this package; it must not depend on concrete CLI, filesystem, network, or external orchestration implementations.

Inputs are explicit, validated, and versionable. Canonical state changes remain separate from read-only proposals or generated artifacts and require the same deterministic validation rules regardless of caller.
