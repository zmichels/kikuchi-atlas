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
evidence:
  - ../superpowers/specs/2026-07-17-ice-reflector-ridge-globes-design.md
---

# KIKU-F006: Ice Ih reflector-defined ridge globes

## Description

Formalize a phase-neutral reflector catalog and analytic spherical raised-band
field, then publish separate Ice Ih intensity-relief and reflector-ridge globe
bundles. The first reflector recipe retains the 15 tie-preserved, strength-
eligible members used by the prior Ice science-art policy.

## Acceptance Criteria

- [ ] A project-owned, phase-neutral catalog preserves Ice source, reflector,
  strength, Bragg-width, selection, and frame provenance without serializing
  upstream simulator objects.
- [ ] The reflector globe derives raised geometry analytically from the 15
  selected Ice bands and never from pixels or vector artwork.
- [ ] Intensity and reflector-ridge Ice products have distinct recipes,
  identities, bundles, and claim boundaries.
- [ ] Every exported mesh is deterministically validated as watertight,
  consistently wound, positive-volume, and a single body.
