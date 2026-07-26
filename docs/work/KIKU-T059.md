---
id: KIKU-T059
type: task
title: Upgrade quartz near-depth artist pair to 60 fps
status: done
parent: KIKU-F014
created: 2026-07-21
priority: P1
tags: [quartz, near-depth, grayscale, rotation, 60fps, video-art]
links:
  - ../acceptance/quartz-near-depth-artist-pair.md
evidence:
  - ../../scripts/render_retained_near_depth_rotation.py
  - ../../local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/manifest.json
  - ../../local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/manifest.json
  - ../../local/idealized-near-depth-rotation/quartz-artist-pair-60fps-v1/identity-left-oblique-right.png
  - ../../local/idealized-near-depth-rotation/quartz-artist-pair-60fps-v1/STEVE-KIDDER-QUARTZ-60FPS-NOTES.txt
---

# KIKU-T059: Upgrade quartz near-depth artist pair to 60 fps

## Description

Supersede the cataloged 24 fps pair with identity and oblique alpha-quartz
near-depth editions at true 60 fps and 2048-square resolution. Keep the
24-second loop duration, source fields, grayscale treatment, motion axis, and
initial orientations fixed while rendering 1,440 unique orientations per
edition. Stream ordered frames into the editing master so the higher temporal
resolution does not require another retained PNG sequence.

## Acceptance Criteria

- [x] Each edition contains 1,440 newly rendered orientations at exact 60 fps, 24 seconds, and 2048 x 2048 pixels, without temporal interpolation or a duplicate endpoint.
- [x] Identity `(0, 0, 0)` and oblique `(17, 31, 43)` editions bind the same checksum-locked retained master, overlap field, tone map, optical-depth treatment, and x-axis motion.
- [x] Ordered rendering uses bounded in-flight work and streams directly into a ProRes 422 HQ editing master.
- [x] Each edition also has a full-resolution 2048-square H.264 viewing copy derived from its decoded master.
- [x] Loop closure, controlled-pair identity, complete media decode, hashes, probes, focused tests, lint, tracker/catalog validation, and whitespace checks pass.
- [x] The new 60 fps products replace the 24 fps pair in the artifact catalog without deleting the previous local editions.
