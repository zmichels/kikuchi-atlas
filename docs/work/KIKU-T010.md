---
id: KIKU-T010
type: task
title: Implement Final Rendering and Reproduction
status: active
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
  - ../../local/runs/run-d0c8306c3c060907/manifest.json
  - ../../local/reproductions/run-d0c8306c3c060907/manifest.json
---

# KIKU-T010: Implement Final Rendering and Reproduction

## Description

Render the selected orientation at final resolution and prove that its recipe
and source evidence reproduce the same canonical outputs.

## Acceptance Criteria

- [x] Final-render integration tests verify content identities and high-bit-depth outputs.
- [x] The reproduction command rebuilds from the recorded manifest and selection.
- [x] Deterministic and environment-dependent comparison evidence is linked here.
- [x] Scientific-clean and gallery-crisp products derive from the same immutable projection.
- [x] A stage-by-stage clarity ledger compares raw, acquisition-corrected, scientific-clean, and gallery-crisp products without treating local aesthetic references as calibrated truth.
- [ ] Human review confirms coherent luminous bands and nodes, reduced proof-grade speckle, smooth band interiors, and no conspicuous halos or artificial line overlays.

## Implementation Evidence

- Code landed in `41582bc` with clarity tuning in `34404f8` and a genuine
  non-identical GPU-source tolerance regression in `5d6d2c9`.
- `render-final` intrinsically validates the selection record, explicitly verifies
  the caller-supplied proof root, and rejects any selection that is not the
  current unique leaf of its proof-scoped lineage.
- The tracked final target is 1536 x 2048 detector-native pixels from one 3072 x
  4096 supersampled projection. The development profile intentionally reuses the
  selected 180 x 240 proof geometry and is marked `DEVELOPMENT / NOT FINAL
  QUALITY` in warnings and provenance.
- The real selected-orientation development artifact is
  `local/runs/run-d0c8306c3c060907`; its manifest-driven rebuild is
  `local/reproductions/run-d0c8306c3c060907`.
- Exact reproduction retained run ID `run-d0c8306c3c060907`, exact CPU float and
  uint16 products, and manifest comparison identity
  `manifest-comparison-f571acc7d56532be` in both roots.
- Development diagnostics show gallery high-frequency energy `0.0210427521`,
  below the selected proof processing value `0.0296949473`; the tuned run has no
  clipping or excessive-gain warnings and contains no line-overlay stage.
- Task 11 remains the separate production-resolution and user visual-acceptance
  gate. The final checkbox above is intentionally open until that review occurs.
