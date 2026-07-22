---
id: KIKU-T068
type: task
title: Render source-bound Ice Ih projection-center sensitivity maps
status: done
parent: KIKU-F023
created: 2026-07-21
priority: P1
tags: [ice-ih, detector-geometry, pc, sensitivity, visualization]
links:
  - ../acceptance/ice-ih-projection-center-sensitivity.md
evidence:
  - ../../scripts/run_ice_ih_projection_center_sensitivity.py
  - ../../tests/unit/test_projection_center_sensitivity.py
---

# KIKU-T068: Render source-bound Ice Ih projection-center sensitivity maps

## Description

Package a deterministic detector-geometry sensitivity probe around the named
source projection center. Validate the grid itself and retain all numerical
arrays needed to reproduce the four-panel visual diagnostic.

## Acceptance Criteria

- [x] Unit tests reject unordered, missing-nominal, undersized, and non-finite
  offset grids.
- [x] The nominal zero-offset cell must recover the source orientation or the
  product fails loudly.
- [x] The local bundle serializes offsets, scores, winning indices, angular
  errors, coverage counts, input identity, figure, and checksums.

## Completion Evidence

Focused tests exercise the grid contract. The generated 9 x 9 product visibly
ties camera-center perturbations to both ranking changes and altered S2
coverage, preserving its synthetic-only boundary.
