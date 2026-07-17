---
id: KIKU-T030
type: task
title: Prove quartz parity against MTEX
status: ready
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

- [ ] The committed ledger is regenerated from the reviewed MTEX request and records 32 vertices and 18 visible faces.
- [ ] Visible labels/counts, Hausdorff distance, volume, and face-normal metrics pass the reviewed tolerances.
- [ ] The acceptance bundle contains `mtex-parity.json` and opens as one unmodified solid in the FlashForge-oriented slicer workflow.
