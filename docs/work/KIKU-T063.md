---
id: KIKU-T063
type: task
title: Map and rank a source-bound Ice Ih detector on its covered S2 grid
status: done
parent: KIKU-F018
created: 2026-07-21
priority: P0
tags: [ice-ih, gnomonic, partial-s2, masked-cosine, verification]
links:
  - ../acceptance/ice-ih-detector-to-s2-adapter-proof.md
evidence:
  - ../../src/kikuchi_lab/dictionary/detector_to_s2.py
  - ../../tests/unit/test_detector_to_s2_adapter.py
---

# KIKU-T063: Map and rank a source-bound Ice Ih detector on its covered S2 grid

## Description

Build the narrow adapter primitive for a known detector recipe: convert exact
S2 sample directions to in-frame gnomonic pixel locations, bilinearly sample
the raw detector, and rank the cache using only the declared covered subset.

## Acceptance Criteria

- [x] Unit tests round-trip detector rays through the declared geometry,
  retain the backside as uncovered, and verify masked ranking semantics.
- [x] The local proof verifies its dictionary and source-detector hashes before
  publishing an append-only result bundle.
- [x] The visual proof shows the detector points, partial S2 values, and ranked
  candidates with the same-source scientific boundary visible.

## Completion Evidence

The adapter proof's source detector geometry maps to 308 cache directions.
The masked ranking result recovers identity entry `6577` with zero angular
error, while explicitly retaining unknown directions as `NaN` and false mask.
