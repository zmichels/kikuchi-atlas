---
id: KIKU-T004
type: task
title: Implement the kikuchipy Projection Boundary
status: done
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [kikuchipy, detector, orientation]
evidence:
  - ../../tests/adapters/test_kikuchipy_projection.py
  - ../../tests/scientific/test_projection_invariants.py
  - ../../src/kikuchi_lab/projection/kikuchipy_adapter.py
---

# KIKU-T004: Implement the kikuchipy Projection Boundary

## Description

Project canonical master patterns through explicit orientation-frame and
detector-geometry contracts while containing kikuchipy types in one adapter.

## Acceptance Criteria

- [x] `tests/adapters/test_kikuchipy_projection.py` proves orientation inversion and detector mapping.
- [x] Projection output is a canonical detector-pattern product with source identities.
- [x] Geometry diagnostics and accepted adapter evidence are linked here.

## Accepted Evidence

- `uv run pytest tests/adapters/test_kikuchipy_projection.py
  tests/scientific/test_projection_invariants.py -q`: 9 passed.
- `uv run pytest -m "not slow and not gpu" -q`: 156 passed, 1 deselected.
- `uv run ruff check src tests`, `uv run python scripts/validate_work_items.py`,
  and `git diff --check`: passed.
- The canonical output is an immutable float32 `DetectorPatternProduct` at the
  supersampled detector shape. Its metadata retains the master product and
  array identities, untouched ebsdsim NPZ checksum, Pnma phase, orientation,
  full detector recipe, energy, PC convention, and supersampling state.
- The EDAX-TSL behavioral invariant maps crystal `[100]` to sample TD
  `[0, 1, 0]` for an active positive 90 degree Bunge phi1 rotation about ND.
  A projection-level regression matches the direct kikuchipy call exactly.
- A non-GPU projection smoke consumed Task 3's real local Metal-generated
  `master-87a6e36534219826` and produced finite raw float32 detector product
  `detector-0b8d425f9d7224b9` at `(24, 32)`, with range
  `[154.36631774902344, 517.0562744140625]`.

## Scientific and API Decisions

The public orientation is an active crystal-to-sample rotation in EDAX-TSL
sample coordinates `[RD, TD, ND]`. The adapter constructs it with orix
`direction="crystal2lab"`, then explicitly inverts it before kikuchipy's
passive `lab2crystal` projection call. The test compares the resulting
quaternion with orix's standard passive constructor and compares the complete
projected image with a direct kikuchipy call.

The in-memory `EBSDMasterPattern` is built from the canonical integrated
`(north, south, y, x)` float32 data with `projection="lambert"` and
`hemisphere="both"`. Its orix phase uses the canonical Pnma space-group 62
lattice `[10.207, 5.980, 4.756, 90, 90, 90]` angstrom. The adapter never
reloads the native ebsdsim NPZ, so projection cannot silently select an
unintegrated energy bin.

Detector supersampling multiplies shape and divides the unbinned pixel size;
binning, fractional PC convention and coordinates, tilt, azimuth, twist, and
sample tilt remain explicit. This preserves physical extent while leaving
downsampling to `KIKU-T005`. The adapter requests `dtype_out="float32"`,
`compute=True`, and `show_progressbar=False`; because canonical master data are
also float32, kikuchipy does not apply integer display-range rescaling.

Orix represents one Euler triplet as a singleton navigation axis, so
kikuchipy returns `(1, Ny, Nx)`. The adapter validates that exact singleton
shape and removes only that navigation dimension to satisfy the canonical 2D
detector-product contract. All kikuchipy, orix, and diffpy types remain behind
private adapter helpers and do not appear in the returned product.
