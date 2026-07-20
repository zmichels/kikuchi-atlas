---
id: KIKU-F007
type: feature
title: Dense retained-field phase masters for Titanite and Zircon
status: active
parent: KIKU-E001
children:
  - KIKU-T038
created: 2026-07-19
priority: P1
tags: [phase-general, kinematical, intensity, retained-field, science-art, animation]
links:
  - ../acceptance/ice-ih-near-depth-stepped.md
  - ../acceptance/titanite-zircon-retained-near-depth.md
evidence:
  - ../../recipes/kinematical/titanite-quiet-master.yml
  - ../../recipes/kinematical/zircon-quiet-master.yml
  - ../../recipes/presentation/titanite-near-depth-stepped-band-led.yml
  - ../../recipes/presentation/zircon-near-depth-stepped-band-led.yml
  - ../acceptance/titanite-zircon-retained-near-depth.md
---

# KIKU-F007: Dense retained-field phase masters for Titanite and Zircon

## Description

Add a deliberately distinct, retained-field companion to the direct-reflector
art family. Each phase gets one provenance-bearing two-hemisphere
kinematical master plus an intensity-weighted, presentation-only near-depth
field. Those saved fields—not flattened images—are the reusable inputs for
active orientation and x-axis rotation exports.

## Acceptance Criteria

- [x] Titanite and zircon source records each drive one verified 1025-square, two-hemisphere kinematical master.
- [x] Each retained master has a matching no-blur, band-led near-depth static derivative with its exact overlap array and manifest.
- [x] Each saved field produces a 12-second active x-axis animation without recalculating diffraction per frame or spinning a flattened raster.
- [x] Outputs state that they are kinematical, presentation-only science art rather than detector acquisitions or dynamical master patterns.
- [x] Recipes, manifests, focused tests, work tracking, and encoded-media verification are retained locally.

## Review State

The engineering and provenance slice is complete. The feature remains active
for human visual review, matching the convention used by the direct-reflector
family.
