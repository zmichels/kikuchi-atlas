---
id: KIKU-T007
type: task
title: Define a Symmetry-Distinct Candidate Set
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [orientation, symmetry, forsterite]
evidence:
  - ../../tests/scientific/test_orientation_candidates.py
  - ../../recipes/proof/forsterite-candidates.yml
  - ../decisions/0002-forsterite-proof-candidate-set.md
---

# KIKU-T007: Define a Symmetry-Distinct Candidate Set

## Description

Define deterministic, crystallographically honest forsterite orientations for
proof comparison without redundant symmetry equivalents.

## Acceptance Criteria

- [ ] Candidate-set tests prove stable ordering and symmetry reduction.
- [ ] Orientations use active crystal-to-sample Bunge Euler angles in degrees.
- [ ] The accepted candidate recipe and reduction evidence are linked here.
