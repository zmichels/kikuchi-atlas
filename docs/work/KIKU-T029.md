---
id: KIKU-T029
type: task
title: Publish primary Ice Ih tattoo geometry
status: active
parent: KIKU-F005
created: 2026-07-16
priority: P1
tags: [ice-ih, science-art, tattoo, vector, visual-review]
links:
  - ../superpowers/specs/2026-07-16-ice-art-globe-and-tattoo-design.md
  - ../superpowers/plans/2026-07-16-ice-art-catalog-and-tattoo.md
  - ../superpowers/specs/2026-07-16-ice-tattoo-hemisphere-boundary-design.md
  - ../superpowers/plans/2026-07-16-ice-tattoo-hemisphere-boundary.md
evidence:
  - ../superpowers/plans/2026-07-16-ice-art-catalog-and-tattoo.md
  - ../superpowers/plans/2026-07-16-ice-tattoo-hemisphere-boundary.md
  - ../acceptance/ice-ih-tattoo-primary.md
---

# KIKU-T029: Publish primary Ice Ih tattoo geometry

## Description

Select and publish the deterministic 145 mm black/skin Ice Ih tattoo geometry
from actively rotated catalog normals and projected great-circle center traces,
within a complete stereographic hemisphere boundary and with no image-derived
edges or node embellishments.

## Acceptance Criteria

- [x] The approved orientation deterministically selects 11 unique catalog members in the fixed dominant, secondary, and fine allocation.
- [x] Physical vector geometry satisfies the prescribed widths, crop, noncrossing gap, endpoint-clearance, and black/skin-only constraints.
- [x] The complete 132.0 mm stereographic hemisphere boundary is serialized and identified separately as a noncrystallographic projection primitive, never as a twelfth reflector.
- [x] The full-disc SVG, PDF, mockup, and stencil retain the whole boundary on the 145 mm artboard with all path contacts inside it.
- [x] SVG, PDF, mockup, stencil, ledgers, diagnostics, disclaimer, and manifest publish atomically with reproducible identities.
- [ ] The user explicitly accepts the primary geometry before this task is marked done or any secondary treatment begins.
