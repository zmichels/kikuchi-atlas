---
id: KIKU-F025
type: feature
title: Compare finite Ice Ih detector geometry candidates on shared support
status: done
parent: KIKU-E001
children:
  - KIKU-T072
created: 2026-07-22
priority: P1
tags: [ice-ih, detector-geometry, projection-center, candidate-search, calibration]
links:
  - ../acceptance/ice-ih-projection-center-cosearch.md
evidence:
  - ../../src/kikuchi_lab/dictionary/geometry_search.py
---

# KIKU-F025: Compare finite Ice Ih detector geometry candidates on shared support

## Description

Add a reusable finite detector-geometry candidate ranker. It samples each
candidate geometry from the same detector field, intersects their S2 coverage
masks, and only then compares dictionary scores. Demonstrate the pattern with
a deliberate Ice Ih PCx/PCy co-search proof.

## Acceptance Criteria

- [x] Candidate geometry scores use a shared coverage mask rather than their
  individually varying detector footprints.
- [x] The implementation rejects empty or incompatible detector candidate sets
  and preserves stable candidate ordering for ties.
- [x] A local 81-candidate Ice proof recovers the source-declared PC and
  nominal orientation while retaining all non-calibration boundaries.

## Completion Evidence

The shared-mask proof retains 231 common directions across 81 PC candidates
and chooses the zero-offset source geometry with identity entry `6577` first.
The figure also records why candidate-native coverage remains diagnostic rather
than a score-comparison basis.
