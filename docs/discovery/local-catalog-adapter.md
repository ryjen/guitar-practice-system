# Local Discovery Catalog Adapter

## Purpose

`scripts/discovery_catalog.py` is the first executable Discovery adapter. It searches a local JSON catalog and normalizes untrusted provider output into the provider-neutral candidate contract.

It uses only the Python standard library and performs no network or domain-state writes.

## Boundaries

The adapter may:

- validate a Discovery request and local catalog
- rank local records deterministically
- report matched and unmet constraints
- normalize provider candidates through a strict field allowlist
- cap confidence according to retained evidence
- degrade safely when a catalog is unavailable or has no match

It does not:

- browse the web
- execute returned links, scripts, MIDI, DAW files, or downloads
- write songs, progress, evidence, schedules, or gear state
- approve or activate candidates
- invent candidates when the local catalog is empty

## Repository catalog

The initial catalog is [`catalogs/discovery/repository.json`](../../catalogs/discovery/repository.json). It indexes only existing repository-owned material:

- technique records
- gear setups
- original backing tracks

The song catalog intentionally remains empty until a candidate is explicitly approved and promoted through the song-use-case layer.

## Search

```bash
python scripts/discovery_catalog.py search \
  examples/discovery/slide-backing-track-request.json \
  catalogs/discovery/repository.json
```

The result includes:

- `complete` or `degraded` status
- a deterministic request fingerprint
- deterministic ephemeral candidate IDs
- ranked candidates
- matched and unmet constraints
- evidence-backed confidence
- warnings

`required_constraints` are hard filters. Other constraints affect ranking and remain visible as trade-offs.

## Normalize provider output

```bash
python scripts/discovery_catalog.py normalize \
  request.json \
  provider-output.json \
  --provider web-ai
```

Provider output may be either a candidate list or an object containing `candidates`.

Normalization:

- retains only candidate-contract fields
- drops unsupported fields such as approval, progress, or active-state mutations
- forces the requested target type
- preserves warnings for dropped or changed data
- removes malformed candidates
- caps confidence at the strongest retained evidence state
- never treats normalization as verification

## Request shape

```json
{
  "target_type": "backing-track",
  "goal": "Find a slow blues backing track for slide phrasing",
  "limit": 3,
  "required_constraints": ["genres", "techniques"],
  "constraints": {
    "genres": ["blues"],
    "styles": ["slow-blues"],
    "techniques": ["slide"],
    "gear_ids": ["amp-fender-deluxe-reverb"],
    "roles": ["lead"],
    "tuning": "standard",
    "meter": "4/4",
    "tempo_bpm": {"min": 50, "max": 72},
    "difficulty": "intermediate"
  }
}
```

Canonical top-level genres are `80s-rock`, `alt-rock`, `blues`, `country`, and `jazz`. Styles remain extensible descriptive tags.

## Catalog item shape

```json
{
  "version": 1,
  "items": [
    {
      "id": "example-id",
      "target_type": "technique",
      "title": "Example",
      "genres": ["blues"],
      "styles": ["blues-rock"],
      "techniques": ["slide"],
      "evidence": [
        {
          "state": "verified",
          "source": "docs/example.md",
          "kind": "repository"
        }
      ],
      "licensing": "original repository material"
    }
  ]
}
```

## Failure behaviour

| Condition | Behaviour |
|---|---|
| Catalog path missing | Exit successfully with `degraded` status and no candidates |
| Valid catalog with no match | Return `degraded` and no invented candidates |
| Invalid request or catalog | Exit code 2 with an error on stderr |
| Malformed provider candidate | Drop candidate and retain a warning |
| Provider confidence without evidence | Cap confidence at `low` |
| Unsupported provider fields | Drop fields and retain a warning |

## Extension boundary

Future adapters may add repository metadata extraction, curated external source lists, provider-specific retrieval, stronger schema validation, and cross-catalog deduplication. All providers must normalize through the same candidate and approval boundary.
