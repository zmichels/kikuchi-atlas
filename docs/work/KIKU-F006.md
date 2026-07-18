---
id: KIKU-F006
type: feature
title: Ice Ih reflector-defined ridge globes
status: ready
parent: KIKU-E001
children: []
created: 2026-07-17
priority: P1
tags: [ice-ih, reflectors, relief, mesh, stl, science-art]
links:
  - ../superpowers/specs/2026-07-17-ice-reflector-ridge-globes-design.md
  - ../superpowers/plans/2026-07-17-ice-reflector-ridge-globes.md
evidence:
  - ../superpowers/specs/2026-07-17-ice-reflector-ridge-globes-design.md
  - ../acceptance/ice-ih-reflector-ridge-globe.md
  - ../acceptance/ice-ih-intensity-relief-globe.md
---

# KIKU-F006: Ice Ih reflector-defined ridge globes

## Description

Formalize a phase-neutral reflector catalog and analytic spherical raised-band
field, then publish separate Ice Ih intensity-relief and reflector-ridge globe
bundles. The first reflector recipe retains the 15 tie-preserved, strength-
eligible members used by the prior Ice science-art policy.

## Acceptance Criteria

- [x] A project-owned, phase-neutral catalog preserves Ice source, reflector,
  strength, Bragg-width, selection, and frame provenance without serializing
  upstream simulator objects.
- [x] The reflector globe derives raised geometry analytically from the 15
  selected Ice bands and never from pixels or vector artwork.
- [x] Intensity and reflector-ridge Ice products have distinct recipes,
  identities, bundles, and claim boundaries.
- [x] Every exported mesh is deterministically validated as watertight,
  consistently wound, positive-volume, and a single body.
- [ ] An explicit user review accepts the generated fixed previews for visual
  readability.
- [ ] External slicer ingestion and any physical-print assessment are recorded
  separately; neither is implied by automated mesh validation.

## Acceptance evidence and remaining gates

Both published bundles have recorded source, catalog or master, build, field,
topology, SHA-256 inventory, physical bounds, and post-serialization mesh
validation evidence in their acceptance ledgers. The product boundaries are
explicit: the reflector globe is analytic catalog-derived ridges, while the
intensity globe samples the raw kinematical master. `KIKU-F006` remains
`ready` solely for explicit user preview review and optional external slicer or
physical-print gates; those gates are not claimed complete.
