---
id: KIKU-T030
type: task
title: Publish Ice Ih relief globe
status: ready
parent: KIKU-F005
created: 2026-07-16
priority: P1
tags: [ice-ih, science-art, globe, mesh, fabrication]
links:
  - ../superpowers/specs/2026-07-16-ice-art-globe-and-tattoo-design.md
  - ../superpowers/plans/2026-07-16-ice-relief-globe.md
evidence:
  - ../superpowers/plans/2026-07-16-ice-relief-globe.md
---

# KIKU-T030: Publish Ice Ih relief globe

## Description

Convert shared catalog cohorts into reference-density and fine watertight Ice Ih
relief spheres in the canonical crystal frame, using maximum-tier overlap and a
bounded geometric shoulder without raster resampling or spatial filtering.

## Acceptance Criteria

- [ ] The radial field occupies the background plus four cohort tiers, stays within 68-75 mm, and never adds intersection height.
- [ ] Reference and fine welded sphere topologies meet exact count, winding, manifold, connectivity, and self-intersection checks.
- [ ] Binary STL, fine GLB, fixed diagnostics, recipes, catalog, ledgers, validation report, and manifest publish atomically.
- [ ] Fabrication warnings remain separate from hard geometry validation and the user reviews the rotatable proof before closure.
