# Ice-Ih Tattoo Hemisphere Boundary Design

**Status:** implemented; awaiting visual acceptance

**Date:** 2026-07-16

## Purpose

Replace the edge-clipped, rimless presentation of the primary rotated Ice-Ih
tattoo with a complete stereographic hemisphere disc. The final SVG, PDF,
mockup, and stencil must show the whole circular projection boundary and every
crystallographic trace inside it. The result should read as a sphere-like
hemisphere rather than an unbounded network of arcuate lines.

This addendum supersedes only the rimless/open-crop requirements in the
existing Ice art catalog and tattoo design and implementation plan. The
approved 11 crystallographic paths, orientation, tier allocation, path-width
hierarchy, selection evidence, and scientific claim boundaries remain in
force.

## Approved visual contract

- The composition remains centered on a 145.0 mm square artboard.
- A complete circular projection boundary is visible in every primary output.
- The boundary has an exact 132.0 mm **outer** diameter and a 2.2 mm black
  stroke. This leaves 6.5 mm of clear artboard margin on every side.
- The existing 11 crystallographic traces remain exactly 4 dominant, 4
  secondary, and 3 fine paths with their approved ordered widths.
- Each trace is uniformly mapped into the bounded disc without changing its
  projected orientation or relative geometry.
- Every trace ends at the boundary's inner edge. Bands are drawn first and the
  boundary is drawn last so their designed endpoint contacts merge cleanly
  into the limb.
- Nothing extends outside the outer boundary or is clipped by the page.
- The primary treatment remains black ink plus untouched skin only.
- No blur, halo, doubled band edge, node glyph, fake shading, latitude,
  longitude, equator, detector rectangle, or other decorative graticule is
  introduced.

The curved great-circle traces and the enclosing stereographic limb provide
the sphere-like reading. The boundary is intentionally moderate: visually
strong enough to establish the hemisphere, but narrower than the strongest
dominant ribbons.

## Scientific and provenance boundary

The circle is a projection primitive, not a crystallographic reflector. It
must be represented and serialized separately from the 11 `TattooPath`
records, with the explicit role `stereographic_hemisphere_boundary` and the
claim `noncrystallographic_projection_primitive`.

The geometry identity includes the boundary role, outer diameter, width,
center, and coordinate/hash representation. Adding or changing the boundary
therefore creates a new geometry ID and publication run ID without changing
the source catalog, selected member IDs, orientation, normalized center
traces, score ledger, or 4/4/3 tier assignments.

The existing rimless retained bundle remains immutable audit evidence. It is
superseded as the primary visual candidate and is not recorded as the accepted
tattoo geometry.

## Contracts and components

### Boundary contract

Add an immutable boundary value to the art-product contracts. It stores:

- schema version;
- role and scientific-claim classification;
- center `(72.5, 72.5)` mm;
- exact 132.0 mm outer diameter;
- exact 2.2 mm width;
- black ink color; and
- a deterministic identity derived from all serialized fields.

The boundary is not included in the 11-path count or any reflector/member
cohort. A consumer can therefore distinguish measured/simulated
crystallographic structure from projection framing without parsing SVG
semantics.

### Recipe

Replace the tracked rimless flag with an exact projection-boundary mapping.
The strict Ice tattoo recipe accepts only the approved enabled boundary,
dimensions, role, and black palette for this version. The recipe ID changes
and the catalog recipe and catalog identity do not.

### Geometry builder and validator

The builder derives the boundary first, computes its inner-edge radius, and
uniformly maps the already-selected normalized stereographic traces into that
radius. Selection and scoring are not rerun under altered criteria.

Validation requires:

- exactly 11 unique crystallographic paths plus exactly one boundary;
- exact boundary dimensions, center, role, and color;
- every path endpoint on the boundary inner edge within a strict numeric
  tolerance;
- all nonendpoint path coordinates inside the inner edge;
- no page-edge clipping;
- the existing ordered widths, open-path rules, and physical clearances; and
- deterministic geometry identity and serialization.

Boundary endpoint contact is a required designed relationship, not a
noncrossing-clearance violation. Existing true crystallographic crossing and
unrelated-path clearance semantics remain unchanged.

### Vector and raster renderers

The canonical SVG contains exactly 11 open black path elements followed by
one circular boundary primitive. The boundary is drawn last. The PDF and both
PNG derivatives use the same physical coordinates and z-order.

The mockup shows the complete disc on the existing skin palette. The stencil
shows the same complete disc on white. Both remain 1713 by 1713 pixels at
300 dpi, and the PDF remains a physical 145.0 mm square. Outputs remain crisp,
deterministic, and free of timestamps or blur.

### Bundle and ledger

Publication preflight rebuilds the boundary, geometry, SVG, PDF, mockup, and
stencil before filesystem mutation. The inventory and manifest record the new
recipe, geometry, boundary, and run identities. The selection ledger continues
to list only the 11 crystallographic paths; the geometry and publication
ledgers identify the boundary separately.

Atomic no-replace publication remains required. The old rimless bundle is not
deleted or overwritten.

## Failure behavior

Preflight fails before output mutation if the boundary is missing, duplicated,
misclassified as a reflector, off-center, outside its exact dimensions,
nonblack, drawn below the paths, or inconsistent across output formats. It
also fails if a band endpoint misses the inner limb, a trace escapes the disc,
the complete boundary would be page-clipped, or any existing selection,
clearance, identity, disclaimer, or inventory rule is violated.

The gray-wash/dotwork treatment remains blocked until the user explicitly
accepts the regenerated bounded primary geometry.

## Test strategy

Implementation follows test-driven development:

1. Contract tests first prove the immutable, separate boundary identity and
   its exclusion from the 11-path reflector count.
2. Recipe tests first reject the old rimless policy and all wrong boundary
   dimensions, roles, colors, and enablement states.
3. Geometry tests first require exact full-disc placement, endpoint contact,
   containment, unchanged selected path IDs/tiers, and a new geometry ID.
4. SVG tests first require 11 paths plus one final circle, exact z-order, full
   artboard margins, and no extra primitives.
5. PDF/PNG tests first require identical physical geometry, complete visible
   boundary, exact dimensions and palettes, deterministic bytes, and no blur.
6. Bundle tests first reject forged or inconsistent boundary evidence before
   mutation and prove no-replace publication beside the retained rimless
   bundle.
7. A bounded real-Ice integration publishes one new retained candidate and
   verifies unchanged catalog, selected member IDs, orientation, score ledger,
   and tier allocation.

Focused tests, relevant regressions, Ruff, tracker validation, and the full
suite must pass before visual review.

## Acceptance gate

Present the complete bounded mockup and stencil at readable scale. Acceptance
requires the user to confirm:

- the entire outer circle is visible;
- the composition reads as a hemisphere or sphere-like projection;
- the moderate limb supports rather than overpowers the ribbon hierarchy;
- band-to-boundary contacts look intentional and clean; and
- the dense crystallographic crossings remain aesthetically acceptable.

Only that later visual acceptance closes KIKU-T029 and permits the secondary
gray-wash/dotwork treatment to begin.
