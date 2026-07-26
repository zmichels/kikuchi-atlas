---
id: KIKU-F014
type: feature
title: Artist-grade retained-field animation editions
status: done
parent: KIKU-E001
children:
  - KIKU-T058
  - KIKU-T059
created: 2026-07-21
priority: P1
tags: [retained-field, near-depth, animation, artist-master, orientation]
links:
  - ../acceptance/quartz-near-depth-artist-pair.md
evidence:
  - ../../scripts/render_retained_near_depth_rotation.py
---

# KIKU-F014: Artist-grade retained-field animation editions

## Description

Publish high-resolution, edit-friendly animations from retained kinematical
master and near-depth overlap fields. Editions may vary declared initial
orientation while keeping the source field, display treatment, motion axis,
duration, frame rate, encoding profile, and scientific claim boundary fixed.

## Acceptance Criteria

- [x] Artist editions derive from checksum-bound retained fields rather than flattened image rotation.
- [x] Orientation variants record an explicit active crystal-to-sample Bunge orientation.
- [x] Full-resolution editing masters and practical viewing copies decode cleanly and retain exact media facts and hashes.
- [x] Source-field resolution and presentation-raster resolution remain separately stated.
