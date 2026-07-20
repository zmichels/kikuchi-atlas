---
id: KIKU-T042
type: task
title: Normalize individual Atlas products and publish relational browsing
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, product-catalog, static-site, provenance]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
  - ../products/ARTIFACT_CATALOG.yml
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../scripts/build_atlas.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T042: Normalize individual Atlas products and publish relational browsing

## Description

Replace the bundle-level Atlas view with a curated individual-product registry.
The Atlas must support both phase-first and product-first browsing, preserve
many-to-many phase/product-family relations, and show a fixed product matrix so
one phase is not accidentally represented by a different visual treatment.

## Acceptance Criteria

- [x] Individual SVG, MP4, and STL products are tracked as curated release records with direct-media, bundle, and provenance links where available.
- [x] Every source-backed phase has the same four core product families represented: direct-reflector template, orientation variation, x-axis motion, and reflector-ridge globe.
- [x] Phase cards use comparable direct-reflector lead thumbnails instead of mixing a dynamical master with an idealized band plot.
- [x] The static site has a product-first page that filters individual products by phase, family, medium, and text.
- [x] Candidate phases show the same matrix with source-promotion status instead of a misleading empty product type.
- [x] Tests cover registry relations, comparable lead selections, product-page controls, and correct phase-page linking.
