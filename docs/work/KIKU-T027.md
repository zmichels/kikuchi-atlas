---
id: KIKU-T027
type: task
title: Solve labeled convex crystal habits
status: ready
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- scipy
- halfspace
- topology
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T027: Solve labeled convex crystal habits

## Description

Intersect labeled crystallographic half-spaces into one bounded convex polygon
mesh, preserve inactive planes, scale explicitly, and triangulate deterministically.

## Acceptance Criteria

- [ ] Analytic cube and invalid/unbounded fixtures prove solver and failure behavior.
- [ ] Quartz produces 32 vertices, 18 visible polygon faces, and 12 labeled inactive planes before MTEX parity comparison.
- [ ] Every triangle maps back to one outward-oriented labeled polygon face.
