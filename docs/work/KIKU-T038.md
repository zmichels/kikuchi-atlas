---
id: KIKU-T038
type: task
title: Build dense Titanite and Zircon retained fields and rotations
status: active
parent: KIKU-F007
depends_on:
  - KIKU-T026
  - KIKU-T036
created: 2026-07-19
priority: P1
tags: [titanite, zircon, kinematical, intensity, near-depth, rotation]
links:
  - ../acceptance/ice-ih-near-depth-stepped.md
  - ../acceptance/titanite-zircon-retained-near-depth.md
evidence:
  - ../../local/runs/kinematical-titanite/kinematical-run-630cf9676428842e/manifest.json
  - ../../local/runs/kinematical-zircon/kinematical-run-fe9afb8f5d8f4ba9/manifest.json
  - ../../local/runs/kinematical-depth-titanite-band-led/near-depth-run-f01977d809458364/manifest.json
  - ../../local/runs/kinematical-depth-zircon-band-led/near-depth-run-b3faf10a1a53d610/manifest.json
  - ../../local/idealized-near-depth-rotation/titanite-x-axis-band-led-v1/manifest.json
  - ../../local/idealized-near-depth-rotation/zircon-x-axis-band-led-v1/manifest.json
  - ../acceptance/titanite-zircon-retained-near-depth.md
---

# KIKU-T038: Build dense Titanite and Zircon retained fields and rotations

## Description

Reuse the established Ice Ih field-led/near-depth method for the existing
Titanite and Zircon source records. Keep their already-published sparse
direct-reflector pieces intact as a separate aesthetic product; this task
adds one denser kinematical field foundation per phase and renders active
sample-frame x-axis rotations from those retained arrays.

## Acceptance Criteria

- [x] Version-controlled base and presentation recipes parse with exact source and recipe identities.
- [x] Titanite and zircon master bundles retain raw stereographic arrays, reflection catalogs, source snapshots, and manifests.
- [x] Near-depth products reuse saved master arrays, retain overlap diagnostics, and preserve the no-spatial-filter contract.
- [x] Each animation has 144 distinct active-field frames at 1024 square pixels, 12 fps, and validates as a 12-second MP4/GIF pair.
- [ ] The dense products are visually reviewed against the Ice Ih near-depth lineage before promotion.
