---
title: Oriented Spherical Master and Hemisphere Reprojection Design
date: 2026-07-15
status: approved
project_prefix: KIKU
task: KIKU-T027
depends_on: [KIKU-F002, KIKU-T026]
---

# Oriented Spherical Master and Hemisphere Reprojection Design

## Purpose

Rotate the Ice Ih kinematical master as a directional scalar field on the unit
sphere, then render that oriented field as fixed specimen-frame hemispheres and
full-sphere views. The operation must move the reflector/band network under an
explicit crystal orientation. It must not imitate orientation variation by
rotating a flat image, moving only the camera, or changing detector geometry.

The first proof deliberately reuses the recent Ice Ih field-led aesthetic. Ice
is held fixed as the phase so that orientation is the only scientific variable
in the identity-versus-rotated comparison. The selected non-special orientation
is active crystal-to-sample Bunge ZXZ Euler `(17, 31, 43)` degrees, already used
by the repository's kikuchipy orientation-parity tests.

## Decisions

1. The canonical source is the both-hemisphere Ice Ih crystal-frame master, not
   a rendered PNG.
2. The repository's existing `Orientation` contract remains authoritative:
   active crystal-to-sample Bunge ZXZ Euler angles in degrees.
3. Exact source directions are rotated into specimen coordinates without
   changing their attached intensity values.
4. Fixed specimen-frame hemisphere images use inverse spherical reprojection,
   not a two-dimensional image transform.
5. The exact-node rotated field is authoritative. Raster hemispheres and sphere
   meshes are named display derivatives.
6. Raw scientific intensity is immutable. Field-led presentation luminance is
   a separately identified derivative.
7. Both center and boundary vector-overlay layers remain disabled. Visible
   bands come from the master and exact band-overlap treatment.
8. Identity and `(17, 31, 43)` degree outputs are produced together so inverse,
   frame, and display errors remain visible.
9. The first implementation is Python-owned and does not require MTEX.
10. Detector projection, texture accumulation, interactive 3D, quartz, and an
    orientation gallery remain outside this slice.

## Frame and Rotation Contract

Crystal directions use the frame recorded by the Ice master. Specimen
directions use the repository's EDAX-TSL sample ordering:

```text
x = RD
y = TD
z = ND
```

For public orientation `g`, construct the active rotation with the existing
orix convention:

```python
G_cs = Rotation.from_euler(
    g.euler_bunge_deg,
    degrees=True,
    direction="crystal2lab",
)
```

An exact crystal-frame direction `c` moves into the specimen frame as:

```text
s = G_cs c
```

The fixed specimen-frame display is the pullback of the crystal field:

```text
I_sample(s) = I_crystal(G_cs^-1 s)
```

The identity orientation must reduce both equations to exact array identity.
The ledger stores Euler angles, units, direction, input and output frame names,
the orientation ID, rotation matrix, inverse matrix, determinant, quaternion,
and implementation owner/version. It also records the precise `RD, TD, ND`
axis ordering.

## Architecture

```text
Ice both-hemisphere crystal-frame master
                  |
                  v
       canonical SphericalIntensityField
                  |
          +-------+-------------------+
          |                           |
          v                           v
 rotate exact xyz by G_cs      evaluate field-led source channels
          |                           |
          +-------------+-------------+
                        v
          OrientedSphericalIntensityField
                 exact specimen xyz
                        |
          +-------------+----------------+
          |                              |
          v                              v
 fixed specimen directions       full-sphere display mesh
          |                              |
 inverse map by G_cs^-1                  |
          |                              |
 sample crystal field                    |
          +--------------+---------------+
                         v
       hemisphere, sphere, and axis-diagnostic figures
```

The Python rotation core owns frame validation, exact-node transformation,
hashes, and invariants. The reprojection adapter owns specimen display grids,
inverse mapping, source-hemisphere selection, and interpolation. The renderer
owns only display composition. No renderer mutates or silently replaces a
scientific field.

## Product Contracts

### Oriented exact-node field

`OrientedSphericalIntensityField` contains:

- specimen-frame `xyz` for every canonical source node;
- unchanged raw intensity, normalized intensity, and density weight arrays;
- unchanged source row, column, and source-hemisphere provenance;
- source field/product identity and hashes;
- orientation identity and complete frame ledger; and
- separate hashes for rotated coordinates and unchanged value channels.

Node ordering remains identical to the source field. Therefore the intensity
and weight byte hashes must be identical before and after orientation, while
the coordinate hash must differ for every non-identity orientation. A
compressed NPZ and plain JSON ledger are the durable first-proof interchange.
CSV duplication is not required for the high-resolution Ice review bundle.

### Presentation luminance

The recent field-led aesthetic is a named presentation-only channel, not a
replacement for raw master intensity. At a crystal direction `c` it combines:

1. the existing pointwise asinh tone mapping of master intensity; and
2. the existing exact additional-band-overlap optical-depth treatment.

Overlap membership is evaluated in crystal coordinates before orientation (or,
equivalently, at `G_cs^-1 s` for a specimen display direction). It uses the
same reflector threshold, axial band membership, strength weights,
normalization, gain `0.38`, and luminance ceiling `0.985` as the current
field-led Ice recipe. No vector center or boundary paths are drawn.

The presentation ledger records `scientific_claim: presentation_only`,
`spatial_filter: none`, and the interpolation mode independently of the raw
field ledger.

## Hemisphere Reprojection

For each pixel inside a fixed upper or lower specimen-frame stereographic
disk:

1. convert the pixel coordinate to unit specimen direction `s` through orix's
   public inverse stereographic projection;
2. compute `c = G_cs^-1 s`;
3. select the crystal upper or lower source array from the sign of `c.z` using
   the source equator policy;
4. stereographically project `c` into the selected source array; and
5. evaluate source intensity by recorded linear interpolation between exact
   source nodes.

Linear interpolation here is spherical reprojection between simulator nodes.
It is not a convolution, denoising pass, glow, or blur. Identity orientation
uses exact source-grid correspondence and must reproduce the source numeric
arrays without interpolation error. Work is evaluated in bounded row tiles so
the 2400-pixel render does not allocate an unbounded pixel-by-channel cube.

Directions outside the valid source disk, non-finite coordinates, ambiguous
hemisphere ownership, and inverse-mapping failures are fatal. The workflow
does not fill holes by neighborhood smoothing.

## Full-Sphere Display

The sphere renderer evaluates a deterministic longitude/latitude mesh in the
specimen frame, inverse maps each mesh direction to the crystal field, and
colors the mesh from the selected channel. Fixed camera views change only how
the already oriented specimen-frame sphere is seen; they do not define the
orientation.

The first bundle contains two complementary fixed sphere views. Axis markers
show specimen `RD`, `TD`, and `ND` together with the oriented crystal `[100]`,
`[010]`, and `[001]` directions. The axis coordinates must be generated by the
same transform used by the detector-projection adapter.

Interactive HTML, GLB, texture, and print geometry are parked follow-ons. The
exact oriented NPZ is intended to support them without another scientific
transformation.

## Visual Bundle

The first review bundle contains:

1. identity versus oriented upper stereographic hemispheres;
2. oriented upper and lower specimen-frame hemispheres;
3. two full-sphere fixed views using the same field-led channel;
4. an orientation-axis diagnostic; and
5. raw/source, orientation, interpolation, figure, and channel ledgers.

Figures use the field-led monochrome treatment and `#101519` background. The
circular rim remains a display boundary. No center lines, boundary paths,
annotations over the art figure, spatial filtering, or image-space rotation
are permitted.

## Components

- `spherical_intensity/orientation.py`: strict recipe and orientation ledger.
- `spherical_intensity/rotation.py`: exact node transformation and invariants.
- `spherical_intensity/reprojection.py`: specimen-grid pullback and source
  hemisphere sampling.
- `spherical_intensity/oriented_render.py`: hemisphere, sphere, comparison,
  and axis-diagnostic figures.
- Bundle/workflow layer: content-addressed publication, manifest, CLI result,
  and atomic no-replace semantics.
- `recipes/spherical/ice-ih-oriented-s2-proof.yml`: Ice source, identity
  control, `(17, 31, 43)` orientation, smoke/review sizes, and display channel.

The implementation reuses the public `Orientation` model,
`transform_crystal_direction_to_sample`, the spherical source mapping, and the
near-depth optical treatment. It does not introduce another Euler convention.

## Validation

### Rotation invariants

- Identity preserves coordinates and every value channel exactly.
- Arbitrary rotation preserves node count, node order, unit norms, values, and
  source indices.
- `G_cs^-1(G_cs c) = c` within a strict recorded tolerance.
- The rotation matrix is finite, orthonormal, right-handed, and has determinant
  `+1` within tolerance.
- Oriented crystal axes exactly match the existing detector adapter's
  `transform_crystal_direction_to_sample` results.

### Reprojection invariants

- Identity upper and lower numeric fields reproduce their source grids.
- Known exact source nodes reproduce their intensities after arbitrary inverse
  mapping.
- Upper/lower selection is correct on both sides of the rotated crystal
  equator and follows one explicit equator owner.
- Every valid output direction is assigned exactly one source hemisphere.
- No spatial-filter key other than `none` is accepted.

### Artifact invariants

- Repeated runs produce identical numeric hashes and PNG bytes.
- Manifests link the oriented field, Ice source, kinematical recipe, field-led
  presentation recipe, and orientation ID.
- Scientific and presentation channels remain distinguishable in filenames,
  ledgers, and claims.
- Output publication is atomic and never overwrites an existing bundle.

## Bounded Execution

The workflow must complete a 480-pixel smoke bundle with source
`half_size = 32` (`65 x 65` stereographic arrays) before starting one
2400-pixel review render. Smoke exercises both orientations, both hemispheres,
both sphere views, axis diagnostics, and all ledgers at reduced source and
output size. The review uses the current Ice source `half_size = 512`
(`1025 x 1025` stereographic arrays) and evaluates raster output in bounded
tiles.

The workflow reports its current stage and elapsed time. It has explicit stage
timeouts: the smoke bundle is capped at 180 seconds and the complete review at
600 seconds. It emits no unbounded MTEX or external-process call. Failure at
smoke prevents the review render from starting.

## Error Handling

The workflow fails with a normalized error when:

- the orientation is not active `crystal_to_sample` Bunge degrees;
- source identity, array shape, hemisphere order, frame, or energy disagrees;
- the source master does not contain both hemispheres;
- rotation or inverse rotation violates numeric invariants;
- reprojection produces non-finite values or unowned valid directions;
- identity numeric parity fails;
- a requested presentation recipe contains a vector overlay; or
- a bundle path already exists.

There is no silent convention inversion, source substitution, interpolation
fallback, hole filling, or partial bundle publication.

## First-Proof Acceptance Criteria

- An exact oriented Ice S2 field is linked to the unchanged source field and
  orientation `(17, 31, 43)` degrees.
- Identity and oriented node invariants pass with recorded tolerances.
- Identity versus oriented upper-hemisphere figures visibly move the entire
  band/intersection network rather than the camera or image canvas.
- Oriented upper/lower and two full-sphere views use the same specimen-frame
  orientation and field-led channel.
- Both vector-overlay layers are absent and the ledger records no blur.
- A bounded smoke passes before the 2400-pixel review candidate.
- The user reviews the full frame, sphere views, and native-scale crop before
  promotion beyond presentation-proof status.

## Out of Scope and Parked Follow-ons

- Detector projection from the same oriented master.
- A side-by-side parity diagnostic against regenerated rotated reflectors.
- Orientation galleries and animation.
- Selection of orientations from indexed EBSD data.
- Texture/ODF-weighted accumulation of rotated single-crystal fields.
- Interactive WebGL/HTML, GLB, STL, or other 3D export.
- Quartz or phase-general proof.
- Dynamical simulation, chirality recovery, or experimental pattern matching.

These follow-ons must consume the same orientation and frame ledger rather than
redefining orientation locally.
