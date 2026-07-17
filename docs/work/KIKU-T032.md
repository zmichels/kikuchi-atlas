---
id: KIKU-T032
type: task
title: Extract phase-general direct-reflector evidence
status: ready
parent: KIKU-F006
created: 2026-07-16
priority: P1
tags: [reflectors, structure-factor, parity, finite-work]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
evidence:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
---

# KIKU-T032: Extract phase-general direct-reflector evidence

## Description

Promote the adapter's pre-master reflector calculation into an owned,
orientation-independent evidence contract and decouple art-band catalog
construction from dense raster-backed presentation state.

## Acceptance Criteria

- [ ] Direct evidence retains canonical HKLs, crystal normals, d-spacings, Bragg angles, structure factors, weights, calculation policy, and provenance.
- [ ] Ice Ih and forsterite pass numeric parity against the simulator's pre-master reflector boundary.
- [ ] Normal production catalog generation performs zero master-pattern calculations and reports bounded finite work.
- [ ] Catalog and calculation identities are deterministic and exclude orientation-only or rendering-only inputs.
