---
id: KIKU-T065
type: task
title: Recover a spread of reprojected Ice Ih detector orientations
status: done
parent: KIKU-F020
created: 2026-07-21
priority: P0
tags: [ice-ih, quaternions, detector, partial-s2, ranking, verification]
links:
  - ../acceptance/ice-ih-synthetic-detector-orientation-recovery.md
evidence:
  - ../../scripts/run_ice_ih_synthetic_detector_orientation_recovery.py
  - ../../tests/unit/test_synthetic_detector_orientation_recovery.py
---

# KIKU-T065: Recover a spread of reprojected Ice Ih detector orientations

## Description

Select a deterministic spread of cache quaternions, reproject their canonical
master signals onto the declared detector, map the raw synthetic pixels back
to the known camera footprint, and rank all candidate rows on that mask.

## Acceptance Criteria

- [x] Selection starts from the canonical identity and avoids duplicate
  entries; invalid requested counts are rejected in a focused test.
- [x] Four orientation-varied detector fields and partial-S2 signals are
  preserved in an atomic local result bundle.
- [x] The proof rejects publication unless every selected target is first in
  the masked candidate ranking.

## Completion Evidence

The four stable selected entries are `6577`, `15`, `297`, and `7144`. Their
reprojected detector fields recover the corresponding candidate first, and the
visual record presents the score gaps without suggesting acquired EBSD data.
