---
id: KIKU-T071
type: task
title: Assemble a browsable local Ice Ih engine evidence dashboard
status: done
parent: KIKU-F024
created: 2026-07-22
priority: P2
tags: [ice-ih, dashboard, visualization, handoff, evidence]
evidence:
  - ../../scripts/build_ice_ih_engine_dashboard.py
  - ../../tests/unit/test_ice_ih_engine_dashboard.py
---

# KIKU-T071: Assemble a browsable local Ice Ih engine evidence dashboard

## Description

Create a local HTML entry point that links the current image-space,
detector-to-S2, coarse-search, local-refinement, geometry-sensitivity, and
photometric-stress artifacts to their underlying evidence files.

## Acceptance Criteria

- [x] The page fails loudly if a required local evidence file is absent.
- [x] The page labels the observation/transform/solve evidence ladder and its
  synthetic-only boundary.
- [x] A small HTML-contract test checks the retained explicit-preprocessing
  warning and evidence links.

## Completion Evidence

`local/ice-ih-engine-dashboard-v0.1.1/index.html` opens the six current
evidence products from a single dark-theme page and links the verified detector
observation manifest directly.
