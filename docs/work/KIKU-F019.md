---
id: KIKU-F019
type: feature
title: Prove Ice Ih canonical-master to detector reprojection congruence
status: done
parent: KIKU-E001
children:
  - KIKU-T064
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, detector-geometry, master-pattern, reprojection]
links:
  - ../dictionaries/ice-ih-ebsdx-rs-contract-crosswalk.md
  - ../acceptance/ice-ih-master-detector-congruence.md
evidence:
  - ../../scripts/run_ice_ih_master_detector_congruence.py
---

# KIKU-F019: Prove Ice Ih canonical-master to detector reprojection congruence

## Description

Implement the inverse, source-bound geometry bridge from a canonical
two-hemisphere Ice Ih master to declared detector pixels. Preserve raw values,
make the full detector-pattern comparison visible, and describe the result as
same-source coordinate congruence rather than acquired-pattern validation.

## Acceptance Criteria

- [x] A reusable primitive maps a raw stereographic master through declared
  detector geometry and an explicit active crystal-to-sample rotation.
- [x] The source proof verifies run and dictionary-master identities before
  comparing full-resolution raw detector fields.
- [x] A visual record shows source pattern, reprojected pattern, residual, and
  pixelwise agreement with explicit scientific nonclaims.

## Completion Evidence

The `ice-ih-master-detector-congruence-v0.1.1` bundle compares all 3,145,728
pixels and reports a centered cosine of `0.998537216`. Its fields share source
physics but exercise the declared master/detector coordinate bridge.
