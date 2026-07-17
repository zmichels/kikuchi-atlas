---
id: KIKU-F004
type: feature
title: Crystal habit mesh generator
status: done
parent: KIKU-E001
children:
- KIKU-T025
- KIKU-T026
- KIKU-T027
- KIKU-T028
- KIKU-T029
- KIKU-T030
created: 2026-07-17
priority: P1
tags:
- crystal-habit
- mesh
- stl
- mtex
- print-geometry
links:
- ../superpowers/specs/2026-07-17-crystal-habit-mesh-generator-design.md
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
evidence:
- ../incubator/print-geometry.md
---

# KIKU-F004: Crystal habit mesh generator

## Description

Generate arbitrary convex crystal-habit meshes from a CIF and explicit Miller
face-family support distances through a Python-native, unit-aware, validated
pipeline, with quartz as the first MTEX-referenced watertight STL proof.

## Acceptance Criteria

- [x] An arbitrary conforming CIF and habit recipe can enter the Python-native pipeline without quartz-specific geometry code.
- [x] The quartz reference produces a reproducible, watertight, single-solid STL with a `60.0 mm` maximum dimension and complete provenance.
- [x] Quartz polygon geometry passes the reviewed MTEX parity contract.
- [x] Canonical validation rejects invalid solids and reports inactive faces and FDM observations without silently modifying geometry.
- [x] Existing milestone products and acceptance criteria remain unchanged.

## Accepted Evidence

- Child tasks [KIKU-T025](KIKU-T025.md) through
  [KIKU-T030](KIKU-T030.md) are complete against tests and generated evidence.
- [Crystal habit acceptance ledger](../acceptance/crystal-habit-mesh.md) links
  bundle `habit-build-2a7cd569e2ec19d6`, validation, parity, preview, STL, and
  the FlashForge AD5X-oriented slicer observation.
- `KIKU-F001` through `KIKU-F003` were not changed by this feature closure.
