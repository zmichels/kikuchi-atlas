---
id: KIKU-T082
type: task
title: Build and publish calcite parity products
status: done
parent: KIKU-F031
children: []
created: 2026-07-24
priority: P1
tags: [atlas, calcite, parity, products]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../acceptance/calcite-atlas-parity.md
evidence:
  - ../../phases/calcite/source.yml
  - ../../recipes/reflectors/calcite-art-bands.yml
  - ../../recipes/kinematical/calcite-001-atlas-parity-master.yml
  - ../acceptance/calcite-atlas-parity.md
---

# KIKU-T082: Build and publish calcite parity products

## Description

Use the 295 K COD calcite reference to prove the expansion workflow through
the same direct-reflector, retained kinematical-field, and printable geometry
families used by the newest Atlas phases.

## Acceptance Criteria

- [x] The exact CIF, checksum, citation, setting, sites, occupancies, and
  thermal-factor policy verify against a tracked source record.
- [x] Direct-art catalog, parity report, four orientation templates, and
  rotation product are built and checksum-bound.
- [x] Kinematical master, near-depth product, retained-field rotation, ridge
  globe, and intensity-relief globe are built and validated.
- [x] Calcite products are added to the Atlas product registry only after
  their local bundles exist and verify.

## Completion Evidence

See `docs/acceptance/calcite-atlas-parity.md`. The tenth-phase Atlas build has
104 available products and retains all nine earlier phase records.
