---
id: KIKU-T035
type: task
title: Correct non-orthogonal reflector frames and migrate reviewed Ice selection
status: active
parent: KIKU-F006
depends_on:
  - KIKU-T032
created: 2026-07-17
priority: P1
tags: [crystallography, friedel, ice, migration, selection-manifest]
links:
  - ../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md
  - ../superpowers/plans/2026-07-16-phase-general-direct-reflector-art-series.md
evidence:
  - ../../.superpowers/sdd/task-6-debug-report.md
  - ../../.superpowers/sdd/task-6-frame-repair-report.md
---

# KIKU-T035: Correct non-orthogonal reflector frames and migrate reviewed Ice selection

## Description

Replace the unsafe orix-to-diffsims expansion handoff with alignment-aware
unit-cell expansion and exact symmetry/Friedel magnitude ownership, then retain
the reviewed Ice artifact as immutable legacy evidence while rebinding its same
11 canonical HKLs to corrected content identities without automatic reselection.

## Acceptance Criteria

- [x] Quartz expands to `Si3O6`, Ice Ih to four oxygen sites, and forsterite to its verified 28-atom cell before structure-factor calculation.
- [x] Symmetry-equivalent magnitudes are exact ties and `hkl/-hkl` partners cross thresholds together.
- [x] The reviewed Ice catalog/tattoo artifacts remain unchanged and loadable as legacy products.
- [x] A strict versioned manifest records the reviewed ordered HKLs, orientation, tiers, widths, and legacy identity links.
- [ ] Corrected Ice generation rebinds all 11 HKLs, records the manifest in the new bundle, passes containment, and publishes under new IDs.
- [ ] Focused and full regression suites, Ruff, tracker validation, and retained-product checks pass.
