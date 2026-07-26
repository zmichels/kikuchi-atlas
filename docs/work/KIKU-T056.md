---
id: KIKU-T056
type: task
title: Publish a 4K quartz direct-reflector artist rotation bonus
status: done
parent: KIKU-F006
depends_on:
  - KIKU-T034
created: 2026-07-21
priority: P1
tags: [quartz, reflectors, rotation, animation, artist-master, video]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
evidence:
  - ../../scripts/render_direct_reflector_rotation.py
  - ../../local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/manifest.json
  - ../acceptance/quartz-artist-master.md
---

# KIKU-T056: Publish a 4K quartz direct-reflector artist rotation bonus

## Description

Publish an edit-friendly, seamless alpha-quartz direct-reflector animation for
downstream video art. Reuse the accepted direct-reflector catalog and saved standard selection,
actively rotate the crystallographic normals through one x-axis revolution,
and preserve the direct-reflector science-art claim boundary.

The requested edition doubles the earlier quartz export's frame rate from 12
to 24 fps, doubles its duration from 12 to 24 seconds, and increases its square
frame from 1024 to 4096 pixels. The resulting angular speed is one-half of the
earlier export's speed.

## Acceptance Criteria

- [x] The renderer exposes a reusable artist-master export profile and resumable parallel frame generation.
- [x] The full-resolution source sequence contains 576 distinct 4096 x 4096 PNG frames rendered at 2x supersampling.
- [x] A 24 fps, 24-second ProRes 422 HQ editing master decodes cleanly and records exact media properties and hashes.
- [x] A practical H.264 viewing copy decodes cleanly and records exact media properties and hashes.
- [x] The first frame and loop closure are pixel-identical, and representative frames pass visual review.
- [x] Focused tests, Ruff, work-item validation, product-catalog validation, and whitespace checks pass.
