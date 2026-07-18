---
id: KIKU-T037
type: task
title: Add diamond direct-reflector art templates and x-axis rotation
status: done
parent: KIKU-F006
depends_on:
  - KIKU-T034
created: 2026-07-18
priority: P1
tags: [diamond, reflectors, tattoo, vector, rotation, animation]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
evidence:
  - ../../phases/diamond/source.yml
  - ../../recipes/reflectors/diamond-art-bands.yml
  - ../../local/phase-general-direct-reflector-art/diamond-catalog-v1/direct-art-catalog-run-065cf8629d81ea13/manifest.json
  - ../../local/phase-general-direct-reflector-art/exports/diamond-rotated-tattoo-templates-v1/diamond-hemisphere-standard-run-9b89c88619fe53e8/manifest.json
  - ../../local/phase-general-direct-reflector-art/exports/diamond-x-axis-rotation-v1/manifest.json
---

# KIKU-T037: Add diamond direct-reflector art templates and x-axis rotation

## Description

Add diamond as a provenance-bearing direct-reflector phase, then reuse the
approved standard-width active Bunge variants to publish print templates and a
saved-selection x-axis animation. The product remains zero-master science art:
the animation actively rotates reflector normals, not a rendered image.

## Acceptance Criteria

- [x] A verified cubic `F d -3 m` diamond source records the required COD-to-diffpy origin translation and retains source hashes.
- [x] A direct-reflector catalog has at least eleven eligible bands with no master-pattern simulation.
- [x] Standard plus three physically reoriented, standard-width tattoo template bundles retain vector files and provenance snapshots.
- [x] A 12-second x-axis rotation MP4/GIF reuses the saved standard selection and validates after encoding.
- [x] Focused tests, Ruff, tracker validation, and retained-product checks pass.
