# Interactive Spherical Master View

- Status: Incubating
- Boundary: additional scientific viewing and exchange surface, not a replacement for projected images or a fabrication-ready mesh

## Motivation

A freely rotatable sphere would make the global topology of Kikuchi bands,
zone-axis intersections, upper/lower hemisphere continuity, and projection
choices easier to understand than any single planar view. It would also provide
an immediate science-art object and a useful bridge toward spherical-harmonic
analysis and print geometry while preserving stereographic, Lambert, and
detector projections as fundamental products.

## Current evidence

- The kinematical design already requires a fixed-camera spherical line/band
  figure plus explicit hemisphere and coordinate ledgers
  ([focused-rendering design](../superpowers/specs/2026-07-13-band-aware-focused-and-diagrammatic-rendering-design.md)).
- Kikuchipy's
  [`KikuchiPatternSimulator.plot(projection="spherical")`](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.simulations.KikuchiPatternSimulator.plot.html)
  provides Matplotlib and optional PyVista spherical geometry paths, while
  [`EBSDMasterPattern.plot_spherical()`](https://kikuchipy.org/en/stable/tutorials/visualizing_patterns.html)
  displays a stereographic master on the 3D sphere. These can support the first
  viewing proof without inventing a second crystallographic projector.
- MTEX documents
  [three-dimensional spherical pole-figure plots](https://mtex-toolbox.github.io/SphericalProjections.html)
  that can be freely rotated, and its
  [spherical-function plotting](https://mtex-toolbox.github.io/S2FunPlotting.html)
  supports both a colored sphere and a radius-displaced surface. These are
  useful interaction and semantics references, not dependencies.
- [Print geometry](print-geometry.md) already separates visualization evidence
  from watertightness, physical units, thickness, and minimum-feature
  requirements.

## Dependencies

- One full-sphere field with explicit upper/lower hemisphere ordering, seam,
  crystal frame, and angular-coordinate conventions.
- A deterministic mapping from kinematical master intensity and/or exact band
  geometry to vertex color, texture coordinates, or optional display-only
  radial displacement.
- A viewer/export contract naming camera, lighting, scalar range, embedded
  provenance, and whether GLB, VTK/VTP, or a local PyVista session is the
  exchange target.
- Separate identities for a viewing mesh and any fabrication mesh.

## Unresolved questions

- Should the first model use vertex colors, an embedded master-pattern texture,
  exact band ribbons, or two switchable layers?
- Should intensity affect color only, or may an explicitly labeled art view
  displace sphere radius as MTEX spherical-function surfaces can?
- Is GLB the preferred openable artifact, with VTP retained as a higher-fidelity
  scientific interchange, or is a local interactive PyVista scene sufficient
  for the first proof?
- How should the Lambert-square hemisphere seam be sampled and validated on a
  continuous sphere?

## Linked decisions and experiments

- The promoted quiet etched-master direction provides the initial grayscale and
  exact-trace style vocabulary for a spherical view.
- [SHT and spherical harmonics](sht-spherical-harmonic.md) records a compact
  continuous-sphere representation that may become useful after the direct
  master-pattern proof.
- [Print geometry](print-geometry.md) owns topology and manufacturability once a
  viewing model is scientifically stable.

## Promotion trigger

Promote when the accepted kinematical bundle contains a validated full-sphere source field and one reviewed export contract names the interactive viewer, exchange format, seam checks, and display-only versus fabrication semantics.

## Present non-goals

- Replacing stereographic, Lambert, detector, or etched-master projected images.
- Treating a GLB or VTP viewing sphere as a watertight, dimensioned print model.
- Adding interactive UI or 3D exchange to the current kinematical acceptance gate.
- Using generated imagery to create scientific band geometry or scalar values.
