# Practice cockpit public export

The practice cockpit export is a versioned, static projection of public practice content for browser-facing consumers such as Entrobert Music.

## Ownership

`catalogs/practice-cockpit.json` is the canonical public catalog for the fields represented by this contract. The generated artifact at `docs/data/practice-cockpit.json` is a portable distribution copy.

The export deliberately does **not** contain:

- personal practice history or progress;
- recordings or evidence records;
- personal assessment results or scheduling state;
- consumer-specific configuration;
- inferred recommendations or other opaque derived state.

Those concerns remain outside this public export contract.

## Schema version

The top-level `schemaVersion` is an integer. Version `1` contains:

- `durationAllocations` for the supported 15, 30, and 45 minute session views;
- `sessions` with stable IDs, musical context, intent, explicit space, tempo progression, three stages, gear/use-case presentation metadata, and repository-relative provenance;
- `techniques` with stable IDs and concise public technique-path metadata.

Consumers must reject unsupported schema versions rather than silently guessing field meanings.

## Regeneration

From the repository root:

```sh
python scripts/export_practice_cockpit.py
```

CI verifies the checked-in export is semantically identical to the canonical catalog:

```sh
python scripts/export_practice_cockpit.py --check
```

The exporter also validates unique IDs, required fields, duration totals, repository-relative source references, and strictly increasing slow/medium/fast tempo ladders.

## Downstream consumption

A downstream static site should **vendor the generated artifact into its own source tree** during an explicit update. The deployed site should not depend on GitHub or this repository at runtime.

Recommended flow:

1. fetch or copy `docs/data/practice-cockpit.json` at a reviewed commit;
2. store the vendored copy in the downstream repository;
3. validate `schemaVersion` before build;
4. map data fields into the downstream presentation layer;
5. retain the source repository and commit provenance in the update commit or generated metadata;
6. deploy the downstream site with only local static assets.

This keeps the canonical content boundary clear while avoiding cross-origin availability, CSP, privacy, and supply-chain coupling at runtime.

## Change policy

- Additive compatible fields may remain within the same schema version only when existing consumers can safely ignore them.
- Removing, renaming, or changing the meaning/type of a field requires a new schema version.
- Stable IDs must not be repurposed for different sessions or techniques.
- Presentation-specific HTML/CSS structure does not belong in this contract.
- Personal scheduling state, assessment results, personalization, or opaque derived state do not belong in this contract.
