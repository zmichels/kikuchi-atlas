---
id: KIKU-T032
type: task
title: Map Lambert masters onto spherical fields
status: ready
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- lambert
- spherical-field
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
---

# KIKU-T032: Map Lambert masters onto spherical fields

## Description

Convert canonical north/south Lambert-square master arrays into one immutable
spherical scalar field with explicit equator ownership, seam diagnostics, and
a reusable bilinear interpolation ledger.

## Acceptance Criteria

- [ ] Project-owned float64 Lambert transforms pass landmarks, round trips, and a pinned kikuchipy-reference oracle without importing private kikuchipy code in production.
- [ ] Field construction verifies source identity and contracts, deduplicates the equator with north ownership, and rejects normalized seam residuals above `1e-6`.
- [ ] Directional sampling records immutable hemisphere, row, column, and weight ledgers that exactly recover selected source nodes and can be reused for mapped values.
