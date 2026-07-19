---
id: KIKU-T038
type: task
title: Render a bounded dynamical-master rotation proof
status: active
parent: KIKU-F003
depends_on:
  - KIKU-T003
created: 2026-07-19
priority: P1
tags: [forsterite, dynamical, master-pattern, rotation, grayscale, animation]
evidence:
  - ../../local/master-patterns/forsterite-proof/COD-9000319-ebsdsim.bundle/COD-9000319-ebsdsim.manifest.json
  - ../../local/dynamical-master-rotation/forsterite-x-axis-proof-v1/manifest.json
---

# KIKU-T038: Render a bounded dynamical-master rotation proof

## Description

Reuse the retained proof-grade forsterite dynamical master as a spherical
intensity field. Render a small active x-axis rotation proof by resampling the
field—not by rotating pixels—and preserve fixed display mapping and source
provenance for visual review before any higher-resolution master run.

## Acceptance Criteria

- [x] A tested renderer inverse-rotates fixed sample-screen directions and samples the stored Lambert master with no diffraction reruns.
- [x] A 24-frame, 512-pixel x-axis MP4/GIF and contact sheet retain the master identity, source checksums, rotation contract, and fixed grayscale mapping.
- [x] The proof is labeled as proof-grade dynamical-master art, not a detector acquisition or a new final-quality master.
- [x] Focused tests, lint, source-manifest validation, and tracker validation pass before visual review.
- [ ] User visually reviews the retained proof and decides whether a new higher-resolution master is justified.
