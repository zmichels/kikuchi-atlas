---
id: KIKU-T036
type: task
title: Build and accept atomic relief globe bundles
status: ready
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- workflow
- acceptance
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
- ../../tests/integration/test_relief_globe_workflow.py
- ../acceptance/spherical-intensity-relief-globe.md
---

# KIKU-T036: Build and accept atomic relief globe bundles

## Description

Compose source verification, spherical mapping, canonical topology, filtering,
geometry, validation, and export into one content-addressed atomic build and
record real forsterite acceptance without claiming an unperformed print.

## Acceptance Criteria

- [x] The nested CLI produces exactly one five-file atomic bundle or removes partial output and returns a concise failure without traceback.
- [x] Build identity and manifest inventory include recipe, source, mapping, topology, filter, validation, runtime versions, file hashes, byte sizes, and millimetre units.
- [x] Two independent full-resolution builds are identical, the retained `501 x 501` forsterite source passes canonical and processed-round-trip mesh inspection, and all repository gates remain green.
- [ ] Human Flash Studio GUI inspection records the retained STL as one unmodified solid without repair warnings.

The reproducibility, retained-source mesh inspection, and repository gates passed. Flash Studio
1.7.11 exposes no discovered safe noninteractive slicer seam, so slicer-native inspection remains
unobserved and is recorded as the sole concern in the acceptance report. `KIKU-T036` remains open
only for that external GUI inspection.
