---
id: KIKU-T019
type: task
title: Define spherical intensity contracts and profiles
status: done
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [contracts, recipes, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
  - ../../recipes/spherical/forsterite-s2-intensity.yml
  - ../../src/kikuchi_lab/spherical_intensity/contracts.py
  - ../../src/kikuchi_lab/spherical_intensity/recipe.py
  - ../../tests/unit/test_spherical_intensity_contracts.py
---

# KIKU-T019: Define spherical intensity contracts and profiles

## Description

Add immutable directional and axial field contracts plus strict smoke and
acceptance recipes for the bounded forsterite proof.

## Acceptance Criteria

- [x] Directional and axial arrays are typed, immutable, finite, hash-addressed, and plain-data described.
- [x] The recipe fixes all density, tolerance, RNG, serialization, and MTEX-version semantics.
- [x] Only the `32` smoke and `128` acceptance half-size profiles are accepted.
