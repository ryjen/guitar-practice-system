# Public/private IP boundary

This policy is the operational guardrail between the public `guitar-practice-system` repository and the private `guitar-practice-platform` product repository.

## Classification model

| Classification | Repository | Examples |
|---|---|---|
| `PUBLIC-CORE` | Public | Domain schemas, portable formats, validators, reference CLI behavior |
| `PUBLIC-INTERFACE` | Public | Provider contracts, compatibility fixtures, extension points, generic API descriptions |
| `PUBLIC-REFERENCE` | Public | Synthetic examples, deliberately disclosed prompts, baseline algorithms |
| `PRIVATE-PRODUCT` | Private | Hosted workflows, product UX, orchestration, entitlements, marketplace |
| `PRIVATE-INTELLIGENCE` | Private | Production prompts, ranking, adaptation, evaluation, routing, learned heuristics |
| `PRIVATE-CONTENT` | Private | Premium curricula, licensed material, unreleased editorial plans |
| `PRIVATE-DATA` | Private | Practice history, recordings, customer data, telemetry, experiments |
| `SECRET` | Private secret store | Credentials, signing keys, tokens, private endpoints, production configuration |

A file may contain only one effective classification. Split mixed files rather than relying on comments to hide sensitive sections.

## Decision test

Before adding material to the public repository, answer these questions:

1. Can the material be independently useful without the private product?
2. Is it generic across users rather than derived from one customer, cohort, or proprietary dataset?
3. Are all examples synthetic, owned, licensed for redistribution, or clearly public domain?
4. Would publishing the implementation weaken commercial differentiation, fraud controls, abuse resistance, or operational security?
5. Does it contain production prompts, thresholds, ranking weights, evaluation criteria, business strategy, pricing, or roadmap detail?
6. Could it expose personal practice data, recordings, identifiers, or third-party confidential information?

Any `no` to questions 1–3 or `yes` to questions 4–6 means the work starts private.

## Repository ownership

### Public repository

The public core owns stable, portable mechanisms:

- domain concepts and schemas
- validation and compatibility behavior
- provider-neutral interfaces
- deterministic reference implementations
- local-first workflows
- synthetic examples and baseline content
- provenance and approval invariants

Public reference implementations are intentionally disclosed and must be treated as prior art for this project. New commercial differentiation must not be layered directly into them.

### Private repository

The private platform owns product judgment and operations:

- personalization beyond the public baseline
- production AI orchestration and evaluation
- account, billing, entitlement, tenancy, and synchronization systems
- premium and licensed content
- user-derived analytics and experimentation
- teacher, school, partner, and marketplace workflows
- product planning, pricing, acquisition, and commercial metrics
- deployment, observability, incident response, and threat-model details

## Cross-repository contracts

The private platform may depend on tagged versions of the public core. The public core must not depend on, import, fetch, or test against private source code.

Allowed integration mechanisms:

- versioned JSON Schema or OpenAPI contracts
- tagged packages or release artifacts
- stable command-line interfaces
- synthetic compatibility fixtures
- documented extension/provider interfaces

Avoid:

- copying private implementation into public examples
- importing a private Git URL from public build files
- public test fixtures captured from production
- public issue descriptions that reveal unreleased product behavior
- screenshots, logs, or traces containing customer or operational data

## Promotion from private to public

Private work may be promoted only when all of the following are true:

1. The implementation has been generalized and stripped of product assumptions.
2. Inputs and fixtures are synthetic or redistribution-safe.
3. Secrets, identifiers, telemetry, and production configuration are absent.
4. Production prompts, weights, thresholds, and evaluations remain private unless disclosure is intentional.
5. Security and abuse-resistance implications have been reviewed.
6. A public contract and compatibility tests are sufficient for downstream use.
7. The promotion is documented as an explicit disclosure decision.

## Existing public material

Files already committed publicly must be assumed disclosed. Deleting or moving them does not make them confidential again.

Existing prompts and adaptive scripts may remain as `PUBLIC-REFERENCE` baselines. Product development must fork conceptually behind a private interface rather than incrementally turning those public files into production implementations.

## Review cadence

Review this boundary when any of the following occurs:

- a new hosted capability is proposed
- a public schema gains product-specific fields
- a new AI prompt, evaluator, or ranking mechanism is introduced
- premium or licensed content is added
- telemetry or user data becomes an input
- a private implementation needs a new public extension point
- a contributor is uncertain where work belongs

Uncertain work defaults to the private repository until reviewed.
