---
id: KIKU-F008
type: feature
title: Consolidate the local Kikuchi Lab engine and product surface
status: done
parent: KIKU-E001
children:
  - KIKU-T039
created: 2026-07-19
priority: P0
tags: [integration, provenance, local-products, engine]
links:
  - ../architecture/REPO_MAP.md
  - ../architecture/INTEGRATION_HISTORY.md
  - ../products/ARTIFACT_CATALOG.yml
evidence:
  - ../../scripts/product_status.py
  - ../../tests/unit/test_product_status.py
---

# KIKU-F008: Consolidate the local Kikuchi Lab engine and product surface

## Description

Join the independently developed dynamical and spherical/direct-reflector
lineages into one local engine branch. Preserve the experimental MTEX/S2
workbench as an explicit, separately committed boundary; establish a durable
repository map and catalog rather than relying on worktree names or chat
history to locate products.

## Acceptance Criteria

- [x] The dynamical-master and spherical-intensity implementation branches are joined by a two-parent integration commit.
- [x] Shared source contracts use the fuller phase-general implementation while dynamical CLI coverage is retained.
- [x] The intentionally unaccepted MTEX/S2 workbench is preserved in its own committed branch and excluded from the stable surface.
- [x] The repository map, integration note, and product catalog document source, local-media, and claim boundaries.
- [x] A static product-catalog test and status command distinguish missing machine-local media from missing tracked render inputs.
- [x] Tracker validation and focused engine tests pass on the integration branch.
