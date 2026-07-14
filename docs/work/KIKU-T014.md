---
id: KIKU-T014
type: task
title: Adapt Forsterite Phase and Reflections to Kikuchipy
status: ready
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [diffsims, phase, reflections, provenance]
evidence:
  - ../../phases/forsterite/source.yml
---

# KIKU-T014: Adapt Forsterite Phase and Reflections to Kikuchipy

## Description

Build the standard-Pnma orix phase from the canonical tracked source and wrap
diffsims reflection enumeration, factors, angles, and selection as plain data.

## Acceptance Criteria

- [ ] The Pbnm-to-Pnma basis transform matches the existing verified simulation view.
- [ ] The adapter uses public diffsims APIs and does not leak upstream objects into durable contracts.
- [ ] Every retained reflector records indices, spacing, factor magnitude, angle, and selection provenance.
