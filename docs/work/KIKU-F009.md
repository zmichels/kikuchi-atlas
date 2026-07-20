---
id: KIKU-F009
type: feature
title: Publish a provenance-first Kikuchi Atlas v0
status: active
parent: KIKU-E001
children:
  - KIKU-T040
  - KIKU-T041
  - KIKU-T042
  - KIKU-T044
  - KIKU-T045
  - KIKU-T046
  - KIKU-T047
created: 2026-07-20
priority: P1
tags: [atlas, phase-catalog, provenance, local-publication]
links:
  - ../atlas/README.md
  - ../atlas/PHASE_REGISTRY.yml
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../products/ARTIFACT_CATALOG.yml
evidence:
  - ../../scripts/build_atlas.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-F009: Publish a provenance-first Kikuchi Atlas v0

## Description

Create a browsable, local-first publication layer that organizes the project's
phase-specific visual and printable work without weakening existing scientific
claim boundaries. The Atlas data model must distinguish a verified source from
an intentionally named reference candidate and must leave room for later
master-pattern and dictionary products.

## Acceptance Criteria

- [x] The Atlas has a tracked phase registry with a claim boundary and an explicit source state for every entry.
- [x] A deterministic local command renders an index and one self-explanatory page per phase from the registry and product catalog.
- [x] Missing ignored `local/` media are reported as unavailable instead of being mistaken for a missing source or recipe.
- [x] Existing artifact-catalog phases are cross-checked against the Atlas registry.
- [x] The Atlas has a curated individual-product registry, phase-first product matrix, and a product-first searchable browse page.
- [ ] The first three candidate structures are promoted to tracked source records and receive accepted direct-reflector products.
