---
id: KIKU-F012
type: feature
title: Prepare the Kikuchi Atlas for public release
status: active
parent: KIKU-E001
children:
  - KIKU-T051
  - KIKU-T052
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
- [ ] A future account/DOI decision is recorded before any external upload.

## Progress Evidence

- KIKU-T051 provides a tested public-gallery and archival-staging builder.
- KIKU-T052 remains intentionally deferred until the user selects the public
  hosting/repository identity and archival metadata.
