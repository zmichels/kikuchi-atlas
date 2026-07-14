---
id: KIKU-T022
type: task
title: Generate portable exact-node MTEX script
status: ready
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [mtex, matlab, s2funtri, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
---

# KIKU-T022: Generate portable exact-node MTEX script

## Description

Generate deterministic, machine-path-neutral MATLAB source for exact-node
`S2FunTri`, 3D plots, density sampling, and flushed stage evidence.

## Acceptance Criteria

- [ ] The script rejects duplicate directional nodes and validates exact-node interpolation within `1e-8`.
- [ ] Density sampling fixes and restores RNG state, writes atomic derivatives, and never uses marker-alpha waits.
- [ ] Script bytes contain no absolute local path and are deterministic for one recipe/profile.
