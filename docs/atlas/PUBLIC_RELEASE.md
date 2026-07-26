# Kikuchi Atlas public-release contract

## Status

The source repository is public at
[`zmichels/kikuchi-atlas`](https://github.com/zmichels/kikuchi-atlas), and its
existing browser-safe static gallery is public at
[`zmichels.github.io/kikuchi-atlas`](https://zmichels.github.io/kikuchi-atlas/).
The new 12-phase, 125-product candidate is pending independent review, merge to
`master`, a successful protected-environment workflow run, and observed live
verification. Until those gates pass, this contract does not claim that the
live gallery serves the candidate. The full-resolution UMN mirror remains
private, and the separately reviewed archive and DOI release remain
intentionally unpublished. No public Drive root or Google Site has passed its
separate publication gate.

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

## Pending static-gallery candidate

The
[`atlas-gallery-web-0.2.0-draft.2` prerelease](https://github.com/zmichels/kikuchi-atlas/releases/tag/atlas-gallery-web-0.2.0-draft.2)
is the review candidate payload. The Pages workflow reconstructs the gallery
from its ordered assets, checks the reconstructed ZIP against its pinned
SHA-256, and deploys only the resulting static `site/` tree after the reviewed
workflow reaches `master`. The release payload is deliberately a technical
deployment transport rather than the final archival distribution. Publication
status changes only after a successful master deployment and observed live
verification.

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
