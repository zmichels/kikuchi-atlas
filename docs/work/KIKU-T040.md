---
id: KIKU-T040
type: task
title: Define the Atlas registry and generate local browse pages
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [atlas, static-site, phase-catalog]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../scripts/build_atlas.py
  - ../../tests/unit/test_atlas.py
---

# KIKU-T040: Define the Atlas registry and generate local browse pages

## Description

Build the first data-first Atlas view from the stable product catalog and a
phase registry. The rendered pages are a local browser surface only; source
records, recipes, and manifests remain canonical.

## Acceptance Criteria

- [x] The registry contains every cataloged phase and preserves each product's tier boundary.
- [x] The static builder produces an index and individual phase pages without an external website framework.
- [x] Tests cover the candidate/verified state distinction, generated page count, and local product links.
