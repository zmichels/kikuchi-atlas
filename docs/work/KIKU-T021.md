---
id: KIKU-T021
type: task
title: Bundle deterministic spherical exchange artifacts
status: done
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [csv, npz, json, bundle, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
  - ../../tests/unit/test_spherical_intensity_bundle.py
  - ../../src/kikuchi_lab/spherical_intensity/bundle.py
---

# KIKU-T021: Bundle deterministic spherical exchange artifacts

## Description

Write exact CSV, NPZ, JSON, and optional axial exchange artifacts through a
hash-inventoried atomic bundle boundary.

## Acceptance Criteria

- [x] CSV row/column order, numeric formatting, NPZ dtypes, and JSON semantics are fixed and tested byte-for-byte.
- [x] The ledger and manifest preserve field, source, recipe, and artifact identities without self-hashing ambiguity.
- [x] Failed writes never promote a partial bundle, and optional axial absence is explicit.

## Verification

- Focused deterministic bundle suite: `69 passed`, including review-hardening
  cases for canonical axial eligibility, bounded omitted equator pairs,
  diagnostic-only MTEX validation identity, collision investigation, strict
  registered inventory, status-gated quarantined partial evidence, universal
  active-partial rejection, and filesystem-free prevalidation.
- Existing artifact and persistence regression: `44 passed`.
- Spherical contract and mapping regression: `93 passed`.
- Ruff, work-item validation, and diff checks pass on the completed slice.
