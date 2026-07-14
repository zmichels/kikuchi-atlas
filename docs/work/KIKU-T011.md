---
id: KIKU-T011
type: task
title: Run Production and Visual Acceptance
status: active
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [gpu, production, visual-acceptance]
evidence:
  - ../acceptance/forsterite-milestone.md
  - ../decisions/0004-bounded-observable-simulation-ladder.md
  - ../../recipes/benchmarks/forsterite-resolution-501.yml
  - ../../recipes/production/forsterite-simulation.yml
  - ../../recipes/gallery/forsterite-final.yml
  - ../../local/runs/
---

# KIKU-T011: Run Production and Visual Acceptance

## Description

Execute the authoritative ebsdsim GPU production pass on the M2, render the
final bundle, inspect it at native scale, and record the acceptance decision.
Production-source development now follows the bounded, observable ladder in
ADR 0004 after the original all-controls-at-once run proved finite but
operationally unreasonable.

## Acceptance Criteria

- [ ] GPU evidence proves the requested authoritative backend ran without substitution.
- [ ] Scientific diagnostics and native-scale visual review are recorded.
- [ ] The user-accepted final bundle, recipe, and rendered image are linked here.
- [x] CPU-only preflight, explicit multi-bin opt-in, and durable progress journaling prevent another opaque production launch.

## Runtime diagnosis and current rung

- The first `forsterite-production-master` attempt was interrupted after at
  least 5 h 29 min. Metal command-completion counters were advancing, GPU
  utilization was near 99%, and no recovery occurred; the run was slow rather
  than frozen.
- Exact counts predict about 5.74 h per attempted production bin and at least
  two bins before relative-image stopping, making the previous single-shot
  execution unreasonable on the local M2.
- `simulate-master --plan-only` now reports finite bounds without creating a
  GPU device. Multi-bin execution requires `--allow-multi-bin` and explicitly
  remains non-resumable under ebsdsim 0.1.8.
- The active `forsterite-resolution-501` rung changes only `halfw` from 128 to
  250, retains the proven one-bin physics controls, and records every chunk in
  a persistent journal. Its plan is 63,701 directions, 2,361 reflections, and
  7,963 chunks.
- The rung completed in 2,104.13 s of dynamical work and published
  `master-437f865cd0f68384`. The identical final rendering contract produced
  `local/runs/run-4088ff482ebb77a2`; its matched 257-grid baseline is
  `local/runs/run-ec3991afa700bc0c`.
- Preliminary review records sharper fine structure but also greater granular
  texture and persistent bright zone-axis clipping. The linked acceptance
  ledger leaves user acceptance and any next-rung promotion explicitly open.
