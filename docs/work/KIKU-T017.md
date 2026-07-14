---
id: KIKU-T017
type: task
title: Bundle and Reproduce Kinematical Runs
status: done
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [workflow, bundle, determinism]
evidence:
  - ../superpowers/plans/2026-07-13-kikuchipy-kinematical-reference-products.md
  - ../../tests/unit/test_kinematical_bundle.py
  - ../../tests/integration/test_kinematical_workflow.py
---

# KIKU-T017: Bundle and Reproduce Kinematical Runs

## Description

Add a standalone kinematical workflow and manifest so the new baseline does not
destabilize the accepted dynamical final bundle.

## Acceptance Criteria

- [x] One run bundle contains canonical recipes, arrays, figures, reflector records, ledger, and checksums.
- [x] Repeating the run with the same scientific inputs reproduces its canonical identity and products.
- [x] Existing scientific-clean and gallery bundle tests remain unchanged and passing.
