---
id: KIKU-T047
type: task
title: Combine direct-reflector and orientation visual matrix cells
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, visual-hierarchy, orientation]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T047: Combine direct-reflector and orientation visual matrix cells

## Description

The direct-reflector and orientation-variation families overlap in the current
release: the same direct templates commonly satisfy both. Combine them only in
the visual matrix as one balanced orientation-set tile, while retaining their
distinct relational rows in the coverage table and product registry.

## Acceptance Criteria

- [x] The visual matrix has one combined direct-reflector orientation tile rather than two overlapping tiles.
- [x] The combined tile uses a balanced four-thumbnail orientation presentation where four canonical variants exist.
- [x] Wide-band or other remaining direct-template variants remain discoverable in the individual-product library.
- [x] Core and extension visual groups use a stable three-column presentation at desktop width and remain responsive.
- [x] Unit tests, Atlas generation, and tracker validation pass.

## Completion Evidence

- The visual matrix combines the two overlapping core family cells but leaves
  the normalized registry, coverage table, and individual-product library
  intact.
- Four canonical views are shown in a 2×2 thumbnail grid; the remaining
  direct-template product is named in the card and available below.
- `pytest tests/unit/test_atlas.py -q`, `ruff check`, the Atlas build, and
  work-item validation passed.
