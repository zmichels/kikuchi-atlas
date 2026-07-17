---
id: KIKU-T036
type: task
title: Publish five-phase standard-width orientation gallery
status: active
parent: KIKU-F006
depends_on:
  - KIKU-T032
  - KIKU-T034
created: 2026-07-17
priority: P1
tags: [orientation, great-circle, vector, gallery, direct-reflector]
links:
  - ../superpowers/specs/2026-07-17-five-phase-standard-orientation-gallery-design.md
  - ../superpowers/plans/2026-07-17-five-phase-standard-orientation-gallery.md
evidence:
  - ../superpowers/specs/2026-07-17-five-phase-standard-orientation-gallery-design.md
---

# KIKU-T036: Publish five-phase standard-width orientation gallery

## Description

Use retained zero-master direct-reflector evidence and passing parity reports
to publish three physically rotated, standard-width hemisphere views for each
of five phases. Each orientation must resolve a real geometry-valid selection;
no output may be a camera or raster-only rotation.

## Acceptance Criteria

- [ ] A tracked recipe records exactly three distinct active
  crystal-to-sample Bunge orientations and all fifteen phase-orientation cells.
- [ ] Each cell passes deterministic bounded standard-width selection and
  geometry feasibility against its real direct-reflector catalog.
- [ ] Fifteen white-background PNG/SVG products and a labeled comparison sheet
  publish atomically with zero master-pattern simulations.
- [ ] Every output retains selection, geometry, orientation, source catalog,
  parity, command, and checksum provenance for independent reproduction.
- [ ] Focused and full verification pass, then the retained comparison is
  presented for user visual review.
