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
- [ ] Two independent full-resolution builds are identical, the retained `501 x 501` forsterite source passes mesh and slicer inspection, and all repository gates remain green.

The reproducibility, retained-source mesh inspection, and repository gates passed. Flash Studio
1.7.11 exposes no discovered safe noninteractive slicer seam, so slicer-native inspection remains
unobserved and is recorded as a concern in the acceptance report.
