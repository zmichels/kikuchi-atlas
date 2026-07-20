---
id: KIKU-T050
type: task
title: Extend source-backed phase parity with intensity and relief studies
status: ready
parent: KIKU-F011
created: 2026-07-20
priority: P2
tags: [atlas, intensity, depth, relief, phase-parity]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
evidence:
  - ../../src/kikuchi_lab/spherical_intensity
  - ../../src/kikuchi_lab/reflector_globe
---

# KIKU-T050: Extend source-backed phase parity with intensity and relief studies

## Description

Add intensity-master, depth-field motion, and intensity-relief products only
where each phase has a stated field model and geometry recipe. These are
extension products, not requirements for core direct-reflector parity.

## Acceptance Criteria

- [ ] Each extension binds to an explicit source field/model and phase recipe.
- [ ] Atlas coverage and claim boundaries distinguish direct-reflector, intensity, and print-geometry tiers.
- [ ] Missing extensions stay explicitly planned rather than being derived from unrelated phase media.
