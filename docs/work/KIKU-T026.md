---
id: KIKU-T026
type: task
title: Expand crystallographic habit planes
status: done
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- crystallography
- symmetry
- planes
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T026: Expand crystallographic habit planes

## Description

Parse a conforming CIF at the orix/diffpy boundary and expand each Miller family
into deterministic unit plane normals in the explicit `X||a*, Z||c` frame.

## Acceptance Criteria

- [x] Three- and four-index families validate and produce finite unit reciprocal-plane normals.
- [x] Quartz point-group `32` expands the five reviewed families into 30 labeled planes without merging `r` and `z`.
- [x] Downstream products contain only project-owned plain geometry and phase contracts.

## Accepted Evidence

- `src/kikuchi_lab/habit/crystallography.py` and
  `tests/scientific/habit/test_crystallography.py`.
- The acceptance manifest records the explicit
  `X||a*, Y||cross(c,a*), Z||c` frame and 30 expanded plain-data planes.
