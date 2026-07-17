---
id: KIKU-T028
type: task
title: Validate and export printable triangle meshes
status: done
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- mesh
- stl
- validation
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T028: Validate and export printable triangle meshes

## Description

Validate the derived triangle mesh without repair, emit deterministic binary
STL bytes and a fixed labeled preview, and report advisory FDM observations.

## Acceptance Criteria

- [x] Validation proves one convex watertight consistently wound positive-volume body with no duplicate or degenerate triangles.
- [x] Trimesh runs with `process=False`, and a deliberately broken mesh is rejected without mutation.
- [x] STL bytes and the fixed 900-by-900 PNG preview reproduce exactly from identical geometry.

## Accepted Evidence

- `src/kikuchi_lab/habit/mesh.py` and
  `tests/unit/habit/test_habit_mesh.py`.
- [Crystal habit acceptance ledger](../acceptance/crystal-habit-mesh.md) links
  the immutable validation report, STL, and labeled preview.
