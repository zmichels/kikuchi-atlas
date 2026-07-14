---
id: KIKU-F002
type: feature
title: Kikuchipy kinematical reference products
status: done
parent: KIKU-E001
children:
  - KIKU-T013
  - KIKU-T014
  - KIKU-T015
  - KIKU-T016
  - KIKU-T017
  - KIKU-T018
created: 2026-07-13
priority: P0
tags: [kinematical, kikuchipy, forsterite, visualization]
links:
  - ../superpowers/specs/2026-07-13-band-aware-focused-and-diagrammatic-rendering-design.md
  - ../superpowers/plans/2026-07-13-kikuchipy-kinematical-reference-products.md
evidence:
  - ../acceptance/forsterite-milestone.md
  - ../acceptance/kinematical-forsterite.md
  - ../../recipes/kinematical/forsterite-etched-master.yml
  - ../../local/runs/kinematical/kinematical-run-d1dab780ec480f72/manifest.json
---

# KIKU-F002: Kikuchipy kinematical reference products

## Description

Expose kikuchipy's existing stereographic, spherical, Lambert-master, and
detector-projected kinematical capabilities as deterministic project products
before deciding whether a custom dynamical/kinematical hybrid is warranted.

## Acceptance Criteria

- [x] All six implementation tasks have accepted evidence.
- [x] A cited forsterite recipe reproduces the selected orientation in every projection.
- [x] Reflection selection and coordinate conventions are explicit and inspectable.
- [x] Native-scale figures establish a durable visual decision gate for later hybrid work.
