# ADR-0003: Private ownership of all AI work

## Status

Accepted.

## Context

The previous public/private split allowed deliberately disclosed reference prompts and AI-adjacent public interfaces. That boundary is too permissive for the intended commercial and governance model.

AI-related work tends to combine product judgment, prompts, provider behavior, evaluation methods, datasets, operational controls, and future roadmap assumptions. Even apparently generic AI examples can expose product direction or create an unstable public dependency.

## Decision

All AI-related work belongs exclusively in the private `guitar-practice-platform` repository.

The public `guitar-practice-system` repository must remain AI-independent.

AI-related work includes:

- prompts and prompt templates
- model, provider, agent, orchestration, tool, and routing code
- retrieval, embeddings, model-derived metadata, and datasets
- AI-assisted discovery, coaching, recommendation, generation, or evaluation
- guardrails, traces, red-team cases, model fallbacks, and cost controls
- AI-specific schemas, fixtures, examples, interfaces, documentation, issues, and roadmap work

There is no promotion path for AI material from private to public.

When an AI capability needs a public dependency, only an independently useful, AI-neutral domain contract or deterministic mechanism may be extracted and reviewed separately.

## Migration

The active public `prompts/` directory is removed. Its files are copied into the private repository under `ai/prompts/reference-import/` for provenance.

Those files remain disclosed in public Git history and must not be treated as confidential or commercially differentiating.

## Consequences

### Positive

- Establishes an unambiguous repository boundary
- Prevents accidental disclosure of AI product direction and implementation detail
- Keeps public contracts stable and useful without model dependencies
- Simplifies review: any AI-related public change is rejected or moved private

### Negative

- Public users do not receive prompt examples or AI-provider adapters
- AI-neutral contracts may require deliberate extraction from private capabilities
- Previously public prompt history remains permanently disclosed

## Enforcement

- Public PR checklist rejects all AI-related changes
- Public roadmap and issues must not describe planned AI capabilities
- Private policy owns all AI artifacts and prohibits promotion back to public
- Boundary reviews treat ambiguous or AI-adjacent work as private by default
