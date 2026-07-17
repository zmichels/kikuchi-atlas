---
id: KIKU-T033
type: task
title: Onboard quartz zircon and titanite reflector catalogs
status: done
parent: KIKU-F006
depends_on:
  - KIKU-T032
  - KIKU-T035
created: 2026-07-16
priority: P1
tags: [quartz, zircon, titanite, provenance, parity]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
  - ../superpowers/plans/2026-07-16-phase-general-direct-reflector-art-series.md
evidence:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
  - ../acceptance/phase-general-direct-reflector-art-series.md
  - ../acceptance/quartz-zircon-titanite-direct-catalogs.md
---

# KIKU-T033: Onboard quartz zircon and titanite reflector catalogs

## Description

Add cited, checksum-verified, setting-explicit structure records for alpha-quartz,
stoichiometric zircon, and stoichiometric monoclinic titanite, then validate one
bounded direct-versus-simulator reflector parity proof for each phase.

Onboarded source identities are `COD-9012600`,
`COD-9000684-isotropic-U`, and `COD-9000509`. Zircon records the explicit
origin-choice-2 to choice-1 offset; titanite records the exact P21/a to P21/c
axis/coordinate mapping and the non-integer-orbit fallback boundary.

## Acceptance Criteria

- [x] Each source record identifies license, checksum, cell setting, sites, occupancies, thermal treatment, transformations, and limitations.
- [x] Structural validation and reflection/systematic-absence checks pass for all three phases.
- [x] Each phase retains one bounded onboarding parity diagnostic without automatic retry or resolution growth.
- [x] Every phase publishes an orientation-independent, provenance-bearing art-band catalog with at least 11 defensible axial candidates.
