# Public/private IP boundary

This policy governs the public `guitar-practice-system` repository and the private `guitar-practice-platform` repository.

## Non-negotiable AI rule

All AI-related material belongs exclusively in `guitar-practice-platform`.

This includes prompts, model-provider code, routing, orchestration, agents, retrieval, embeddings, AI-assisted discovery, coaching, recommendation, generation, evaluation, datasets, traces, guardrails, experiments, AI-specific schemas, examples, fixtures, issues, documentation, and roadmap work.

There is no promotion path from private to public for AI material.

When a private AI capability needs a public dependency, extract only an AI-independent domain contract or deterministic mechanism that remains useful without mentioning models, prompts, providers, or AI product behavior.

## Classification model

| Classification | Repository | Examples |
|---|---|---|
| `PUBLIC-CORE` | Public | Domain schemas, portable formats, validators, deterministic CLI behavior |
| `PUBLIC-INTERFACE` | Public | AI-independent compatibility contracts and fixtures |
| `PUBLIC-REFERENCE` | Public | Synthetic musical examples and deterministic baseline algorithms |
| `PRIVATE-AI` | Private | Every AI-related artifact or capability |
| `PRIVATE-PRODUCT` | Private | Hosted workflows, product UX, entitlements, marketplace |
| `PRIVATE-INTELLIGENCE` | Private | Ranking, adaptation, evaluation, routing, learned heuristics |
| `PRIVATE-CONTENT` | Private | Premium curricula, licensed material, unreleased editorial plans |
| `PRIVATE-DATA` | Private | Practice history, recordings, customer data, telemetry, experiments |
| `SECRET` | Private secret store | Credentials, signing keys, tokens, endpoints, production configuration |

A file may contain only one effective classification. Split mixed files rather than placing private or AI material beside public content.

## Public repository ownership

The public repository may own:

- musical domain concepts and schemas
- deterministic validation and compatibility behavior
- local-first workflows
- deterministic catalog search and ranking
- AI-independent extension points
- synthetic, owned, public-domain, or redistribution-safe examples
- provenance, approval, privacy, and safety invariants

It must not contain AI-related code, documentation, examples, interfaces, prompts, plans, issues, or fixtures.

## Private repository ownership

The private platform owns:

- all AI work
- hosted services and production operations
- personalization and proprietary recommendation logic
- identity, tenancy, synchronization, billing, and entitlements
- premium and licensed content
- user-derived analytics and experimentation
- product planning, pricing, acquisition, and commercial metrics
- deployment, observability, incident response, and threat-model details

## Cross-repository contracts

The private platform may depend on tagged versions of the public core. The public core must not depend on, import, fetch, or test against private source code.

Allowed public integration mechanisms:

- versioned AI-independent JSON Schema or OpenAPI contracts
- tagged packages or release artifacts
- stable deterministic command-line interfaces
- synthetic compatibility fixtures

Prohibited public integration mechanisms:

- prompt contracts or prompt examples
- model-provider or agent interfaces
- AI-specific fields, schemas, or extension points
- model-derived production fixtures
- references to private product or AI roadmap behavior
- imports from private Git URLs

## Promotion from private to public

Private non-AI work may be promoted only after generalization, provenance review, security review, and removal of product-specific assumptions.

AI material may not be promoted. Only a separately extracted AI-independent mechanism may be considered.

## Existing public material

Files already committed publicly must be assumed disclosed. Deleting or moving them does not make them confidential again.

The former public prompt directory has been removed from the active tree and copied into a private provenance area. Those imported prompts remain disclosed and must not be treated as commercial differentiation.

## Review rule

Reject or move a public change when it introduces or discusses:

- AI, models, prompts, agents, embeddings, retrieval, or model providers
- AI-assisted discovery, coaching, recommendation, or generation
- model evaluation, guardrails, traces, datasets, or derived metadata
- future AI capabilities or AI-specific public interfaces

When uncertain, the work starts private.
