---
id: KIKU-T049
type: task
title: Promote candidate phase CIFs before all-phase core rendering
status: done
parent: KIKU-F011
created: 2026-07-20
priority: P1
tags: [plagioclase, muscovite, diopside, sources, provenance]
links:
  - ../atlas/PHASE_REGISTRY.yml
evidence:
  - ../../src/kikuchi_lab/sources/structure.py
---

# KIKU-T049: Promote candidate phase CIFs before all-phase core rendering

## Description

Fetch, pin, and verify the exact An52 plagioclase, 2M1 muscovite, and ambient
diopside CIFs named by the Atlas. Resolve any centering, setting, and
mixed-occupancy adapter requirements before classifying them as tracked sources
or rendering their direct-reflector products.

## Acceptance Criteria

- [x] Each source record pins its exact CIF, checksum, licensing, citation, and simulation-relevant structure values.
- [x] Source verification tests cover the stated centering, setting, or mixed-occupancy concerns.
- [x] Atlas candidate records change state only after the corresponding source proof passes.
- [x] Each promoted phase has accepted direct-reflector evidence before its core product publication.

## Completion Evidence

- Checked-in sources: COD-8103560 (An52 plagioclase), COD-9014960
  (2M1 muscovite), and COD-1000007 (ambient diopside).
- Source tests verify checksums and asymmetric-unit expansion. The An52
  C-centered triclinic structure is converted through an explicit
  half-volume primitive basis; muscovite's mixed K/Na, Al/Fe/Mg, and Al/Si
  sites remain explicit.
- Each phase has a zero-master direct-reflector evidence/catalog bundle before
  its four orientation products, x-axis study, and reflector-ridge globe were
  registered.
