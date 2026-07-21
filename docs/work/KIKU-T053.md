---
id: KIKU-T053
type: task
title: Define the Ice Ih dictionary profile and claim boundary
status: done
parent: KIKU-F013
created: 2026-07-20
priority: P0
tags: [ice-ih, dictionary, design, provenance]
links:
  - ../decisions/0005-ice-ih-dictionary-flagship.md
  - ../dictionaries/ice-ih-flagship-design.md
evidence:
  - ../../phases/ice-ih/source.yml
  - ../../recipes/kinematical/ice-ih-oxygen-quiet-proof.yml
---

# KIKU-T053: Define the Ice Ih dictionary profile and claim boundary

## Description

Choose the first useful Ice Ih dictionary representation before generating a
large cache. Bind the work to the average oxygen-sublattice source, a
symmetry-reduced spherical candidate cache, retained full-master refinement,
and explicit detector/acquisition exclusions.

## Acceptance Criteria

- [x] The phase is named as Ice Ih average oxygen sublattice in `P 63/m m c`
  (No. 194), rather than an unspecified generic ice phase.
- [x] Candidate cache sampling, full-master refinement, and the no-hidden
  detector-adapter boundary are explicit.
- [x] Synthetic retrieval is identified as the first validation rung, with no
  claim of acquired-pattern indexing accuracy.
