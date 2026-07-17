---
id: KIKU-T035
type: task
title: Validate and export relief globe meshes
status: done
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- mesh-validation
- export
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
- ../../tests/unit/relief/test_relief_mesh.py
- ../acceptance/spherical-intensity-relief-globe.md
---

# KIKU-T035: Validate and export relief globe meshes

## Description

Validate the unchanged indexed radial mesh with a relief-specific star-shaped
certificate and emit deterministic STL, field-ledger NPZ, validation JSON,
and fixed visual preview artifacts without silent repair.

## Acceptance Criteria

- [x] Validation proves one watertight, consistently wound, positive-volume Euler-2 body with no duplicate or degenerate faces and a positive radial certificate for every triangle.
- [x] Invalid topology, radius, winding, degeneracy, and radial-projection cases fail without mutating or repairing inputs; FDM metrics remain advisory data only.
- [x] STL, timestamp-fixed uncompressed NPZ, validation data, and the fixed full-mesh PNG preview are reproducible and preserve exact units and array contracts.
