---
id: KIKU-T046
type: task
title: Separate core and extension products on Atlas phase pages
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, visual-hierarchy, product-families]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T046: Separate core and extension products on Atlas phase pages

## Description

Give the visual matrix, coverage table, and individual-product library an
explicit core-versus-extension hierarchy. The distinction must use the
registry's authoritative product-family coverage field, rather than a visual
guess or title convention.

## Acceptance Criteria

- [x] Visual matrix cells are grouped into clearly labeled core and extension sections.
- [x] Coverage-table rows are separated by the same authoritative grouping.
- [x] Individual product cards are grouped by core versus extension without duplicate cards.
- [x] Candidate-source phase pages retain both groups and their transparent planned state.
- [x] Unit tests, Atlas generation, and tracker validation pass.

## Completion Evidence

- All grouping is calculated from the authoritative `coverage` field in the
  product-family registry.
- Both the visual matrix and the coverage table render core followed by
  extension; product cards render once under the same hierarchy.
- `pytest tests/unit/test_atlas.py -q`, `ruff check`, the Atlas build, and
  work-item validation passed.
