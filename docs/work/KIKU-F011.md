---
id: KIKU-F011
type: feature
title: Build phase-parity products across the Kikuchi Atlas
status: done
parent: KIKU-E001
children:
  - KIKU-T048
  - KIKU-T049
  - KIKU-T050
created: 2026-07-20
priority: P1
tags: [atlas, phase-parity, provenance, direct-reflector]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../atlas/PRODUCT_REGISTRY.yml
  - ../atlas/README.md
evidence:
  - ../../src/kikuchi_lab/atlas/catalog.py
  - ../../scripts/render_phase_art_templates.py
---

# KIKU-F011: Build phase-parity products across the Kikuchi Atlas

## Description

Bring every Atlas phase toward the same source-backed product vocabulary. Core
parity means a direct-reflector orientation set, x-axis motion study, and
reflector-ridge globe; extensions remain separately labeled intensity, depth,
and relief products. Candidate phases may not receive rendered products until
their named CIF records are promoted and verified.

## Acceptance Criteria

- [x] Every tracked-source phase has the full core visual product set.
- [x] Each candidate phase is either transparently blocked or promoted through a verified source record before rendering.
- [x] Extension products preserve their stated simulation/geometry boundaries and do not substitute for core parity.
- [x] Registry, generated Atlas, provenance bundles, and tests remain consistent.

## Progress Evidence

- The Atlas core now includes the same direct-reflector orientation set,
  x-axis motion study, and reflector-ridge globe for all nine tracked phases.
- The three former intake candidates were promoted through exact CIF records;
  An52 uses a tested primitive-cell transform, while muscovite retains its
  measured mixed site occupancies.
- KIKU-T050 adds a nine-phase kinematical extension baseline: canonical Lambert
  masters, retained-field x-axis motion, and validated intensity-relief globes.
  Existing dynamical and specialty products remain separately identified.
