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
- Scientific and gallery branch regressions require a shared projected root and
  exact shared background-correction output, then allow deliberate divergence.
  They reject missing or divergent correction nodes, disconnected roots,
  unrecorded intermediates, wrong terminals, and arbitrary final arrays.
- Canonical-content regressions recompute and verify full checksums and short
  IDs for every recipe, the orientation candidate set, and the orientation
  decision. Stale IDs, selections outside the candidate set, and a mismatched
  decision link fail before staging; correctly re-identified content changes
  the run ID.
- The materialized content registry covers projected, acquisition-corrected,
  intermediate, scientific, and gallery float arrays. Even a continuous graph
  is rejected if it names a fabricated node with no retained float artifact.
- A 700x1400 regression records five deterministic native 512x512 center/corner
  tiles and directly observes float32 input and complex64 output at every
  sequential SciPy real-FFT boundary. Hermitian-corrected band energies are
  summed before normalization, preserving axis-equivalent cycles-per-pixel
  classification.
- Native 0.5-cycle/pixel checkerboards at 512, 1024, and 2048 pixels remain in
  the observable high band while frequency working memory stays capped at one
  512x512 tile. Small images use their full native extent.
- Quantization ledgers link each uint16 export to its label, recomputed content
  ID, and full source-array SHA-256 in the registry. One-pixel axes fail before
  staging.
- A publication-order regression observes all nested directories flushed
  deepest-first, then the partial root, atomic rename, and final output-root
  flush.
- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)
  records the identity, atomic-publication, layout, quantization, and comparison
  exclusion contracts.
