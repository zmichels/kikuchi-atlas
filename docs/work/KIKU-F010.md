---
id: KIKU-F010
type: feature
title: Establish a portable spherical dictionary fixture
status: done
parent: KIKU-E001
children:
  - KIKU-T043
created: 2026-07-20
priority: P1
tags: [dictionary, spherical, interoperability, provenance]
links:
  - ../../../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md
  - ../../recipes/dictionaries/forsterite-spherical-fixture.yml
evidence:
  - ../../src/kikuchi_lab/dictionary/spherical.py
  - ../../tests/unit/test_spherical_dictionary.py
---

# KIKU-F010: Establish a portable spherical dictionary fixture

## Description

Build a small, deterministic external spherical-dictionary package from the
project's provenance-bearing forsterite S2 intensity field. The package must
exercise the `ebsdx-rs` resource contract without being represented as an
experimentally calibrated EBSD dictionary or as a replacement for the Atlas.

## Acceptance Criteria

- [x] A recipe binds the fixture to one exact cited forsterite S2 source product.
- [x] The published package contains canonical spherical signal data, explicit orientation entries, per-entry patterns, checksums, citation, license, and a deterministic ranking fixture.
- [x] The manifest states the crystal-to-sample convention, right-handed frame, lookup limits, and non-validation boundary.
- [x] Unit tests verify rotations, deterministic ranking, payload layout, and every recorded file checksum.
