---
id: KIKU-T015
type: task
title: Generate Kinematical Projection Products
status: ready
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [stereographic, lambert, detector, coordinate-ledger]
evidence:
  - ../superpowers/specs/2026-07-13-band-aware-focused-and-diagrammatic-rendering-design.md
---

# KIKU-T015: Generate Kinematical Projection Products

## Description

Generate stereographic master, Lambert master, detector projection, and plain
detector-geometry coordinates through pinned kikuchipy public APIs.

## Acceptance Criteria

- [ ] Adapter arrays match equivalent direct kikuchipy calls exactly.
- [ ] A source/method/coordinate ledger records frames, units, transforms, hemisphere, origin, and spot checks.
- [ ] The selected `[011]` direction passes a recorded detector-frame alignment check.
