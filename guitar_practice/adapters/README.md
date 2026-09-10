# Adapter layer

Adapters implement application ports for concrete deterministic side effects and integrations such as filesystems, artifact encoders, and temporary legacy migration bridges.

Adapters should expose bounded capabilities rather than ambient process authority. External callers interact through the same validated application contracts as local callers.
