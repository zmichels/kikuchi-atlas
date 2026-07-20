---
id: KIKU-T048
type: task
title: Give diamond the standard direct-reflector orientation set
status: done
parent: KIKU-F011
created: 2026-07-20
priority: P1
tags: [diamond, atlas, core-parity, orientation]
links:
  - ../../phases/diamond/source.yml
  - ../../recipes/reflectors/diamond-art-bands.yml
evidence:
  - ../../scripts/render_phase_art_templates.py
  - ../../docs/atlas/PRODUCT_REGISTRY.yml
---

# KIKU-T048: Give diamond the standard direct-reflector orientation set

## Description

Publish Diamond’s standard, azimuthal-60, oblique-high, and tilt-plus-20
direct-reflector templates from its verified source and saved direct-art
catalog. Register them as ordinary direct-reflector/orientation products, not
tattoo products, so the Atlas visual matrix gains the same core set used by the
other source-backed phases.

## Acceptance Criteria

- [x] Four source-backed diamond SVG templates are published with manifests.
- [x] All four register as direct-reflector and orientation-variation products.
- [x] The Diamond standard template becomes the comparable phase hero.
- [x] Atlas tests/build/tracker validation pass.

## Completion Evidence

- `render_phase_art_templates.py` published the four standard Bunge
  orientations from Diamond’s verified direct-art catalog.
- The Atlas registry names each SVG, bundle, manifest, source recipe, and
  direct-reflector/orientation relation without reintroducing a tattoo family.
- Atlas tests, build, and tracker validation passed.
