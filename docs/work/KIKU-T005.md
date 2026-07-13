---
id: KIKU-T005
type: task
title: Build the Explicit Processing Graph
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [processing, acquisition, gallery]
---

# KIKU-T005: Build the Explicit Processing Graph

## Description

Implement immutable, ordered acquisition-look and gallery-look processing
stages whose parameters and intermediate results remain inspectable.

## Acceptance Criteria

- [ ] Processing invariant tests under `tests/unit/test_processing.py` pass.
- [ ] Every stage records its name, parameters, input, output, and warnings.
- [ ] Reference stage images and numerical evidence are linked here.
