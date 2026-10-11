# Versioned practice releases

Versioned GitHub Releases distribute deterministic public practice outputs without making generated binaries canonical source.

## Version identity

The project version is `project.version` in `pyproject.toml`. A release tag must be exactly `v<project.version>`. For project version `0.1.0`, the accepted tag is `v0.1.0`.

`guitarctl release prepare` fails closed unless:

- the tag uses `vMAJOR.MINOR.PATCH`;
- the tag exactly matches the project version;
- the source SHA is a full lowercase 40-character Git SHA; and
- any supplied previous tag also uses the version-tag format.

The practice-bundle provenance records the source tag/SHA, project version, versioned public contract/catalog versions, Python runtime, generator-input hashes, and SHA-256 hashes for generated/public payload files.

## Local regeneration

Generate the material-change input from the exact tagged revision. For a subsequent release:

```bash
previous_tag=v0.0.9
current_tag=v0.1.0
mkdir -p generated

git diff --name-only "$previous_tag" HEAD -- \
  backing-tracks \
  catalogs/grooves \
  catalogs/progressions \
  catalogs/practice-data.json \
  contracts/backing-tracks \
  contracts/progressions \
  contracts/dsp > generated/release-changes.txt

guitarctl validate repo

guitarctl release prepare \
  --tag "$current_tag" \
  --source-sha "$(git rev-parse HEAD)" \
  --previous-tag "$previous_tag" \
  --changed-paths generated/release-changes.txt \
  --output-dir generated/release

guitarctl release verify \
  --tag "$current_tag" \
  --source-sha "$(git rev-parse HEAD)" \
  --output-dir generated/release
```

For the initial release, use `git ls-files` over the same public paths to populate `generated/release-changes.txt` and omit `--previous-tag`.

The output directory contains:

- `guitar-practice-system-<tag>/` — unpacked public practice bundle;
- `guitar-practice-system-<tag>.tar` — deterministic release archive;
- `guitar-practice-system-<tag>.tar.sha256` — archive checksum sidecar;
- `RELEASE.md` — deterministic release notes and regeneration instructions.

The archive contains generated backing-track MIDI, public backing-track/groove/progression manifests and contracts, the DSP preset contract/fixture, validated `practice-data`, `provenance.json`, and the bundle's internal `SHA256SUMS`.

Archive entries are sorted with fixed ownership, mode, and modification time. `release verify` checks provenance identity, payload hashes, internal checksums, archive content/order/metadata, and the archive checksum sidecar.

## GitHub workflow

`.github/workflows/release.yml` runs only for `v*` tag pushes.

1. `validate-release` has read-only repository permission. It verifies tag/SHA identity, runs `guitarctl validate repo`, derives bounded material-change notes, builds the release twice, runs `release verify`, compares both outputs byte-for-byte, and checks the archive sidecar.
2. `publish-release` depends on the successful validation job and receives only `contents: write`. It checks out the same tag/SHA, regenerates and verifies the package again, then publishes the tar, checksum sidecar, and `RELEASE.md` directly to a GitHub Release with `gh release create`.

There is no `actions/upload-artifact` or `actions/download-artifact` handoff. Release files exist only in the ephemeral runner workspace until the explicit GitHub Release publication step. Publishing fails when a release for the tag already exists instead of mutating an existing versioned release.

Rendered audio remains out of scope until the rendering toolchain and licensing/provenance are suitable for deterministic public distribution.
