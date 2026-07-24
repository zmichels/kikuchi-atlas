---
id: KIKU-F029
type: feature
title: Release the lightweight Ni Reference Pack v0.1
status: done
parent: KIKU-E001
children:
  - KIKU-T077
  - KIKU-T078
created: 2026-07-24
priority: P1
tags: [reference-pack, nickel, provenance, checksums, acquired-ebsd]
links:
  - ../reference-packs/ni-gain24db-calibration-hough-v0.1.md
  - ../acceptance/ni-gain24db-reference-pack-intake.md
evidence:
  - ../../reference-packs/ni-gain24db-calibration-hough-v0.1.source-inventory.json
  - ../../scripts/verify_ni_gain24db_reference_pack.py
  - ../../scripts/build_ni_gain24db_reference_baseline.py
---

# KIKU-F029: Release the lightweight Ni Reference Pack v0.1

## Description

Publish the user-approved lightweight release boundary: a legal upstream
pointer, exact source inventory, source/cache verifier, recipe, and rerunnable
local baseline. Keep the 100+ MB source data external and retain the explicit
source-bound scientific claim.

## Acceptance Criteria

- [x] A tracked source-inventory manifest names the CC BY source, recipe, and
  every expected raw file with bytes and SHA-256 digest, without copying raw
  data into the repository.
- [x] A verifier can fetch through Kikuchipy only when requested and rejects
  missing, unexpected, resized, or altered source files.
- [x] Public documentation gives a short reproduce path, an exact current
  recipe digest, attribution, baseline result, and nonclaims.

## Completion Evidence

The verifier accepted all 26 source files (114,787,781 bytes) from the
Kikuchipy cache on 2026-07-24. The current recipe digest reproduced the fixed
CPU Hough baseline: 7/7 patterns indexed, mean fit 0.26731613278388977, mean
confidence 0.7579495310783386, and 50 selected reflectors.
