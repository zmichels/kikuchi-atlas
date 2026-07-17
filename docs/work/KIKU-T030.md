---
id: KIKU-T030
type: task
title: Prove quartz parity against MTEX
status: done
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- mtex
- parity
- acceptance
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T030: Prove quartz parity against MTEX

## Description

Export a compact MTEX 6.1.1 quartz ledger, compare Python and MTEX polygon
geometry without ordering assumptions, and record the accepted slicer smoke check.

## Acceptance Criteria

- [x] The committed ledger is regenerated from the reviewed MTEX request and records 32 vertices and 18 visible faces.
- [x] Visible labels/counts, Hausdorff distance, volume, and face-normal metrics pass the reviewed tolerances.
- [x] The acceptance bundle contains `mtex-parity.json` and opens as one unmodified solid in the FlashForge-oriented slicer workflow.

## Accepted Evidence

- `scripts/export_mtex_habit_reference.m`,
  `reference/habits/quartz-mtex-request.json`,
  `reference/habits/quartz-mtex-6.1.1.json`, and
  `tests/integration/test_mtex_habit_parity.py`.
- The marked MATLAB/MTEX regeneration test passes against MTEX 6.1.1.
- [Crystal habit acceptance ledger](../acceptance/crystal-habit-mesh.md) records
  the parity metrics and Flash Studio 1.7.11 AD5X-oriented import inspection.
