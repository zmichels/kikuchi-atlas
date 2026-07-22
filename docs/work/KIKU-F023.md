---
id: KIKU-F023
type: feature
title: Expose Ice Ih detector dictionary sensitivity to declared projection center
status: done
parent: KIKU-E001
children:
  - KIKU-T068
created: 2026-07-21
priority: P1
tags: [ice-ih, detector, projection-center, calibration, dictionary]
links:
  - ../acceptance/ice-ih-projection-center-sensitivity.md
evidence:
  - ../../scripts/run_ice_ih_projection_center_sensitivity.py
---

# KIKU-F023: Expose Ice Ih detector dictionary sensitivity to declared projection center

## Description

Use the checked simulated Ice Ih detector field to make the current
detector-to-S2 adapter's geometric dependency visible. Publish a bounded PCx/
PCy perturbation map that retains scores, coarse winners, angular errors, and
coverage changes rather than presenting a geometry-free rank claim.

## Acceptance Criteria

- [x] The offset grid must be finite, ordered, and retain the zero-offset
  source-declared geometry.
- [x] Each grid cell must recompute both the camera footprint and masked
  candidate ranking from the fixed source detector field.
- [x] A checksum-bearing visual bundle makes score, winner error, and covered
  direction count inspectable together with the source detector image.

## Completion Evidence

The 9 x 9 grid returns nominal entry `6577` with zero error at the source
geometry and exposes up to 88.129 degrees of top-entry deviation over the
deliberately broad perturbation grid. The acceptance record states why this
is a sensitivity diagnostic, not a tolerance or calibration claim.
