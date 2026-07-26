---
id: KIKU-T083
type: task
title: Build and publish orthoenstatite parity products
status: done
parent: KIKU-F031
children: []
created: 2026-07-24
priority: P1
tags: [atlas, enstatite, orthopyroxene, parity, products]
links:
  - ../atlas/PHASE_REGISTRY.yml
  - ../acceptance/enstatite-atlas-parity.md
evidence:
  - ../../phases/enstatite/source.yml
  - ../../recipes/reflectors/enstatite-art-bands.yml
  - ../../recipes/kinematical/enstatite-001-atlas-parity-master.yml
  - ../acceptance/enstatite-atlas-parity.md
---

# KIKU-T083: Build and publish orthoenstatite parity products

## Description

Promote the 0 GPa COD orthoenstatite reference through the same
direct-reflector, retained kinematical-field, and printable geometry families
used by the current Atlas parity phases.

## Acceptance Criteria

- [x] The exact CIF, checksum, citation, setting, sites, occupancies, and
  thermal-factor policy verify against a tracked source record.
- [x] Direct-art catalog, parity report, four orientation templates, and
  rotation product are built and checksum-bound.
- [x] Kinematical master, near-depth product, retained-field rotation, ridge
  globe, and intensity-relief globe are built and validated.
- [x] Enstatite products are added to the Atlas product registry only after
  their local bundles exist and verify.

## Completion Evidence

See `docs/acceptance/enstatite-atlas-parity.md`. The eleven-phase Atlas build
has 113 available products and retains all ten earlier phase records.
