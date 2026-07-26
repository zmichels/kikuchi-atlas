# Kikuchi Atlas public-release contract

## Status

The source repository is public at
[`zmichels/kikuchi-atlas`](https://github.com/zmichels/kikuchi-atlas), and its
existing browser-safe static gallery is public at
[`zmichels.github.io/kikuchi-atlas`](https://zmichels.github.io/kikuchi-atlas/).
The [full-resolution UMN Drive
mirror](https://drive.google.com/drive/folders/1aUvGSjpQsGqyAlmLcS_vafcHQ6jVciZ4)
and its [Google Sites
catalogue](https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test) have
passed their separate public-access gates. The 125-product link-complete candidate is pending
independent review, merge to `master`, a successful
protected-environment workflow run, and observed live verification. Until
those gates pass, this contract does not claim that the live GitHub gallery
serves the link-complete candidate. The separately reviewed archive and DOI release remain intentionally unpublished.

The Drive upload completed before publication, but full Drive round-trip downloads were waived by the user.
The mirror ledger therefore records public
folder identity and logged-out accessibility without inventing per-product
round-trip package hashes or verification timestamps.

## Deliverables

`scripts/build_public_atlas.py --stage-archive` emits:

- `dist/atlas-public/site/` — a self-contained static browsing gallery;
- `dist/atlas-public/site/release-inventory.html` — a human-readable release
  inventory linked from every page;
- `dist/atlas-public/release-inventory.json` — machine-readable product,
  web-asset, archive-asset, SHA-256, recipe, and claim-boundary metadata; and
- `dist/atlas-public/archive/` — selected original media, previews,
  provenance records, tracked registries, recipes, checksums, and release
  notes suitable for a separately reviewed archival upload.

Tracked pre-publication metadata lives alongside the Atlas source:

- `CITATION.cff` and `.zenodo.json` describe the eventual code release;
- `RELEASE_METADATA.yml` records the public source and gallery URLs alongside
  the still-unresolved archive DOI and stable release-version choices; and
- `STRUCTURAL_SOURCE_AUDIT.json` plus `STRUCTURAL_SOURCE_ATTRIBUTION.md`
  enumerate the exact source records, terms, checksums, and citations for all
  Atlas phases.

The confirmed project license split is MIT for code and CC BY 4.0 for
project-owned Atlas media/geometry. See the repository `LICENSE` and
`LICENSES/ATLAS_MEDIA_AND_GEOMETRY.md`; source structures remain governed by
their individual audit records.

The gallery permits only PNG, SVG, JPEG, and MP4 assets at or below 25 MiB.
STL geometry and other heavier materials remain in the archive path rather
than being made implicit web-host dependencies. Canonical kinematical master
and relief-field exports are selected into the archive when their bundle has
them; redundant run intermediates stay recipe-reconstructible.

## Pending link-complete static-gallery candidate

The
[`atlas-gallery-web-0.2.0-draft.3` prerelease](https://github.com/zmichels/kikuchi-atlas/releases/tag/atlas-gallery-web-0.2.0-draft.3)
is the collision-free review candidate payload. It supersedes the earlier
gallery transport without moving, overwriting, deleting, or reusing an
existing tag or release. The Pages workflow reconstructs the gallery from its
ordered assets, checks the reconstructed ZIP against its pinned SHA-256, and
deploys only the resulting static `site/` tree after the reviewed workflow
reaches `master`. The release payload is deliberately a technical deployment
transport rather than the final archival distribution. Publication status
changes only after a successful master deployment and observed live
verification.

Every candidate product links to its exact public Drive package folder, and
the GitHub gallery links back to the public Google Site. The folder links do
not imply the waived package-level download-and-hash comparison.

## Remaining release gates

For the archive DOI release:
1. Assign a stable archive release version rather than the current draft tag.
2. Rebuild the local Atlas and archive package from a clean checkout.
3. Review the selected archive payload, checksums, structural-source terms,
   authorship, citation, and license terms.
4. Publish the separately reviewed archive package, record its DOI, and add
   stable download links to a future public release registry.

## Claim boundary

The Atlas gallery contains modeled visualizations and printable geometry. It
does not claim to host acquired EBSD patterns, camera-calibrated detector
simulations, or a dictionary-indexing dataset unless a later release is
explicitly documented and validated as such.
