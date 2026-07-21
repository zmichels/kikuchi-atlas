---
id: KIKU-T054
type: task
title: Generate and verify the Ice Ih spherical candidate cache
status: done
parent: KIKU-F013
created: 2026-07-20
priority: P0
tags: [ice-ih, dictionary, cache, so3, s2]
links:
  - ../dictionaries/ice-ih-flagship-design.md
  - ../../recipes/kinematical/ice-ih-oxygen-quiet-proof.yml
evidence:
  - ../../local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21/manifest.json
  - ../../scripts/build_ice_ih_spherical_dictionary.py
  - ../../src/kikuchi_lab/dictionary/ice_ih.py
  - ../../tests/unit/test_ice_ih_dictionary.py
---

# KIKU-T054: Generate and verify the Ice Ih spherical candidate cache

## Description

Produce the fast, source-bound coarse candidate matrix from the checked Ice
master. Persist orientations, S2 directions, normalized candidate rows,
source/recipe identities, checksums, and a readable resource manifest.

## Acceptance Criteria

- [x] The cache uses documented `6/mmm` fundamental-zone and S2 samplers at
  the accepted 5-degree resolution.
- [x] Rows derive from raw canonical master intensity via named bilinear
  sampling, mean-centering, and L2 normalization only.
- [x] The package is atomically published, hash-verified, and contains no
  absolute local path.
- [x] Cache dimensions, orientation uniqueness, source hashes, and every
  payload checksum are independently verified.

## Accepted Evidence

`ice-ih-spherical-dictionary-d9be1442fd1b0461` is a 13,155-by-1,946 float32
candidate matrix (97.65 MiB) derived from the checked Ice master. The resource
was built locally in 3.70 seconds and independently reverified from its
published checksums and deterministic cache-ranking fixture.
