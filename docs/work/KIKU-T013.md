---
id: KIKU-T013
type: task
title: Define Kinematical Contracts and Recipe
status: done
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [contracts, recipes, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-kikuchipy-kinematical-reference-products.md
  - ../../recipes/kinematical/forsterite-etched-master.yml
  - ../../tests/unit/test_kinematical_contracts.py
---

# KIKU-T013: Define Kinematical Contracts and Recipe

## Description

Add immutable, schema-versioned recipe and array-product contracts for the
project-owned kinematical boundary.

## Acceptance Criteria

- [x] Recipe validation fixes energy, reflection selection, orientation, detector, and output projections explicitly.
- [x] Array products are immutable, finite, hash-addressed, and contain plain metadata only.
- [x] The forsterite recipe is phase-neutral in schema and cites the tracked structure record.
