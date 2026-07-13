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
  tests/scientific/test_processing_invariants.py -q`: 18 passed.
- `uv run pytest -m "not slow and not gpu" -q`: 178 passed, 1 deselected.
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
unsharp/detail enhancement intentionally retains overshoot. Tone mapping is
the explicit display-range boundary. It reports clipping above 0.1%, decreasing
tone endpoints, and detail gain above the documented initial ceiling of 2.0;
the requested parameters remain unchanged in every case.

The checked-in YAML presets make the first proof comparison reviewable:
scientific-clean uses restrained background correction, normalization, CLAHE,
and tone mapping; gallery-crisp adds named multiscale detail and unsharp stages.
Both use anti-aliased downsampling only after all supersampled processing.
