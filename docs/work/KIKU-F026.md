---
id: KIKU-F026
type: feature
title: Prove Ice Ih transfer through multiple declared virtual camera geometries
status: done
parent: KIKU-E001
children:
  - KIKU-T073
created: 2026-07-23
priority: P1
tags: [ice-ih, detector-geometry, virtual-camera, transfer, dictionary]
links:
  - ../acceptance/ice-ih-virtual-camera-transfer.md
evidence:
  - ../../src/kikuchi_lab/dictionary/detector_profiles.py
  - ../../scripts/run_ice_ih_virtual_camera_transfer.py
---

# KIKU-F026: Prove Ice Ih transfer through multiple declared virtual camera geometries

## Description

Use one canonical Ice Ih dictionary with three source-bound, named virtual
camera geometries. Generate each detector field from the same raw master,
retain its own S2 coverage mask, and verify known orientations rank first
without making invalid cross-profile score comparisons.

## Acceptance Criteria

- [x] Nominal, wider-field, and narrower-field detector profiles are explicit
  immutable geometry values with clear non-commercial scope.
- [x] Two separated cache orientations recover first for every profile through
  its own raw detector and partial-S2 sampling path.
- [x] A checksum-bearing local bundle and visual sheet show the detector views,
  covered S2 support, per-profile matches, and nonclaims.

## Completion Evidence

The Ice Ih transfer bundle retains 308, 390, and 196 covered directions for
the three profiles and recovers entries `6577` and `15` first in all six
profile/target cases. It demonstrates a named geometry-adapter boundary, not
inter-instrument calibration or acquired-pattern accuracy.
