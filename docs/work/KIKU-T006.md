---
id: KIKU-T006
type: task
title: Write Diagnostics and Artifact Bundles
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [artifacts, diagnostics, provenance]
evidence:
  - ../../tests/unit/test_diagnostics.py
  - ../../tests/unit/test_artifact_bundle.py
  - ../decisions/0001-artifact-identity-and-bundle-layout.md
---

# KIKU-T006: Write Diagnostics and Artifact Bundles

## Description

Write content-addressed, atomically published bundles containing manifests,
raw products, processing stages, high-bit-depth images, and diagnostics.

## Acceptance Criteria

- [ ] Diagnostics and artifact tests under `tests/unit/test_diagnostics.py` and `tests/unit/test_artifact_bundle.py` pass.
- [ ] TIFF/PNG exports preserve the required bit depth and declared intensity mapping.
- [ ] A validated example bundle and manifest are linked here.
