---
id: KIKU-T045
type: task
title: Add a visual product matrix to Atlas phase pages
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, visuals, matrix, browsing]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T045: Add a visual product matrix to Atlas phase pages

## Description

Give each phase page a compact product-family matrix whose available cells use
actual local thumbnails. Keep the detailed coverage table below it so visual
browsing never hides product counts, missing families, or source-promotion
state.

## Acceptance Criteria

- [x] Every phase page has one visual matrix cell for every registered product family.
- [x] Available cells show source-backed local thumbnails and open their actual product media.
- [x] Multi-product families select non-redundant representatives where possible, while preserving full counts and links below.
- [x] Planned and candidate-source cells remain visually explicit rather than being rendered as fabricated products.
- [x] Unit tests, Atlas generation, and tracker validation pass.

## Completion Evidence

- The Atlas generator renders seven visual product-family cells per phase.
- Direct templates use the lead thumbnail; orientation cells use alternative
  orientations where available, avoiding an immediate duplicate of the lead.
- `pytest tests/unit/test_atlas.py -q`, `ruff check`, the Atlas build, and the
  work-item validation all passed.
