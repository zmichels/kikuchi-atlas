---
id: KIKU-T079
type: task
title: Pin and validate the Ni Hough preprocessing-variant protocol
status: done
parent: KIKU-F030
children: []
created: 2026-07-24
priority: P1
tags: [nickel, hough, preprocessing, recipe, testing]
links:
  - ../../recipes/reference-pack/ni-gain24db-preprocessing-sensitivity-v0.1.yml
evidence:
  - ../../src/kikuchi_lab/reference_pack/ni_hough.py
  - ../../tests/unit/test_ni_hough.py
---

# KIKU-T079: Pin and validate the Ni Hough preprocessing-variant protocol

## Description

Define the three-variant protocol and isolate the aggregate diagnostic summary
from the runtime-specific Hough implementation so input validation and report
semantics are tested directly.

## Acceptance Criteria

- [x] The compact summary validates dimensions and finite metric values.
- [x] The recipe fixes source, geometry, reflectors, variant order, expected
  results, and all comparison boundaries.

## Completion Evidence

Unit tests cover aggregate calculation and malformed metric vectors; the actual
study enforces the recipe's expected result values before publication.
