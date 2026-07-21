---
id: KIKU-T060
type: task
title: Implement and prove Ice Ih canonical S2 cache ranking
status: done
parent: KIKU-F015
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, spherical, ranking, rust, verification]
links:
  - ../dictionaries/ice-ih-ebsdx-rs-contract-crosswalk.md
evidence:
  - ../../../ebsdx-rs/crates/ebsdx-core/src/dictionary_resource.rs
  - ../../../ebsdx-rs/crates/ebsdx-core/tests/spherical_dictionary_resource.rs
---

# KIKU-T060: Implement and prove Ice Ih canonical S2 cache ranking

## Description

Implement a bounded cache-ranking path for an observed canonical spherical
signal. Read the required float32 NPY payloads without silently reshaping,
interpolating, or applying detector preprocessing. Validate behavior against
the immutable Ice Ih held-out package fixture, then expose it via a narrow
`ebsdxr` command.

## Acceptance Criteria

- [x] Unit tests cover normalization, invalid payload rejection, and stable
  ranking ties.
- [x] A CLI integration proof ranks the package's held-out fixture and matches
  the documented top cache entry and score tolerance.
- [x] The command rejects detector-pattern input, implicit runtime geometry,
  and incompatible observed S2 signal width.
- [x] Focused Rust tests, package verification, tracker validation, and the
  real local Ice package preflight/ranking command pass.

## Completion Evidence

The focused Rust suite verifies candidate-row normalization, observed-signal
normalization, deterministic score ties, NPY payload constraints, and exact
direction-grid identity. The real Ice Ih package returned `6952` first with a
score difference below `2e-8` relative to the producer's recorded float32
diagnostic; a mismatched grid was rejected before ranking.
