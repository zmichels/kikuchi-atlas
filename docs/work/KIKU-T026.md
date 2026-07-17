---
id: KIKU-T026
type: task
title: Expand crystallographic habit planes
status: ready
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

- [ ] Three- and four-index families validate and produce finite unit reciprocal-plane normals.
- [ ] Quartz point-group `32` expands the five reviewed families into 30 labeled planes without merging `r` and `z`.
- [ ] Downstream products contain only project-owned plain geometry and phase contracts.
