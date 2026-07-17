---
id: KIKU-T025
type: task
title: Define habit recipe and quartz reference source
status: done
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- recipe
- cif
- provenance
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T025: Define habit recipe and quartz reference source

## Description

Define the immutable habit recipe, tracked public-domain quartz CIF, explicit
support distances, source hash, and content-derived recipe identity.

## Acceptance Criteria

- [x] Quartz CIF bytes and public-domain provenance are tracked with the reviewed SHA-256.
- [x] The recipe validates Miller convention, support distances, target millimetres, and optional FDM context.
- [x] Recipe identity includes semantic content and CIF bytes without machine-local paths.

## Accepted Evidence

- `phases/quartz/COD-9000775.cif`, `recipes/habits/quartz-mtex-example.yml`,
  and `tests/unit/habit/test_habit_recipes.py`.
- The reviewed CIF SHA-256 is
  `10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57`.
