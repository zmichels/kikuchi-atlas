---
id: KIKU-F013
type: feature
title: Build the Ice Ih flagship spherical dictionary
status: done
parent: KIKU-E001
children:
  - KIKU-T053
  - KIKU-T054
  - KIKU-T055
  - KIKU-T057
created: 2026-07-20
priority: P0
tags: [ice-ih, dictionary, indexing, spherical, interoperability]
links:
  - ../decisions/0005-ice-ih-dictionary-flagship.md
  - ../dictionaries/ice-ih-flagship-design.md
  - ../../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md
evidence:
  - ../../phases/ice-ih/source.yml
  - ../../recipes/kinematical/ice-ih-oxygen-quiet-proof.yml
---

# KIKU-F013: Build the Ice Ih flagship spherical dictionary

## Description

Make Ice Ih the first genuinely useful scientific dictionary line: a
provenance-bound, symmetry-reduced spherical candidate cache tied to the full
Ice master and capable of transparent synthetic retrieval/refinement tests.
Keep the dictionary reusable across future detector adapters without claiming
that it is already calibrated against acquired EBSD patterns.

## Acceptance Criteria

- [x] The Ice Ih flagship choice, oxygen-sublattice boundary, two-level
  architecture, and explicit nonclaims are recorded in an ADR and design.
- [x] A 5-degree `6/mmm`-reduced SO(3) cache is generated from the checked raw
  Ice master with a portable manifest and checksum inventory.
- [x] The cache matcher emits ranked candidate orientations and supports a
  declared full-master local refinement path.
- [x] Held-out synthetic recovery demonstrates the full coarse-to-refined
  retrieval path, including score and angular-error diagnostics.
- [x] The package can be independently verified against the local
  `ebsdx-rs` dictionary-resource contract without a hidden detector model.

## Progress Evidence

- `local/dictionaries/ice-ih-spherical-candidate-v0.1.0` is the first sealed
  13,155-by-1,946 float32 candidate cache from the checked Ice master.
- `local/dictionaries/ice-ih-spherical-recovery-proof-v0.1.0` records a
  held-out 3.54-degree synthetic rotation: coarse retrieval reached 2.30
  degrees and full-master local refinement reached 0.46 degrees.
- `local/dictionaries/ice-ih-spherical-candidate-v0.1.3` embeds that recovery
  fixture, recomputes it during verification, and labels the crystal-frame
  master separately from the sample-frame candidate directions. It also adds
  the draft contract's detector-independent metadata. `ebsdxr
  dictionary-resource-preflight` independently checks the sealed package and
  requires explicit runtime inputs before a future matcher can proceed.
