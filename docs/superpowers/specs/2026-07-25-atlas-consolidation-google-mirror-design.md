# Kikuchi Atlas Consolidation and Google Mirror Design

**Date:** 2026-07-25

**Status:** User-approved design

## Goal

Consolidate every publishable Kikuchi Atlas product into one canonical local
phase/product hierarchy, add the three completed quartz artist-master products
that are not yet in the Atlas registry, update the existing GitHub Pages Atlas,
and create a public University of Minnesota Google Sites/Drive mirror that can
carry the full-resolution publication payload.

This work must preserve every existing phase and product. It must not resume
the paused grossular, almandine, or tremolite phase-expansion batch.

The final local root is:

```text
/Users/Z/Documents/kikuchi/local/atlas/phases/
```

The acceptance target is 12 phases and 125 available individual products.

## Starting State

- The tracked Atlas registry contains 12 phases and 122 `local-published`
  products.
- Three completed quartz artist-master products are recorded in the artifact
  catalog and acceptance/work records but are not registered as Atlas products:
  - Direct-reflector artist master, x-axis rotation.
  - Near-depth identity artist master, 60 fps.
  - Near-depth oblique 17/31/43 artist master, 60 fps.
- The five-phase orientation gallery remains review evidence and is not an
  individual phase product.
- Publishable artifacts are scattered across ten ignored `local/` roots.
- The full current `local/` tree is approximately 33.69 GiB across 10,099
  files. This includes working intermediates that are outside the publication
  scope.
- The current GitHub Pages deployment is behind the local 12-phase Atlas.
- The existing public site and repository are:
  - `https://zmichels.github.io/kikuchi-atlas/`
  - `https://github.com/zmichels/kikuchi-atlas`
- The verified UMN account is `zmichels@umn.edu`. Google Drive reports
  7.82 GB used of a 100 GB allocation, leaving 92.18 GB available.
- That account permits Drive files to be shared with anyone on the internet
  who has the link.
- Google Sites offers a `Public` audience for published sites. The unpublished
  test draft is named `Kikuchi Atlas publishing test` and proposes:
  `https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test`.
- The locally mounted UMN Drive at
  `/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu` is a different
  account and must not be used for this publication.

## Publication Architecture

### 1. Canonical local product store

The canonical local product store is the source of publication truth for
generated artifacts. Tracked structural sources remain in:

```text
phases/<slug>/
```

Only generated, publishable products move under:

```text
local/atlas/phases/<slug>/products/<product-id>/
```

Each product package uses this structure:

```text
<product-id>/
  product-package.yml
  media/
  previews/
  web/
  provenance/
```

- `media/` holds the authoritative publication artifact, including
  full-resolution artist masters and printable meshes.
- `previews/` holds thumbnails, posters, and still previews.
- `web/` holds browser-friendly proxies when the authoritative artifact is too
  large or unsuitable for direct browser playback.
- `provenance/` holds a self-contained export of the product's release
  metadata, checksums, source/recipe identities, and tracked-record references.
- `product-package.yml` inventories every packaged file and records its byte
  count, SHA-256, MIME type, role, source commit, registry identity, and
  intended publication destinations.

A phase-level `phase-package.yml` inventories its product packages. Paths in
package manifests are relative to the phase package; public artifacts may not
contain absolute local paths.

### 2. Atlas registries and builders

`docs/atlas/PHASES.yml`, `docs/atlas/PRODUCT_REGISTRY.yml`, and
`docs/atlas/RELEASE_METADATA.yml` remain the curated relational source for
Atlas navigation and publication state.

The product registry will be updated to canonical package paths and will add
the three quartz artist-master records. Existing product IDs and scientific
claims remain unchanged unless a direct validation failure requires a
documented correction.

Current runtime, acceptance, release, and tracker files will be updated to the
canonical paths. Historical specifications and plans retain their original
path evidence and are not rewritten as though the new layout existed earlier.

### 3. GitHub Pages catalogue

GitHub Pages remains the primary fast catalogue. It publishes:

- Phase and product navigation.
- Preview images.
- Browser-friendly SVG, PNG, JPEG, and MP4 assets.
- Provenance and product metadata.
- Links to the UMN mirror for full-resolution media and complete downloads.

The existing release-driven Pages workflow remains in place. A new release
payload, split archive, release inventory, checksum, workflow pin, and release
metadata will replace the stale deployment only after a clean local public
build. Heavy masters are not duplicated into the Pages deployment.

### 4. UMN Google Drive full-resolution mirror

The first mirror uses the verified `zmichels@umn.edu` My Drive because its
public-link behavior and available capacity have been observed directly. The
remote hierarchy is:

```text
Kikuchi Atlas/
  atlas-mirror.yml
  phases/
    <slug>/
      phase-package.yml
      products/
        <product-id>/
```

The remote hierarchy mirrors the canonical local phase/product layout.
Upload records store stable Drive file IDs and public URLs separately from
local package manifests so an upload or URL change never alters the scientific
artifact identity.

Existing remote quartz files are deduplication candidates only. A matching
name or displayed size is insufficient: an existing remote item is accepted
only after its byte count and checksum match the canonical local file.

The correct UMN account is not currently mounted in Google Drive for Desktop.
Implementation must therefore use one of these verified transports:

1. Add `zmichels@umn.edu` to Google Drive for Desktop with user participation,
   then verify the mounted account before copying; or
2. Upload phase packages through the signed-in Chrome session.

No data may be copied into the mounted `mich0201@umn.edu` tree.

### 5. Google Sites mirror

The Google Site is a public research-distribution mirror, not a second custom
web application. It contains:

- A landing page describing the Atlas and its claim boundaries.
- A phase directory with one page per current phase.
- Links to the primary GitHub Pages phase/product catalogue.
- Links to the corresponding public Drive phase folder and full-resolution
  products.
- A provenance/about page explaining sources, recipes, checksums, licenses,
  and nonclaims.

The Site may embed the GitHub Pages catalogue where Google Sites supports the
embed cleanly, but all navigation must still work through ordinary links if
the embed is blocked.

The current test draft may be reused and renamed for the production mirror.
It remains unpublished until the final publication gate.

## Transactional Cutover

### 1. Freeze and inventory

Create a machine-readable migration ledger mapping every registry-referenced
legacy artifact to its canonical package destination. Record byte counts and
SHA-256 values before copying.

Classify each legacy file as:

- Publishable canonical artifact.
- Publishable preview or web proxy.
- Provenance required by a product package.
- Nonpublishable working intermediate.
- Historical evidence that remains in place.

### 2. Copy and verify

Populate the canonical tree with APFS clone copies when available, otherwise
normal copies. Do not use symlinks or hard links. Preserve original filenames
inside their package roles.

Each destination must match its source byte-for-byte. The migration ledger and
package manifests must be complete before registries change.

### 3. Register and rebuild locally

Update current registry, release, acceptance, tracker, script, and test
references. Register the three quartz products, giving the Atlas 12 phases and
125 products.

Build the local Atlas entirely from canonical paths. The build must not fall
back to any legacy publishable root.

### 4. Build and deploy GitHub Pages

Create or verify web proxies for heavyweight products, including both
near-depth quartz movies. Build the public site and release archive, verify
that no local paths survive, publish the new GitHub release payload, update the
workflow pin, and deploy Pages.

The existing Pages deployment remains live until its replacement passes all
local and release checks.

### 5. Upload and verify Drive

Upload the canonical publication packages phase by phase. Record the Drive
identity and public URL for every uploaded item. Stop before capacity becomes
unsafe: the anticipated remaining quota after upload must include at least
10 GB of headroom.

For every remote item, verify:

- Expected filename and package location.
- Byte count.
- Checksum or a downloaded byte-for-byte comparison.
- Public-view behavior where the item is intended to be public.

Interrupted uploads resume from the mirror ledger rather than restarting the
entire collection.

### 6. Build and publish Google Sites

Build the Site pages from the verified phase inventory. Before publication,
test all GitHub and Drive links from the draft.

Changing the Site audience to `Public`, changing the Drive mirror to public
access, and pressing the final Publish control are consequential permission
and publication actions. Obtain action-time user confirmation immediately
before those steps.

After publication, verify the Site and representative full-resolution Drive
files in a logged-out browser context.

### 7. Remove legacy publishable copies

Legacy publishable files are removed immediately only after all of these are
true:

- The canonical local Atlas is complete.
- The 12-phase/125-product local build passes.
- The updated GitHub Pages site is live and verified.
- The Google Drive inventory is complete and publicly accessible.
- The Google Site is public and verified.
- Every canonical artifact has an accepted checksum.

Delete only the exact legacy publishable paths listed in the migration ledger.
Nonpublishable intermediates remain outside the Atlas hierarchy.

After deletion, rerun the local and public builders from canonical paths. A
successful post-delete rebuild proves that no hidden legacy fallback remains.

## Failure Handling

- **Path collision:** Identical hashes deduplicate. Same-name/different-byte
  artifacts receive distinct product-controlled names; nothing is overwritten.
- **Missing provenance:** The product remains unavailable and the cutover
  stops for that product.
- **Remote capacity:** Stop before upload if the manifest total plus 10 GB
  exceeds reported free space.
- **Interrupted Drive sync:** Retain local canonical files and resume using the
  mirror ledger.
- **Public-sharing restriction:** Keep the Site or item unpublished and report
  the exact policy boundary.
- **Pages deployment failure:** Preserve the existing live release and repair
  the candidate deployment without deleting local or legacy files.
- **Remote checksum mismatch:** Upload a new verified object, retain both until
  the correct identity is established, and never relabel the mismatched object.
- **Cleanup failure:** Stop deletion immediately. Canonical and remote copies
  remain valid; unresolved legacy paths stay recorded.

## Verification and Acceptance

The completion gate includes:

- Registry schema and uniqueness tests.
- Exactly 12 phases and 125 available products.
- Package-manifest schema, existence, byte-count, and SHA-256 validation.
- No runtime dependency on legacy publishable roots.
- Local Atlas build and navigation smoke tests.
- Public-site build with no surviving local URLs.
- Browser playback/preview checks for web-safe products.
- GitHub release checksum and workflow-pin verification.
- Live GitHub Pages HTTP and navigation checks.
- Complete Google Drive mirror-ledger reconciliation.
- Logged-out access checks for the Drive root, every phase folder, and a
  representative sample of each media type.
- Logged-out Google Site navigation and link checks.
- A post-cleanup local and public rebuild.
- A durable acceptance record containing counts, hashes, public URLs,
  deployment identities, deviations, and nonclaims.

## Deliverables

- Canonical local phase/product packages.
- Migration and cleanup ledger.
- Twelve phase manifests and 125 product manifests.
- Updated Atlas registries, tests, current acceptance records, and release
  metadata.
- Updated local Atlas.
- Updated GitHub release and Pages deployment.
- Verified UMN Google Drive full-resolution mirror.
- Verified public Google Site.
- Final acceptance and post-cleanup verification record.

## Nonclaims

- Google Sites and My Drive are a convenient public distribution mirror, not a
  permanent research archive, CDN, or preservation guarantee.
- Public accessibility does not guarantee unlimited traffic or permanent URL
  stability.
- A browser-playable proxy is not the authoritative artist master.
- A remote filename or displayed size is not proof of artifact identity.
- The consolidation does not expand scientific scope, add new mineral phases,
  or imply that one structural reference represents an entire mineral group.
- Original third-party source payloads are not republished unless their rights
  and attribution explicitly permit it.
