---
id: KIKU-T050
type: task
title: Extend source-backed phase parity with intensity and relief studies
status: done
parent: KIKU-F011
created: 2026-07-20
priority: P1
tags: [atlas, intensity, depth, relief, phase-parity]
links:
  - ../atlas/PRODUCT_REGISTRY.yml
evidence:
  - ../../src/kikuchi_lab/spherical_intensity
  - ../../src/kikuchi_lab/reflector_globe
---

# KIKU-T050: Extend source-backed phase parity with intensity and relief studies

## Description

Complete the extension release for all nine source-backed Atlas phases. Each
phase receives a kinematical intensity-master reference, a retained-field
depth-motion study, and an intensity-relief globe. The three products share
one source-backed kinematical master lineage per phase; any pre-existing
dynamical or specialty derivative remains a separately identified richer
product, rather than being silently substituted into the parity set.

## Acceptance Criteria

- [x] Each of the nine source-backed phases has an explicit kinematical recipe,
  retained master bundle, and canonical Lambert-field export.
- [x] Each phase has one provenance-linked depth-field x-axis motion study and
  one intensity-relief globe derived from that phase's canonical field.
- [x] Atlas product-type pages report 9/9 availability for intensity master,
  depth-field motion, and intensity-relief globe, with the kinematical tier
  stated on every parity product.
- [x] Existing dynamical and specialty derivatives remain separately named;
  they are never used as stand-ins for a missing phase.
- [x] Registry, generated Atlas, provenance bundles, and tests remain
  consistent.

## Completion Evidence

- `local/atlas-extension-parity/kinematical/` contains a re-published,
  content-addressed canonical Lambert bundle for each of the nine phases.
  The canonical exporter records any lower-hemisphere in-plane alignment and
  validates an exact shared equator before a spherical field is exposed.
- `local/atlas-extension-parity/depth-motion/` contains nine 144-frame,
  12-second active x-axis motions. They sample retained master and overlap
  fields; no diffraction is recalculated per frame.
- `local/atlas-extension-parity/relief/` contains nine validated 80 mm,
  1.2 mm-maximum outward relief STL bundles. Each records its canonical-master
  identity, interpolation ledger, mesh validation, and preview.
- The generated Atlas reports 9/9 phase availability in each extension family.
