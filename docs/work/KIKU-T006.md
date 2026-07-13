---
id: KIKU-T006
type: task
title: Write Diagnostics and Artifact Bundles
status: done
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

- [x] Diagnostics and artifact tests under `tests/unit/test_diagnostics.py` and `tests/unit/test_artifact_bundle.py` pass.
- [x] TIFF/PNG exports preserve the required bit depth and declared intensity mapping.
- [x] A validated example bundle and manifest are linked here.

## Accepted Evidence

- `tests/unit/test_diagnostics.py` exercises known robust percentiles, clipping
  fractions, gradient distributions, frequency-band separation, and malformed
  arrays.
- `tests/unit/test_artifact_bundle.py` builds a complete temporary example
  bundle, independently reads its TIFF and PNG products to prove uint16/uint8
  depth, and verifies every manifest byte count and SHA-256 against disk.
- The example proves canonical JSON, an external manifest checksum, the
  acquisition-corrected semantic boundary, complete float-stage retention,
  and a quantization record linked to the source float product for every
  uint16 export.
- Recovery regressions prove completed-run refusal, partial-run refusal,
  explicit timestamped abandonment, malformed-input cleanup, and run identity
  stability across timestamps, timings, resource values, and local paths.
- Adversarial nested `artifact_location`, relative/absolute path, `retrieved_at`,
  and `generated_at` evidence cannot perturb the explicit versioned run-identity
  whitelist. Source/master/recipe checksums, software versions, projection
  geometry, decision IDs, ordered stage lineage, and float pixels do perturb it.
- A 64x128 regression proves that equal 0.25-cycle/pixel signals along either
  detector axis receive identical radial-frequency energy classification.
- Background-lineage regressions reject a missing or misnamed correction,
  discontinuous input/output IDs, and an acquisition-corrected array unrelated
  to the recorded background-stage output.
- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)
  records the identity, atomic-publication, layout, quantization, and comparison
  exclusion contracts.
