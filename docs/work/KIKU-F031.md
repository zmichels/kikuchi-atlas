---
id: KIKU-F031
type: feature
title: Expand the Atlas mineral phase suite
status: active
parent: KIKU-E001
children:
  - KIKU-T081
  - KIKU-T082
  - KIKU-T083
  - KIKU-T084
created: 2026-07-24
priority: P1
tags: [atlas, phases, parity, minerals, provenance]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../atlas/REQUESTED_PHASE_EXPANSION.md
  - ../acceptance/calcite-atlas-parity.md
  - ../acceptance/enstatite-atlas-parity.md
  - ../acceptance/pyrope-atlas-parity.md
evidence:
  - ../../phases/calcite/source.yml
  - ../../phases/enstatite/source.yml
  - ../../recipes/kinematical/calcite-001-atlas-parity-master.yml
  - ../../recipes/kinematical/enstatite-001-atlas-parity-master.yml
  - ../../phases/pyrope/source.yml
  - ../../recipes/kinematical/pyrope-001-atlas-parity-master.yml
  - ../acceptance/pyrope-atlas-parity.md
---

# KIKU-F031: Expand the Atlas mineral phase suite

## Description

Add the requested rock-forming and ore-mineral references without replacing
existing Atlas phases. Each mineral name must resolve to an exact composition,
structure, setting, and cited source before its products can claim parity.

## Acceptance Criteria

- [x] Existing quartz, plagioclase An52, forsterite, diopside, and muscovite
  products remain present and unchanged.
- [ ] Every requested missing mineral has a promoted exact-structure source or
  an explicit blocked/deferred source decision.
- [ ] Every accepted new phase reaches the same source, direct-art,
  kinematical, retained-depth, and printable-globe product families as the
  current Atlas parity phases.
- [ ] Atlas registries and release metadata validate with no unpublished local
  artifact represented as published.
