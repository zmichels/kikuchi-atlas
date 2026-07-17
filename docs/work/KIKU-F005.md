---
id: KIKU-F005
type: feature
title: Spherical intensity relief globe
status: ready
parent: KIKU-E001
children: []
created: 2026-07-17
priority: P1
tags:
  - spherical-intensity
  - relief
  - mesh
  - stl
  - print-geometry
links:
  - ../superpowers/specs/2026-07-17-spherical-intensity-relief-globe-design.md
evidence:
  - ../incubator/print-geometry.md
  - ../acceptance/forsterite-milestone.md
---

# KIKU-F005: Spherical intensity relief globe

## Description

Generate a deterministic, watertight, star-shaped globe whose outward radial
relief derives from a validated raw both-hemisphere Kikuchi master pattern,
with an `80.0 mm` base diameter, `1.2 mm` maximum relief, explicit spherical
filtering, and complete source-to-mesh provenance.

## Acceptance Criteria

- [ ] Any conforming canonical both-hemisphere master product can enter the relief pipeline without forsterite-specific geometry code.
- [ ] The retained `501 x 501` forsterite master produces a reproducible five-file bundle with the reviewed source, mapping, filter, topology, and runtime identities.
- [ ] The canonical mesh contains exactly `163842` vertices and `327680` triangles, preserves subdivision-7 connectivity, and passes the reviewed radial-projection certificate.
- [ ] The STL is one watertight, consistently wound, positive-volume body with radii in `[40.0, 41.2] mm`, no duplicate or degenerate triangles, and no silent repair.
- [ ] Slicer inspection records one unmodified solid while keeping physical printing, orientation, supports, infill, and material as operator decisions.
- [ ] Existing crystal-habit and forsterite milestone products remain unchanged.
