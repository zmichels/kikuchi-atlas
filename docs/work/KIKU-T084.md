---
id: KIKU-T084
type: task
title: Build and publish pyrope parity products
status: done
parent: KIKU-F031
children: []
created: 2026-07-25
priority: P1
tags: [atlas, pyrope, garnet, parity, products]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../acceptance/pyrope-atlas-parity.md
evidence:
  - ../../phases/pyrope/source.yml
  - ../../recipes/reflectors/pyrope-art-bands.yml
  - ../../recipes/kinematical/pyrope-001-atlas-parity-master.yml
  - ../acceptance/pyrope-atlas-parity.md
---

# KIKU-T084: Build and publish pyrope parity products

## Description

Promote the 298.15 K COD pyrope Mg endmember through the same direct-reflector,
retained kinematical-field, animation, and printable-geometry families used by
the current Atlas parity phases.

## Acceptance Criteria

- [x] The exact source CIF and deterministic derivative verify their checksums,
  citation, Ia-3d setting, sites, implicit full occupancies, and thermal-factor
  policy.
- [x] Direct-art catalog, simulator-parity report, four orientation templates,
  and direct x-axis rotation are built and checksum-bound.
- [x] Kinematical master, near-depth product, retained-field rotation,
  reflector-ridge globe, and intensity-relief globe are built and validated.
- [x] All nine pyrope product records are registered only after their local
  media, preview, bundle, provenance, and recipe paths exist and validate.

## Completion Evidence

See `docs/acceptance/pyrope-atlas-parity.md`. The twelve-phase Atlas build has
122 available products and retains all eleven earlier phase records.
