---
id: KIKU-T018
type: task
title: Add CLI and Conduct Native-Scale Visual Gate
status: active
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [cli, visual-review, decision-gate]
evidence:
  - ../acceptance/forsterite-milestone.md
  - ../acceptance/kinematical-forsterite.md
  - ../incubator/interactive-spherical-view.md
  - ../../tests/unit/test_cli.py
  - ../../local/runs/kinematical/kinematical-run-d1dab780ec480f72/manifest.json
---

# KIKU-T018: Add CLI and Conduct Native-Scale Visual Gate

## Description

Expose the workflow through the local CLI, retain native-scale review figures,
and record whether pure kinematical outputs satisfy the desired schematic and
science-art direction before planning a hybrid renderer.

## Acceptance Criteria

- [x] The CLI reports the run path, identity, selected reflector count, and figure inventory.
- [x] The retained review includes stereographic, spherical, Lambert, detector, and threshold-comparison views.
- [ ] The decision record explicitly chooses pure kinematical refinement or a separately planned evidence-guided hybrid.
- [x] Interactive sphere and openable 3D viewing are linked as an additive incubated direction, not a replacement for projected images.
