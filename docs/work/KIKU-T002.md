---
id: KIKU-T002
type: task
title: Define Stable Recipes, Provenance, and Canonical Products
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [contracts, provenance, identity]
links:
  - ../superpowers/plans/2026-07-12-exceptional-forsterite-pattern.md
---

# KIKU-T002: Define Stable Recipes, Provenance, and Canonical Products

## Description

Define immutable project-owned data contracts and content-derived identities
that do not expose upstream simulator or projection objects.

## Acceptance Criteria

- [ ] Contract tests under `tests/unit/test_identity.py`, `test_recipes.py`, and `test_products.py` pass.
- [ ] Versioned product persistence round-trips data and rejects corrupt evidence.
- [ ] The accepted contract implementation is linked here.
