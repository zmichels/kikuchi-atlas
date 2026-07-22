---
id: KIKU-T072
type: task
title: Implement shared-mask detector geometry candidate ranking
status: done
parent: KIKU-F025
created: 2026-07-22
priority: P1
tags: [detector-to-s2, common-mask, geometry-search, verification]
links:
  - ../acceptance/ice-ih-projection-center-cosearch.md
evidence:
  - ../../src/kikuchi_lab/dictionary/geometry_search.py
  - ../../tests/unit/test_detector_geometry_search.py
---

# KIKU-T072: Implement shared-mask detector geometry candidate ranking

## Description

Build the finite candidate search primitive and prove that its selected
geometry and orientation are evaluated with a common S2 support. Package the
Ice Ih PCx/PCy grid, scores, errors, native coverages, common mask, figure, and
checksums.

## Acceptance Criteria

- [x] A small synthetic detector test ranks the true geometry above a shifted
  candidate using the common mask.
- [x] Incompatible detector shapes fail before matching.
- [x] The source-bound co-search fails loudly unless the zero-offset source
  candidate and identity entry are recovered.

## Completion Evidence

Focused tests exercise shared-mask geometry comparison and invalid candidate
sets. The full 81-candidate Ice proof recovers the source geometry and emits a
four-panel visual evidence sheet.
