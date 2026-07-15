---
id: KIKU-T026
type: task
title: Render Ice Ih near-depth stepped presentation proof
status: active
parent: KIKU-F004
created: 2026-07-14
priority: P1
tags: [ice-ih, kinematical, presentation, depth, no-blur]
evidence:
  - ../superpowers/specs/2026-07-14-ice-near-depth-stepped-design.md
  - ../acceptance/ice-ih-near-depth-stepped.md
  - ../../recipes/presentation/ice-ih-near-depth-stepped.yml
  - ../../recipes/presentation/ice-ih-near-depth-stepped-emphasis.yml
  - ../../tests/unit/test_near_depth_recipe.py
  - ../../tests/scientific/test_near_depth_overlap.py
  - ../../tests/unit/test_near_depth_render.py
  - ../../tests/unit/test_near_depth_bundle.py
  - ../../tests/integration/test_ice_near_depth.py
  - ../../local/runs/kinematical-depth-ice/near-depth-run-7744aaa7dcdd20b8/manifest.json
  - ../../local/runs/kinematical-depth-ice-emphasis/near-depth-run-4625b83f045dc1df/manifest.json
---

# KIKU-T026: Render Ice Ih near-depth stepped presentation proof

## Description

Add a separately ledgered presentation derivative of the accepted Ice Ih quiet
master. Genuine multi-band overlap advances through pointwise luminance while
exact symmetric boundary and center paths add crisp stepped relief without
blur, resampling, or a directional shadow.

## Acceptance Criteria

- [x] Exact axial band membership produces a separately inspectable additional-overlap field.
- [x] Optical-depth compositing is pointwise, monotonic, and identical where additional overlap is zero.
- [x] Coincident vector boundary and center casings reproduce the approved symmetric stepped treatment.
- [x] A content-addressed bundle links the treatment to the unchanged Ice source, base recipe, and base product.
- [x] A bounded smoke render passes before one 2400 px review candidate is produced.
- [x] A separately named emphasis recipe strengthens the stepped relief while preserving geometry and the quiet candidate.
- [ ] The user reviews the new candidate before it is promoted beyond presentation-proof status.
