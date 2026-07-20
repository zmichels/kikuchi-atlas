---
id: KIKU-T044
type: task
title: Expand Atlas visual highlights and remove tattoo catalog products
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, visuals, catalog-curation]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T044: Expand Atlas visual highlights and remove tattoo catalog products

## Description

Make phase pages visually useful before the product matrix by presenting a
small selection of actual local product previews. Remove tattoo-template
products and terminology from the Atlas registry and generated publication;
the source artwork remains an unmodified local historical artifact outside the
curated Atlas.

## Acceptance Criteria

- [x] The Atlas registry contains no tattoo product family, product identifier, title, caption, or family tag.
- [x] Each source-backed phase page has a concise visual-highlights section drawn from actual available products.
- [x] Product counts, phase heroes, matrix rows, filters, docs, and generated pages stay internally consistent after curation.
- [x] Unit tests and tracker validation cover the revised visual publication contract.

## Completion Evidence

- `python scripts/build_atlas.py` generated nine phase pages and 46 curated individual products.
- `pytest tests/unit/test_atlas.py -q` passed with phase-highlight and removal assertions.
- `ruff check src/kikuchi_lab/atlas tests/unit/test_atlas.py` and
  `python scripts/validate_work_items.py` passed.
