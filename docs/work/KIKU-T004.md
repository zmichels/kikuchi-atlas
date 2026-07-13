---
id: KIKU-T004
type: task
title: Implement the kikuchipy Projection Boundary
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [kikuchipy, detector, orientation]
evidence:
  - ../../tests/adapters/test_kikuchipy_projection.py
  - ../../tests/scientific/test_projection_invariants.py
  - ../../src/kikuchi_lab/projection/kikuchipy_adapter.py
---

# KIKU-T004: Implement the kikuchipy Projection Boundary

## Description

Project canonical master patterns through explicit orientation-frame and
detector-geometry contracts while containing kikuchipy types in one adapter.

## Acceptance Criteria

- [ ] `tests/adapters/test_kikuchipy_projection.py` proves orientation inversion and detector mapping.
- [ ] Projection output is a canonical detector-pattern product with source identities.
- [ ] Geometry diagnostics and accepted adapter evidence are linked here.
