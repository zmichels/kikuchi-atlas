---
id: KIKU-F030
type: feature
title: Release the Ni preprocessing-sensitivity support study
status: done
parent: KIKU-E001
children:
  - KIKU-T079
  - KIKU-T080
created: 2026-07-24
priority: P1
tags: [reference-pack, nickel, preprocessing, hough, diagnostics]
links:
  - ../reference-packs/ni-gain24db-preprocessing-sensitivity-v0.1.md
  - ../acceptance/ni-gain24db-preprocessing-sensitivity.md
evidence:
  - ../../recipes/reference-pack/ni-gain24db-preprocessing-sensitivity-v0.1.yml
  - ../../scripts/run_ni_gain24db_preprocessing_sensitivity.py
---

# KIKU-F030: Release the Ni preprocessing-sensitivity support study

## Description

Turn a critical protocol choice into a bounded, reproducible support study:
compare three named background-processing variants while holding the Ni source,
Hough geometry, master, reflector selection, and calibration patterns fixed.

## Acceptance Criteria

- [x] The recipe pins the complete variant ladder, source/inventory identity,
  shared Hough route, expected aggregates, reference convention, and
  nonclaims.
- [x] The runner verifies the source inventory and linked baseline recipe,
  records per-pattern results, and fails on unexpected aggregate changes.
- [x] A shareable diagnostic makes the protocol and limited interpretation
  visible without presenting the result as independent truth or a general
  method ranking.

## Completion Evidence

The retained 2026-07-24 run produced three 7/7-indexed variants and a
checksum-bearing JSON/PNG evidence bundle. Against the all-division reference,
the raw and static-only mean cubic-symmetry-reduced deltas were 0.164918° and
0.049757°, respectively.
