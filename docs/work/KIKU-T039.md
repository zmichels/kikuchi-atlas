---
id: KIKU-T039
type: task
title: Merge rendering lineages and publish the local product map
status: done
parent: KIKU-F008
depends_on:
  - KIKU-T018
  - KIKU-T038
created: 2026-07-19
priority: P0
tags: [integration, worktrees, product-catalog]
links:
  - ../architecture/REPO_MAP.md
  - ../architecture/INTEGRATION_HISTORY.md
  - ../products/ARTIFACT_CATALOG.yml
evidence:
  - ../../scripts/product_status.py
  - ../../tests/unit/test_product_status.py
---

# KIKU-T039: Merge rendering lineages and publish the local product map

## Description

Resolve the divergent local worktree history into one branch without
discarding either scientific-art lineage. Record the historical tracker-ID
collision explicitly, make the current product families discoverable, and keep
the advanced MTEX workbench out of the accepted core until separately reviewed.

## Acceptance Criteria

- [x] Conflicting shared modules, crystal records, CLI coverage, and dependency metadata are reconciled and tested.
- [x] Historical tracker collision handling is documented without deleting reachable history.
- [x] The selected dynamical, direct-reflector, retained-field, and printable anchor products have catalog entries with recipes and render entry points.
- [x] Catalog entries use repository-relative paths and have a locally testable static contract.
- [x] The primary checkout can become the sole stable source checkout; additional worktrees are explicitly archival or experimental.
