---
id: KIKU-T005
type: task
title: Build the Explicit Processing Graph
status: done
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [processing, acquisition, gallery]
evidence:
  - ../../tests/unit/test_processing_stages.py
  - ../../tests/scientific/test_processing_invariants.py
  - ../../recipes/proof/scientific-clean.yml
  - ../../recipes/gallery/gallery-crisp.yml
  - ../../src/kikuchi_lab/processing/graph.py
  - ../../src/kikuchi_lab/processing/stages.py
---

# KIKU-T005: Build the Explicit Processing Graph

## Description

Implement immutable, ordered acquisition-look and gallery-look processing
stages whose parameters and intermediate results remain inspectable.

## Acceptance Criteria

- [x] Stage and invariant tests under `tests/unit/test_processing_stages.py` and `tests/scientific/test_processing_invariants.py` pass.
- [x] Every stage records its name, parameters, input, output, and warnings.
- [x] Reference synthetic stage images and numerical evidence are linked here.

## Accepted Evidence

- `uv run pytest tests/unit/test_processing_stages.py
  tests/scientific/test_processing_invariants.py -q`: 26 passed.
- `uv run pytest -m "not slow and not gpu" -q`: 186 passed, 1 deselected.
- `uv run ruff check src tests`, `uv run python
  scripts/validate_work_items.py`, and `git diff --check`: passed.
- Deterministic synthetic band, step-edge, constant-field, and Nyquist
  checkerboard images in the focused tests prove float32/finiteness, immutable
  outputs, constant-field detail neutrality, unsharp overshoot retention,
  monotonic tone response, and anti-aliased 4x detector downsampling.
- The scientific-clean and gallery-crisp graph results retain the exact same
  canonical detector-product ID while receiving distinct content-derived
  processed-product IDs. Every immutable stage record links its input/output
  image IDs, parameters, and structured warnings.

## Scientific and API Decisions

The canonical detector projection is an immutable input and is never promoted
to a processing intermediate or overwritten. Processing creates owned,
read-only float32 arrays at every stage, with an ordered identity chain from
the source image through the final detector-resolution image. The result
records source shape, output shape, supersampling, and physical detector extent
and rejects a downsample target that disagrees with canonical detector
geometry.

Robust normalization intentionally does not clip percentile outliers, and
unsharp/detail enhancement intentionally retains overshoot. CLAHE declares an
explicit `clip_0_1` input-domain policy, records the measured input clipping
fraction, and reports clipping above 0.1%. Tone mapping remains the explicit
display-range boundary and separately reports clipping above 0.1% and
decreasing tone endpoints. The requested parameters remain unchanged in every
case.

The checked-in YAML presets make the first proof comparison reviewable:
scientific-clean uses restrained background correction, normalization, CLAHE,
and tone mapping; gallery-crisp adds named multiscale detail and unsharp stages.
Both use anti-aliased downsampling only after all supersampled processing.

## Follow-up Quality Evidence

- Both presets now use a real robust percentile window of 1% to 99%. An
  end-to-end outlier regression proves normalization retains out-of-window
  values and the following CLAHE boundary explicitly clips and reports them.
- Preset schema version 1, name, and intent are required and round-trip from
  YAML. Name and intent remain descriptive metadata: renaming either does not
  change the computational recipe ID. Missing, Boolean, or unsupported schema
  versions are rejected.
- Multiscale detail and unsharp stages measure actual RMS Fourier-amplitude
  transfer above 0.25 cycles per pixel. That measured ratio is recorded in
  stage diagnostics and triggers a structured warning above the initial 2.0x
  ceiling. Transfer tests prove an unsharp amount of 1.5 exceeds 2.0x on a
  Nyquist target, while constant and near-zero inputs remain finite and do not
  create false warnings.
