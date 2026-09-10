# AI extension points

AI integrations are optional application adapters, not domain dependencies.

## Allowed roles

AI may propose candidate grooves, arrangements, practice contexts, progression alternatives, summaries, or explanations. A provider can be local (for example through the Dubnium supervisor gateway) or remote.

## Required controls

Every inference-backed proposal should retain provider/model/request identity and content digests. Generated material must pass deterministic validation before it can be approved. Canonical state mutation remains a separate explicit operation.

Provider failure, unavailability, or removal must not break deterministic practice, assessment, scheduling, catalog, or export workflows.

## Trust boundary

Treat model output exactly like untrusted external input:

1. parse into a bounded proposal schema;
2. reject unknown/oversized fields;
3. validate musical and state invariants deterministically;
4. retain provenance;
5. require approval for canonical mutation;
6. record the resulting state transition independently of the model transcript.

Do not give provider adapters ambient filesystem, credential, repository, or state-mutation capabilities merely because they are running inside a CLI process. Prefer capability-specific inputs and outputs.
