---
id: KIKU-F012
type: feature
title: Prepare the Kikuchi Atlas for public release
status: active
parent: KIKU-E001
children:
  - KIKU-T051
  - KIKU-T052
  - KIKU-T085
  - KIKU-T086
  - KIKU-T087
created: 2026-07-20
priority: P1
tags: [atlas, publication, provenance, archive]
links:
  - ../atlas/PUBLIC_RELEASE.md
  - ../atlas/README.md
  - ../atlas/PRODUCT_REGISTRY.yml
evidence:
  - ../../scripts/build_public_atlas.py
  - ../../src/kikuchi_lab/atlas/publication.py
  - ../acceptance/atlas-consolidation-and-google-mirror.md
---

# KIKU-F012: Prepare the Kikuchi Atlas for public release

## Description

Create a reproducible public-release surface without prematurely creating an
account, publishing a URL, or treating an Atlas visual as an acquired or
indexing-validated EBSD product. The release surface must separate
browser-safe gallery assets from DOI-oriented scientific/print artifacts.

## Acceptance Criteria

- [x] A deterministic build produces a public gallery with no surviving local
  filesystem links.
- [x] The gallery and archive have a machine-readable product and checksum
  inventory with explicit claim boundaries.
- [ ] A stable archival release version and DOI decision are recorded before the separate archive upload.

## Progress Evidence

- KIKU-T051 provides a tested public-gallery and archival-staging builder.
- KIKU-T052 remains intentionally deferred until the user selects the public
  hosting/repository identity and archival metadata.
- KIKU-T085 freezes and then materializes the 125 canonical product packages.
- KIKU-T086 refreshes the release-driven 125-product GitHub Pages catalogue.
- KIKU-T087 gates the UMN Drive and Google Sites mirror on action-time
  confirmation and logged-out verification.
- KIKU-T085, KIKU-T086, and KIKU-T087 are complete with a final acceptance
  record covering the canonical tree, live Pages, public Drive/Site mirror,
  recoverable cleanup, and explicit Drive round-trip nonclaim.
- The feature remains active only for the separately reviewed archival package
  and DOI. `archive_doi` is still null.
