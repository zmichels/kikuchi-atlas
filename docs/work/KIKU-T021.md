---
id: KIKU-T021
type: task
title: Bundle deterministic spherical exchange artifacts
status: ready
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [csv, npz, json, bundle, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
---

# KIKU-T021: Bundle deterministic spherical exchange artifacts

## Description

Write exact CSV, NPZ, JSON, and optional axial exchange artifacts through a
hash-inventoried atomic bundle boundary.

## Acceptance Criteria

- [ ] CSV row/column order, numeric formatting, NPZ dtypes, and JSON semantics are fixed and tested byte-for-byte.
- [ ] The ledger and manifest preserve field, source, recipe, and artifact identities without self-hashing ambiguity.
- [ ] Failed writes never promote a partial bundle, and optional axial absence is explicit.
