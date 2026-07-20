---
id: KIKU-T034
type: task
title: Publish five-phase standard and wide art family
status: active
parent: KIKU-F006
depends_on:
  - KIKU-T032
  - KIKU-T033
created: 2026-07-16
priority: P1
tags: [orientation, great-circle, vector, tattoo, gallery]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
  - ../superpowers/plans/2026-07-16-phase-general-direct-reflector-art-series.md
evidence:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
  - ../acceptance/phase-general-direct-reflector-art-series.md
---

# KIKU-T034: Publish five-phase standard and wide art family

## Description

Apply one configurable active crystal-to-sample Bunge orientation to the five
phase catalogs, freeze deterministic 11-band selections, and publish four new
standard plus five new 15-percent-wider complete hemisphere-art bundles and a
ten-cell comparison sheet.

## Acceptance Criteria

- [x] All first-series compositions use active crystal-to-sample Bunge ZXZ `(17, 31, 43)` degrees through recipe data rather than phase-specific code.
- [x] Each phase pair shares exactly the same selected reflector IDs and centerline coordinates, with only crystallographic widths scaled by `1.15` and the 2.20 mm boundary unchanged.
- [x] Nine new SVG, PDF, PNG, geometry, recipe, catalog, provenance, validation, and manifest bundles publish atomically and deterministically.
- [x] The reviewed Ice Ih standard-reference bundle is referenced without modification, and the labeled ten-cell comparison sheet is retained for user review.

## Review State

Scientific, computational, retention, and native-resolution inspection gates
are complete. The work item remains active only for the user's aesthetic
preference review of the standard/wide comparison.
