# Print Geometry

- Status: Incubating
- Boundary: derived, labeled geometry products, not simulated intensity truth

## Motivation

Kikuchi-band organization is well suited to tactile and sculptural forms,
including planar reliefs, spherical shells, cutouts, and light-transmitting
objects. A print pipeline could translate a scientifically traced scalar field
or a separately labeled diagrammatic band representation into watertight,
manufacturable geometry.

## Current evidence

- The artifact bundle retains immutable float arrays, diagnostics, and explicit
  quantization mappings suitable as source evidence for later geometry
  derivation ([ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)).
- The aesthetic catalog describes a user-supplied tetragonal spherical STL as
  a valid 57,800-triangle shell with modest relief and no degenerate triangles;
  its units and license remain unverified
  ([aesthetic-clarity.yml](../../reference/catalog/aesthetic-clarity.yml)).
- [ADR 0003](../decisions/0003-clarity-aesthetic-target.md) explicitly keeps
  spherical and print products outside the planar final-pattern contract.
- The approved [crystal-habit mesh generator design](../superpowers/specs/2026-07-17-crystal-habit-mesh-generator-design.md)
  and [KIKU-F004](../work/KIKU-F004.md) promote a direct-morphology mesh spine
  using a quartz habit proof. That work establishes shared scale, triangulation,
  validation, export, and provenance components, but it does not promote an
  intensity-derived or diagrammatic Kikuchi relief product.

## Dependencies

- A named mapping from canonical intensity or diagrammatic band evidence to
  height, thickness, or shell displacement.
- Mesh validation for watertightness, orientation, self-intersections, minimum
  feature size, relief range, and printer-scale units.
- Separate provenance and labeling for intensity-derived versus
  geometry-derived products.

## Unresolved questions

- For the Kikuchi-derived product, should the first printable artifact be a
  full sphere or a spherical segment? The separately promoted direct habit
  solid does not answer this relief-specific choice.
- Does readable geometry require a continuous master-pattern map, extracted
  band centerlines, or a multiscale blend of both?
- Which physical size, material, process, and relief limits should define the
  first manufacturability contract?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) provides
  source-array and derived-artifact identity concepts.
- [ADR 0003](../decisions/0003-clarity-aesthetic-target.md) records the
  reference STL observation and present planar scope.
- [SHT and spherical harmonics](sht-spherical-harmonic.md) records a possible
  future route to continuous spherical source fields.
- [Interactive spherical view](interactive-spherical-view.md) separates an
  openable viewing model from topology- and unit-constrained print geometry.
- [KIKU-F004](../work/KIKU-F004.md) tracks the direct crystal-habit generator
  and shared mesh spine without changing this record's relief semantics.

## Promotion trigger

Promote when one labeled source field and one target fabrication process have explicit scale, relief, topology, and minimum-feature acceptance tests.

## Present non-goals

- Copying or redistributing the reference STL.
- Assuming its unverified units or relief ratio are correct for forsterite.
- Converting an 8-bit preview directly into authoritative geometry.
- Adding STL or other print output to milestone-one acceptance.
