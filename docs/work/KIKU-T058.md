---
id: KIKU-T058
type: task
title: Publish identity and oblique quartz near-depth artist masters
status: done
parent: KIKU-F014
created: 2026-07-21
priority: P1
tags: [quartz, near-depth, grayscale, rotation, orientation, video-art]
links:
  - ../acceptance/quartz-near-depth-artist-pair.md
evidence:
  - ../../scripts/render_retained_near_depth_rotation.py
  - ../../local/idealized-near-depth-rotation/quartz-identity-4k-24fps-24s-v1/manifest.json
  - ../../local/idealized-near-depth-rotation/quartz-oblique-17-31-43-4k-24fps-24s-v1/manifest.json
  - ../../local/idealized-near-depth-rotation/quartz-artist-pair-v1/identity-left-oblique-right.png
---

# KIKU-T058: Publish identity and oblique quartz near-depth artist masters

## Description

Correct the intended visual treatment for the quartz video-art handoff: use
the smooth grayscale near-depth retained field, not the sparse direct-reflector
composition. Publish a controlled pair that differs only in its initial active
crystal-to-sample orientation: identity `(0, 0, 0)` and oblique
`(17, 31, 43)` Bunge ZXZ degrees.

Both loops use one x-axis revolution, 576 distinct frames, 24 fps, 24 seconds,
4096-square presentation sampling, and the same source master, overlap field,
tone mapping, optical-depth treatment, and encoding profile.

Original production roots (historical invocation evidence):
`local/idealized-near-depth-rotation/quartz-identity-4k-24fps-24s-v1`
and
`local/idealized-near-depth-rotation/quartz-oblique-17-31-43-4k-24fps-24s-v1`.
These superseded 24 fps artifacts remain historical evidence and are not
current Atlas publication packages.

Current canonical publication packages for the superseding 60 fps pair:
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-identity-60fps/`
and
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-oblique-17-31-43-60fps/`.

## Acceptance Criteria

- [x] The tiled high-resolution renderer is pixel-identical to the original full-frame path at a bounded test size.
- [x] Identity and oblique editions bind the same retained 1025-square quartz master and overlap arrays.
- [x] Each edition contains 576 sequential 4096 x 4096 frames and closes exactly without a duplicate endpoint.
- [x] Each edition publishes a 24 fps, 24-second ProRes 422 HQ editing master and H.264 viewing copy.
- [x] The two frame-zero previews are visibly distinct and their manifests differ only where orientation or file identity requires.
- [x] Full decode, focused tests, Ruff, tracker/catalog validation, and whitespace checks pass.
