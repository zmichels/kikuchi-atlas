---
id: KIKU-T006
type: task
title: Write Diagnostics and Artifact Bundles
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [artifacts, diagnostics, provenance]
---

# KIKU-T006: Write Diagnostics and Artifact Bundles

## Description

Write content-addressed, atomically published bundles containing manifests,
raw products, processing stages, high-bit-depth images, and diagnostics.

## Acceptance Criteria

- [ ] Artifact round-trip and corruption tests under `tests/unit/test_artifacts.py` pass.
- [ ] TIFF/PNG exports preserve the required bit depth and declared intensity mapping.
- [ ] A validated example bundle and manifest are linked here.
