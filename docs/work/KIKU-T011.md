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
  - ../../recipes/production/forsterite-simulation.yml
  - ../../recipes/gallery/forsterite-final.yml
  - ../../local/runs/
---

# KIKU-T011: Run Production and Visual Acceptance

## Description

Execute the authoritative ebsdsim GPU production pass on the M2, render the
final bundle, inspect it at native scale, and record the acceptance decision.

## Acceptance Criteria

- [ ] GPU evidence proves the requested authoritative backend ran without substitution.
- [ ] Scientific diagnostics and native-scale visual review are recorded.
- [ ] The user-accepted final bundle, recipe, and rendered image are linked here.
