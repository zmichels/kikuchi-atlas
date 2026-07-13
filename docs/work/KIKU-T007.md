---
id: KIKU-T007
type: task
title: Define a Symmetry-Distinct Candidate Set
status: done
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [orientation, symmetry, forsterite]
evidence:
  - ../../tests/scientific/test_orientation_candidates.py
  - ../../recipes/proof/forsterite-candidates.yml
  - ../decisions/0002-forsterite-proof-candidate-set.md
---

# KIKU-T007: Define a Symmetry-Distinct Candidate Set

## Description

Define deterministic, crystallographically honest forsterite orientations for
proof comparison without redundant symmetry equivalents.

## Acceptance Criteria

- [x] Candidate-set tests prove stable ordering and symmetry reduction.
- [x] Orientations use active crystal-to-sample Bunge Euler angles in degrees.
- [x] The accepted candidate recipe and reduction evidence are linked here.

## Accepted Evidence

The twelve-candidate recipe is
[forsterite-candidates.yml](../../recipes/proof/forsterite-candidates.yml),
identified as `candidate-set-770010a96a2dbf3e`. The reduction convention,
`0.01` degree tolerance, bounded generation rationale, and non-exhaustive
scope are accepted in
[ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md).

`tests/scientific/test_orientation_candidates.py` proves deterministic IDs
and order, the exact active Bunge-degree convention, direct-lattice `[uvw]`
semantics, explicit `phi1` metadata, metric-aware zone-axis alignment,
literal-false bounded scope, fixed-sample `mmm` disorientation, and stable
serialization. Constructor-mutation and malformed-YAML regressions protect the
owned candidate tuple and strict scientific scalar types. Derived zone-axis
label formatting remains visible in display serialization but is excluded from
scientific identity. All 66 pairs are distinct; the minimum disorientation is
approximately `24.0515` degrees.
