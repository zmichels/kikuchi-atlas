---
id: KIKU-T034
type: task
title: Map and filter radial relief geometry
status: ready
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- filtering
- radial-geometry
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
---

# KIKU-T034: Map and filter radial relief geometry

## Description

Map raw both-hemisphere intensity through one robust global range, sample it
onto canonical topology, apply a deterministic physical-scale spherical
Gaussian filter, and displace vertices outward without changing connectivity.

## Acceptance Criteria

- [ ] Mapping uses one global `1st` to `99th` percentile range, clamp, and positive gamma before directional interpolation; per-hemisphere normalization is impossible.
- [ ] The `0.8 mm` FWHM, `3 sigma` filter preserves constants, is rotationally invariant, attenuates sub-resolution features, and records deterministic diagnostics.
- [ ] Radial geometry preserves canonical faces and directions exactly and keeps every radius within `[40.0, 41.2] mm` for the canonical recipe.
