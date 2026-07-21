---
id: KIKU-F018
type: feature
title: Prove Ice Ih detector-to-partial-S2 dictionary sampling
status: done
parent: KIKU-E001
children:
  - KIKU-T063
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, detector-geometry, partial-s2, indexing]
links:
  - ../dictionaries/ice-ih-ebsdx-rs-contract-crosswalk.md
  - ../acceptance/ice-ih-detector-to-s2-adapter-proof.md
evidence:
  - ../../scripts/run_ice_ih_detector_to_s2_adapter_proof.py
---

# KIKU-F018: Prove Ice Ih detector-to-partial-S2 dictionary sampling

## Description

Implement an explicit, source-bound detector-to-S2 sampling adapter for the
checked Ice Ih simulated source run. Preserve coverage rather than filling the
unseen sphere, use a distinct masked metric, and demonstrate self-consistent
candidate recovery without presenting it as acquired-pattern performance.

## Acceptance Criteria

- [x] The adapter maps declared sample-frame S2 directions through the exact
  TSL detector geometry, retains a coverage mask, and samples raw detector
  values bilinearly without tone or background processing.
- [x] A same-source detector proof identifies the identity cache candidate
  first and records the score, coverage, geometry, and source hashes.
- [x] The partial-S2 metric and its non-interoperability with the current
  strict full-S2 Rust matcher are stated in docs and output metadata.

## Completion Evidence

The local `ice-ih-detector-to-s2-proof-v0.1.0` bundle covers 308/1,946
directions and ranks cache entry `6577` first at `0.999549817`. Unit tests
verify ray/pixel round trips, backside masking, and coverage-specific ranking.
