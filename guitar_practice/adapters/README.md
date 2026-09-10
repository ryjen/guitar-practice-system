# Adapter layer

Adapters implement application ports for concrete side effects and integrations. Filesystems, artifact encoders, model/supervisor gateways, and legacy migration bridges live here.

Adapters should expose bounded capabilities rather than ambient process authority. AI adapters in particular receive explicit context and return proposals; they do not receive canonical mutation capabilities.
