---
id: KIKU-T017
type: task
title: Bundle and Reproduce Kinematical Runs
status: ready
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [workflow, bundle, determinism]
evidence:
  - ../superpowers/plans/2026-07-13-kikuchipy-kinematical-reference-products.md
---

# KIKU-T017: Bundle and Reproduce Kinematical Runs

## Description

Add a standalone kinematical workflow and manifest so the new baseline does not
destabilize the accepted dynamical final bundle.

## Acceptance Criteria

- [ ] One run bundle contains canonical recipes, arrays, figures, reflector records, ledger, and checksums.
- [ ] Repeating the run with the same scientific inputs reproduces its canonical identity and products.
- [ ] Existing scientific-clean and gallery bundle tests remain unchanged and passing.
