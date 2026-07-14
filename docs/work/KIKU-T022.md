---
id: KIKU-T022
type: task
title: Generate portable exact-node MTEX script
status: done
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [mtex, matlab, s2funtri, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
  - ../../src/kikuchi_lab/spherical_intensity/mtex_script.py
  - ../../src/kikuchi_lab/spherical_intensity/bundle.py
  - ../../tests/unit/test_spherical_intensity_mtex_script.py
  - ../../tests/unit/test_spherical_intensity_bundle.py
---

# KIKU-T022: Generate portable exact-node MTEX script

## Description

Generate deterministic, machine-path-neutral MATLAB source for exact-node
`S2FunTri`, 3D plots, density sampling, and flushed stage evidence.

## Acceptance Criteria

- [x] The script rejects duplicate directional nodes and validates exact-node interpolation within `1e-8`.
- [x] Density sampling fixes and restores RNG state, writes atomic derivatives, and never uses marker-alpha waits.
- [x] Script bytes contain no absolute local path and are deterministic for one recipe/profile.

## Verification

- TDD RED: the focused script suite failed at collection because the public
  `generate_mtex_script` module/API did not exist.
- Generator and bundle suite: `80 passed`, covering deterministic LF-only
  source, path neutrality, exact directional/optional-axial semantics, stage
  heartbeats, atomic output names, and registered script bytes/hash.
- Contract, scientific mapping, orix adapter, artifact, and persistence
  regression: `140 passed`.
- MATLAB/MTEX was deliberately not invoked in this source-generation task.
