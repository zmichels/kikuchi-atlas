---
id: KIKU-F022
type: feature
title: Refine held-out Ice Ih detector orientations on the declared partial sphere
status: done
parent: KIKU-E001
children:
  - KIKU-T067
created: 2026-07-21
priority: P1
tags: [ice-ih, dictionary, detector, orientation, local-refinement]
links:
  - ../acceptance/ice-ih-offgrid-detector-refinement.md
evidence:
  - ../../scripts/run_ice_ih_offgrid_detector_refinement.py
---

# KIKU-F022: Refine held-out Ice Ih detector orientations on the declared partial sphere

## Description

Extend the frozen Ice Ih candidate cache with a project-owned local refinement
primitive that keeps the detector-derived S2 coverage mask explicit. Prove its
behavior on deliberately off-grid synthetic detector orientations, rather than
only cache entries that can recover themselves exactly.

## Acceptance Criteria

- [x] Local candidates preserve the active crystal-to-sample quaternion
  convention and are scored only across the supplied covered directions.
- [x] A unit test confirms that held-out detector-derived evidence improves
  upon its coarse orientation seed without silently promoting to full-S2.
- [x] A checksum-bearing local bundle stores three off-grid detector inputs,
  masks, cache records, refined quaternions, errors, and a readable visual
  sheet.

## Completion Evidence

The three held-out views improve from coarse errors of 3.069, 0.823, and 3.069
degrees to 0.346, 0.528, and 0.412 degrees, respectively. The acceptance
record retains the synthetic-only and camera-specific boundaries.
