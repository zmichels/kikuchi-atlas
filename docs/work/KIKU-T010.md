---
id: KIKU-T010
type: task
title: Implement Final Rendering and Reproduction
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [final, rendering, reproducibility]
evidence:
  - ../../tests/integration/test_final_workflow.py
  - ../../tests/integration/test_recipe_reproduction.py
  - ../../recipes/gallery/forsterite-final.yml
  - ../decisions/0003-clarity-aesthetic-target.md
  - ../../reference/catalog/aesthetic-clarity.yml
  - ../../local/runs/
---

# KIKU-T010: Implement Final Rendering and Reproduction

## Description

Render the selected orientation at final resolution and prove that its recipe
and source evidence reproduce the same canonical outputs.

## Acceptance Criteria

- [ ] Final-render integration tests verify content identities and high-bit-depth outputs.
- [ ] The reproduction command rebuilds from the recorded manifest and selection.
- [ ] Deterministic and environment-dependent comparison evidence is linked here.
- [ ] Scientific-clean and gallery-crisp products derive from the same immutable projection.
- [ ] A stage-by-stage clarity ledger compares raw, acquisition-corrected, scientific-clean, and gallery-crisp products without treating local aesthetic references as calibrated truth.
- [ ] Human review confirms coherent luminous bands and nodes, reduced proof-grade speckle, smooth band interiors, and no conspicuous halos or artificial line overlays.
