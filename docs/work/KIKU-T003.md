---
id: KIKU-T003
type: task
title: Validate Forsterite and Isolate ebsdsim
status: done
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [forsterite, ebsdsim, gpu]
evidence:
  - ../../phases/forsterite/source.yml
  - ../../tests/adapters/test_forsterite_source.py
  - ../../tests/adapters/test_ebsdsim_adapter.py
  - ../../tests/integration/test_ebsdsim_gpu.py
  - ../../local/master-patterns/gpu-smoke/forsterite-tiny-gpu.manifest.json
---

# KIKU-T003: Validate Forsterite and Isolate ebsdsim

## Description

Track and validate the COD 9000319 structure, isolate the ebsdsim boundary,
and expose environment diagnostics without backend substitution.

## Acceptance Criteria

- [x] `tests/adapters/test_forsterite_source.py` verifies the tracked source and catalog evidence.
- [x] `tests/adapters/test_ebsdsim_adapter.py` preserves both master-pattern hemispheres and simulation metadata.
- [x] The GPU smoke result and `kikuchi-lab doctor --json` evidence are linked here.

## Accepted Evidence

- COD 9000319 was retrieved on 2026-07-12 and retained byte-for-byte at
  `phases/forsterite/COD-9000319.cif`; SHA-256 is
  `550b8c89c617267d39e7cb6a07fe6f55cd2343453c1c45ec77738bf6fd25d9cd`.
  COD data are CC0-1.0/public domain, with the requested acknowledgement to
  Smyth and Hazen (1973) recorded in `source.yml` and the COD catalog.
- `uv run pytest -m "not gpu and not slow" -q`: 110 passed, 1 deselected.
- `uv run pytest -m "gpu and slow" tests/integration/test_ebsdsim_gpu.py -q -s`:
  1 passed in 3.61 s on Apple M2 Metal. The bounded gate used 4096 trajectories,
  `mc_auto_stop=False`, and produced a finite, non-constant `(2, 17, 17)`
  canonical pattern with resolved backend `gpu_fly_first`.
- `uv run kikuchi-lab doctor --json`: all required checks passed for native
  arm64 Python 3.12.13, Darwin, Apple M2/Metal WebGPU, required packages, and
  output-root writability.
- Local smoke manifest:
  `local/master-patterns/gpu-smoke/forsterite-tiny-gpu.manifest.json`.
  The untouched ebsdsim NPZ SHA-256 is
  `e888f1fe24597319ea6cd7a7257b79a322071a78d485e89e300bcf6cbc584eff`;
  canonical product is `master-531655513a699439`.
- `uv run ruff check src tests` and
  `uv run python scripts/validate_work_items.py`: passed.

## Scientific Decision and Upstream Deviation

COD 9000319 is expressed in non-standard `P b n m`, while ebsdsim 0.1.8
expands space-group 62 in standard `P n m a`. Passing the verbatim CIF directly
produced incorrect resolved multiplicities. The authoritative CIF remains
unchanged; the adapter now creates a deterministic simulation view using
`(a,b,c) -> (b,c,a)` and `(x,y,z) -> (y,z,x)`, records both CIF checksums and
the basis transform, and validates resolved multiplicities `[4,4,4,4,4,8]`.
This is required for correct Mg2SiO4 site weighting and is not a silent source
substitution.

The implementation-plan pseudocode named a module-level
`ebsdsim.mploader.reconstruct_integrated()`, which is not exported by ebsdsim
0.1.8. The adapter uses the corresponding public method on the object returned
by `load_master_pattern()`:
`load_master_pattern(path).reconstruct_integrated()`.
