# Local Discovery Catalog

## Purpose

`scripts/discovery_catalog.py` searches a local JSON catalog using explicit constraints and deterministic ranking rules.

It uses only the Python standard library, performs no network access, and never writes domain state.

## Boundaries

The catalog search may:

- validate a request and local catalog
- apply hard required constraints
- score optional matched constraints
- rank records deterministically
- report matched and unmet constraints
- retain repository provenance and licensing metadata
- degrade safely when a catalog is unavailable or has no match

It does not:

- browse external sources
- normalize arbitrary external output
- execute returned links, scripts, MIDI, DAW files, or downloads
- write songs, progress, evidence, schedules, or gear state
- approve or activate candidates
- invent candidates when the local catalog is empty

## Repository catalog

The initial catalog is [`catalogs/discovery/repository.json`](../../catalogs/discovery/repository.json). It indexes repository-owned material such as:

- technique records
- gear setups
- original backing tracks

Catalog records are explicit metadata. Missing values remain unknown and do not receive inferred defaults.

## Search

```bash
python scripts/discovery_catalog.py \
  examples/discovery/slide-backing-track-request.json \
  catalogs/discovery/repository.json
```

The result includes:

- `complete` or `degraded` status
- catalog and catalog version
- deterministic request fingerprint
- deterministic ephemeral candidate IDs
- ranked candidates
- matched and unmet constraints
- source/provenance references
- warnings

`required_constraints` are hard filters. Other constraints affect the documented score and remain visible as trade-offs.

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
          "source": "docs/example.md",
          "kind": "repository"
        }
      ],
      "licensing": "original repository material"
    }
  ]
}
```

## Ranking semantics

For each candidate:

- each matching requested list value contributes a fixed documented amount
- matching scalar values contribute a fixed documented amount
- tempo contributes only when the catalog BPM is inside the requested range
- required-constraint misses remove the item
- final ties are ordered by stable `source_id`

The score is a reproducible sorting mechanism, not a quality or mastery judgment.

## Failure behaviour

| Condition | Behaviour |
|---|---|
| Catalog path missing | Return `degraded` with no candidates |
| Valid catalog with no match | Return `degraded` with no invented candidates |
| Invalid request or catalog | Exit code 2 with an error on stderr |
| Unknown optional metadata | Leave the corresponding constraint unmet or unconstrained |
| Equal scores | Sort by stable source ID |

## Extension boundary

Public extensions may add deterministic repository metadata extraction, curated static catalogs, stronger schema validation, or cross-catalog deduplication. External retrieval, private ranking, or opaque recommendation behavior is outside this adapter.
