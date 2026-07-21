---
id: KIKU-T057
type: task
title: Validate Ice Ih dictionary against the ebsdx-rs resource contract
status: done
parent: KIKU-F013
depends_on:
  - KIKU-T054
  - KIKU-T055
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, interoperability, ebsdx-rs, contract]
links:
  - ../dictionaries/ice-ih-ebsdx-rs-contract-crosswalk.md
  - ../../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md
evidence:
  - ../../src/kikuchi_lab/dictionary/ice_ih.py
  - ../../recipes/dictionaries/ice-ih-spherical-candidate-v0.1.3.yml
  - ../../../ebsdx-rs/crates/ebsdx-core/src/dictionary_resource.rs
  - ../../../ebsdx-rs/crates/ebsdx-core/tests/spherical_dictionary_resource.rs
---

# KIKU-T057: Validate Ice Ih dictionary against the ebsdx-rs resource contract

## Description

Close the producer/consumer handoff without smuggling in a detector model.
Identify which canonical-package fields already satisfy the draft resource
contract, which require a concrete manifest extension, and what an eventual
`ebsdx-rs` adapter must receive at runtime.

## Acceptance Criteria

- [x] A field-level crosswalk records the actual `v0.1.3` state and explicit
  nonclaims against the local consumer contract.
- [x] The package manifest supplies every detector-independent field required
  for consumer preflight, including phase and coverage detail.
- [x] A consumer-side lint accepts the sealed package and rejects missing
  runtime detector geometry or unnamed preprocessing.
- [x] The package and consumer test retain the exact S2 grid, active `wxyz`
  crystal-to-sample convention, and normalized-cosine preprocessing.

## Accepted Evidence

`ebsdxr dictionary-resource-preflight` independently authenticated
`ice-ih-spherical-dictionary-3ef073c780b83778`: the 13,155 orientation
entries, 1,946 S2 directions, and all 10 manifest-inventoried files passed.
It accepts a named runtime recipe schema and rejects `--require-runtime` calls
without one. The resource distinguishes its crystal-frame canonical master
from its sample-frame cache directions; no detector projection or indexing
result is claimed.
