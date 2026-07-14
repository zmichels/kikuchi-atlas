---
id: KIKU-T020
type: task
title: Map stereographic masters onto S2
status: ready
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [orix, geometry, antipodal, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
---

# KIKU-T020: Map stereographic masters onto S2

## Description

Map valid source pixels through public orix geometry while separating seam,
directional, antipodal, and optional axial semantics.

## Acceptance Criteria

- [ ] Geometry-defined disk and upper-owned equator invariants pass without consulting intensity values.
- [ ] Public-orix cardinal and round-trip checks pass at the fixed tolerances.
- [ ] Seam and antipodal diagnostics use their distinct index rules, and non-centrosymmetric values are never silently folded.
