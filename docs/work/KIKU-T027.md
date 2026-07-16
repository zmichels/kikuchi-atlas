---
id: KIKU-T027
type: task
title: Rotate Ice master on S2 and reproject specimen hemispheres
status: active
parent: KIKU-F003
created: 2026-07-15
priority: P1
tags: [ice-ih, spherical-intensity, orientation, reprojection, visualization]
evidence:
  - ../acceptance/ice-ih-oriented-spherical-master.md
  - ../superpowers/specs/2026-07-15-oriented-spherical-master-design.md
  - ../superpowers/plans/2026-07-16-oriented-spherical-master.md
---

# KIKU-T027: Rotate Ice master on S2 and reproject specimen hemispheres

## Description

Apply the repository's active crystal-to-sample orientation contract to the
Ice Ih directional master field, preserve exact node intensities, and produce
fixed specimen-frame hemisphere and full-sphere views with the field-led
presentation treatment.

## Acceptance Criteria

- [x] Exact oriented S2 nodes preserve source ordering, values, unit norms, and provenance.
- [x] Identity and Bunge `(17, 31, 43)` degree rotations pass inverse and adapter-parity diagnostics.
- [x] Upper/lower hemisphere reprojection uses an explicit inverse spherical mapping with no image rotation or blur.
- [x] The bundle contains identity comparison, both hemispheres, two sphere views, axis diagnostics, and complete ledgers.
- [x] A bounded smoke passes before one 2400-pixel Ice review candidate is produced.
- [ ] The user reviews the oriented figures before promotion beyond presentation-proof status.
