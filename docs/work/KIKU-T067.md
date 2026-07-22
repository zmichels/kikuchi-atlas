---
id: KIKU-T067
type: task
title: Implement and render masked local detector refinement
status: done
parent: KIKU-F022
created: 2026-07-21
priority: P1
tags: [ice-ih, detector-to-s2, local-search, orientation, verification]
links:
  - ../acceptance/ice-ih-offgrid-detector-refinement.md
evidence:
  - ../../src/kikuchi_lab/dictionary/detector_to_s2.py
  - ../../tests/unit/test_detector_to_s2_adapter.py
---

# KIKU-T067: Implement and render masked local detector refinement

## Description

Build the bounded local SO(3) search that starts from a coarse cache winner,
resamples the raw master, and applies the exact observed detector coverage mask
to every local candidate. Package a source-bound off-grid proof and its
visual evidence.

## Acceptance Criteria

- [x] The refinement rejects invalid local-grid settings and a non-unit center
  quaternion.
- [x] It uses the existing masked candidate metric, preserving the detector
  coverage constraint during refinement.
- [x] The held-out proof confirms every truth is absent from the coarse cache
  and fails loudly if refinement does not improve the coarse angular result.

## Completion Evidence

Focused unit tests cover a small declared detector geometry and demonstrate
improvement from 2.5 to less than 1.2 degrees on a held-out orientation. The
full Ice Ih proof renders three native detector fields and their coarse-to-
refined evidence without acquired-data claims.
