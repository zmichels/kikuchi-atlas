---
id: KIKU-F015
type: feature
title: Execute canonical spherical dictionary matching in ebsdx-rs
status: done
parent: KIKU-E001
children:
  - KIKU-T060
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, spherical, matching, interoperability, ebsdx-rs]
links:
  - ../dictionaries/ice-ih-ebsdx-rs-contract-crosswalk.md
  - ../../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md
evidence:
  - ../../../ebsdx-rs/crates/ebsdx-core/src/dictionary_resource.rs
---

# KIKU-F015: Execute canonical spherical dictionary matching in ebsdx-rs

## Description

Turn a preflighted spherical dictionary into an executable, canonical-S2
candidate matcher in `ebsdx-rs`. The matcher accepts only an explicitly
sampled spherical signal on the package's exact direction grid, ranks the
verified cache deterministically, and records the dictionary identity. It is
not a detector projection, acquired-pattern indexer, or experimental accuracy
claim.

## Acceptance Criteria

- [x] The consumer loads only authenticated package payloads and rejects
  unsupported NPY shape, dtype, storage order, and direction-count mismatches.
- [x] Observed signals use the declared mean-center/L2 normalization and
  normalized cosine metric with deterministic score/index tie ordering.
- [x] The Ice Ih `v0.1.3` held-out spherical fixture reproduces its documented
  coarse top candidate from the Rust consumer.
- [x] The CLI makes the canonical-S2 input boundary and non-detector claim
  explicit in both text and JSON output.

## Completion Evidence

`ebsdxr dictionary-resource-rank` preflights the immutable Ice Ih `v0.1.3`
package, checks the observed direction-grid NPY against its packaged bytes, and
returns entry `6952` first for the embedded held-out signal at normalized
cosine `0.6117760946`. Replacing the grid with the package quaternion NPY
fails closed. The command accepts canonical S2 signals only; detector
projection and acquired-pattern indexing remain explicitly out of scope.
