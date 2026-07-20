---
id: KIKU-F003
type: feature
title: Spherical intensity and MTEX density bridge
status: ready
parent: KIKU-E001
children:
  - KIKU-T019
  - KIKU-T020
  - KIKU-T021
  - KIKU-T022
  - KIKU-T023
  - KIKU-T024
  - KIKU-T027
created: 2026-07-13
priority: P1
tags: [spherical-intensity, mtex, density, forsterite]
links:
  - ../superpowers/specs/2026-07-13-spherical-intensity-and-mtex-density-design.md
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
evidence:
  - ../incubator/interactive-spherical-view.md
  - ../incubator/texture-weighted-spherical-intensity.md
---

# KIKU-F003: Spherical intensity and MTEX density bridge

## Description

Export the `KIKU-F002` both-hemisphere stereographic master as an exact-node
directional scalar field on S2, an explicitly validated axial derivative, and
a bounded MTEX 6.1.1 density/3D visualization bundle.

## Acceptance Criteria

- [ ] All seven implementation tasks have accepted evidence and `KIKU-F002` is complete.
- [ ] The forsterite field preserves exact source-node geometry and raw intensity with explicit seam, antipodal, and no-blur semantics.
- [ ] One bounded MTEX acceptance run reproduces source nodes within tolerance and emits a reviewed density cloud and 3D preview.
