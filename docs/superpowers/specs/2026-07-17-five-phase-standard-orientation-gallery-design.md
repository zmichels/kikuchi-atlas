# Five-Phase Standard-Width Orientation Gallery Design

## Purpose

Publish a second, independent science-art family: three physically distinct
active crystal-to-sample orientations for each of Ice Ih, forsterite,
alpha-quartz, zircon, and titanite. The gallery contains fifteen
standard-width vector/raster figures so orientation is the only visual
treatment variable.

This is a presentation-only direct-reflector product. It reuses the retained
orientation-independent catalog evidence and passing parity reports from the
first five-phase family; it does not make a master pattern, infer EBSD
intensities, or modify the reviewed baseline bundles.

## Chosen Approach

Use an explicit, versioned orientation-gallery recipe and a new zero-master
publication workflow. A deterministic preflight resolves an independently
clearance-valid 11-band selection for each phase-orientation cell, then writes
immutable vector-first artifacts and a comparison sheet.

The gallery must rotate the crystallographic reference frame itself:

`normal_sample = orientation_matrix(orientation) @ normal_crystal`.

It must not use a camera-only or post-raster rotation.

## Inputs

- Base policy: `recipes/art/five-phase-hemisphere-series.yml`.
- Direct reflector recipes and immutable source records already referenced by
  that policy.
- Exactly one retained passing parity report per phase, identity-matched to the
  rebuilt direct evidence.
- A new gallery recipe with exactly three named active Bunge ZXZ orientations
  in the `crystal_to_sample` frame.

The final three angles are selected only after a bounded real-catalog
feasibility scan. They must be non-identical, visibly distinct from the first
series orientation, and retained in the gallery recipe rather than generated
at render time.

## Selection and Geometry

- Standard width only: `arc_width_scale = 1.0`.
- Every cell requires exactly 11 selected reflectors with the existing
  dominant/secondary/fine hierarchy, complete circular boundary, and existing
  physical clearance validation.
- Candidate selection remains deterministic and bounded. A selected trace that
  has zero or multiple interior crop fragments is a geometry-feasibility
  conflict: it excludes that member and continues the same bounded search.
- The initial family’s wide-clearance behavior and identities remain unchanged.
  The orientation gallery has its own standard-only search identity and ledger.
- The reviewed Ice standard bundle is a read-only historical reference only;
  it is not substituted into or mutated by this gallery.

## Published Artifacts

One gallery root contains fifteen immutable phase-orientation child bundles
and one comparison bundle:

- per cell: white-background stencil PNG, black-on-white SVG, selection ledger,
  path geometry, catalog snapshot, composition recipe, gallery treatment
  snapshot, and manifest;
- one 3-by-5 comparison PNG rendered directly from vector geometry, with
  orientation labels outside every circular panel;
- a comparison ledger recording cell order, phase, orientation ID, Bunge
  angles, selection ID, geometry ID, renderer version, panel size, source
  catalog, parity-report ID, and `simulation_count: 0`.

All publication is content-addressed, atomic, no-replace, and performed only
after all fifteen cells and the comparison are preflight-valid. The gallery
will not overwrite the existing five-phase standard/wide family.

## Interface

Add:

```text
kikuchi-lab render-phase-art-orientation-gallery \
  --recipe recipes/art/five-phase-standard-orientation-gallery.yml \
  --parity-root local/phase-general-direct-reflector-art/parity \
  --output local/phase-general-direct-reflector-art/orientation-gallery
```

The CLI prints finite work before execution:

```text
phase-art-orientation-gallery finite-work phases=5 orientations=3 cells=15 simulation_count=0
```

## Verification

- Test-first coverage for the new recipe, crop-fragment branch, zero-master
  workflow, exact fifteen-cell inventory, parity identity gate, and no-output
  behavior on preflight failure.
- The real output must prove all fifteen cells use real direct catalogs,
  `simulation_count = 0`, and distinct orientation IDs.
- Open the comparison and representative individual images at native resolution
  for user visual review.
- Run focused gallery tests, relevant direct-art regressions, the full suite,
  Ruff, tracker validation, and `git diff --check`.

## Non-Goals

- No interactive orientation explorer in this slice.
- No wide companions, grayscale treatment, 3D mesh, STL, or tattoo acceptance
  claim for the new variants.
- No camera/image-only rotation, master-pattern simulation, or automatic
  orientation optimization.
