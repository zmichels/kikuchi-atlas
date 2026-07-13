---
id: KIKU-T002
type: task
title: Define Stable Recipes, Provenance, and Canonical Products
status: done
parent: KIKU-F001
created: 2026-07-12
started: 2026-07-12
completed: 2026-07-12
priority: P0
tags: [contracts, provenance, identity]
links:
  - ../superpowers/plans/2026-07-12-exceptional-forsterite-pattern.md
  - ../../src/kikuchi_lab/model/products.py
  - ../../src/kikuchi_lab/model/persistence.py
evidence:
  - ../../tests/unit/test_identity.py
  - ../../tests/unit/test_recipes.py
  - ../../tests/unit/test_products.py
  - ../../tests/unit/test_persistence.py
---

# KIKU-T002: Define Stable Recipes, Provenance, and Canonical Products

## Description

Define immutable project-owned data contracts and content-derived identities
that do not expose upstream simulator or projection objects.

## Acceptance Criteria

- [x] Contract tests under `tests/unit/test_identity.py`, `test_recipes.py`, and `test_products.py` pass.
- [x] Versioned product persistence round-trips data and rejects corrupt evidence.
- [x] The accepted contract implementation is linked here.

## Completion Evidence

- `uv run pytest tests/unit/test_identity.py tests/unit/test_recipes.py tests/unit/test_products.py tests/unit/test_persistence.py -q`: 35 passed.
- `uv run pytest tests/unit -q`: 41 passed.
- `uv run ruff check src tests`: all checks passed.
- `uv run python scripts/validate_work_items.py`: tracker validation passed.
- Follow-up contract review gate: focused suite 58 passed and full fast/unit
  suite 64 passed after complete scientific metadata, byte-backed array
  immutability, and fraction-only PC convention checks were added.
