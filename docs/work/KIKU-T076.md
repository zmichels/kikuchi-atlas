---
id: KIKU-T076
type: task
title: Reproduce the Ni calibration Hough baseline with a visual diagnostic
status: done
parent: KIKU-F028
children: []
created: 2026-07-23
priority: P1
tags: [nickel, hough, pyebsdindex, reproducibility, visualization]
links:
  - ../acceptance/ni-gain24db-reference-pack-intake.md
evidence:
  - ../../scripts/build_ni_gain24db_reference_baseline.py
  - ../../recipes/reference-pack/ni-gain24db-calibration-hough-v0.1.yml
---

# KIKU-T076: Reproduce the Ni calibration Hough baseline with a visual diagnostic

## Description

Use the source-bound upstream PC and processing route to reproduce a compact
CPU Hough result on the seven Ni calibration patterns, then retain the numeric
result and geometry-overlay sheet as local evidence.

## Acceptance Criteria

- [x] The runner pins the optional PyEBSDIndex version and fails if counts,
  reflector selection, or aggregate baseline metrics change.
- [x] It records source and output checksums, runtime versions, processing,
  PC convention, and nonclaims.
- [x] It renders Hough-derived geometrical traces over all calibration
  patterns without presenting them as independent ground truth.

## Completion Evidence

With pyebsdindex==0.3.9.2, the CPU route reproduced 7/7 indexed calibration
patterns with the recipe-pinned mean fit and confidence values.
