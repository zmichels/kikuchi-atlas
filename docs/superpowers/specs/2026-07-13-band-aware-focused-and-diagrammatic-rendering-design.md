---
title: Band-Aware Focused and Diagrammatic Rendering Design
date: 2026-07-13
status: approved
project_prefix: KIKU
milestone: Exceptional Forsterite Pattern
---

# Band-Aware Focused and Diagrammatic Rendering Design

## Purpose

Replace blur-based gallery cleanup with a crystallographically informed model
that can simplify a dynamical Kikuchi pattern without softening it. The model
must preserve or increase the focus of supported band edges, retain measured
light/dark band profiles and asymmetry, omit unsupported granular residuals,
and keep the original scientific product immutable.

The same evidence model will support two deliberately different products:

1. `gallery-focused`, a full-resolution reconstruction whose visible bands
   must be supported by the dynamical image; and
2. `diagrammatic`, a resolution-independent schematic projection intended for
   visual explanation, science-art, and later print-oriented work.

This design adds a project-owned representation rather than another image
filter. It is a practical companion capability now and a useful seam for a
future phase-general or independent rendering engine.

## Decisions

1. The focused and diagrammatic branches never use blur as denoising.
2. Known crystallographic geometry may identify where legitimate Kikuchi
   structures can occur.
3. Geometry alone may not create a band in `gallery-focused`; the original
   dynamical intensity must provide measured support.
4. Band brightness, width, light/dark pairing, asymmetry, and retained
   variation in `gallery-focused` are fitted from the dynamical evidence.
5. `diagrammatic` may use analytic band envelopes, but it remains explicitly
   labeled and linked to the plane families that generated it.
6. The first proof fits evidence in detector space for fast visual iteration.
   Its canonical band geometry uses crystal-plane normals and angular units so
   the model can move upstream to the spherical master without redesign.
7. The existing `scientific-clean` product and its source projection remain
   unchanged. The current Gaussian `fine_detail_attenuate` stage is removed
   from the promoted gallery recipe rather than retuned.
8. The initial diagrammatic style is luminous grayscale bands and nodes on a
   quiet charcoal-gray field. Style is separate from band geometry and
   evidence.

## Meaning of No Blur

The focused and diagrammatic branches prohibit operations whose purpose is to
replace a pixel or coefficient with a spatial neighborhood average. The
prohibition includes Gaussian, box, median, bilateral, non-local-means, and
diffusion smoothing; low-pass residual attenuation; and downsample-then-upscale
cleanup.

Model simplification is allowed. It removes unsupported degrees of freedom
rather than spreading their values into adjacent structure. Allowed operations
include:

- evaluating crystallographic geometry at detector coordinates;
- measuring intensity along and across a predicted band corridor;
- fitting a bounded one-dimensional cross-band profile and a low-complexity
  tangent amplitude model;
- selecting or omitting complete model components by recorded evidence;
- reconstructing intensity from the selected components;
- analytic tone mapping and contrast separation; and
- coverage antialiasing when rasterizing vector geometry at a requested output
  resolution.

Coverage antialiasing is a sampling rule, not a cleanup operation. The SVG
remains the authoritative diagrammatic output, and a hard-edged raster option
can be added later if it proves aesthetically useful.

## Product Boundary

### Scientific product

`scientific-clean` remains the realism anchor. Its detector projection,
processing lineage, floating-point array, and exports must remain hash-identical
when the focused and diagrammatic branches are added.

### Focused product

`gallery-focused` is a model-based interpretation of the same projection. It
contains only evidenced band components, evidenced intersection structure, and
a fitted low-order background. It is not labeled raw, quantitative, or
scientific-clean.

The focused renderer may omit residual detail, but it may not move a supported
band edge, widen it by smoothing, or invent a band from geometry alone.

### Diagrammatic product

`diagrammatic` uses the same band identities and geometry but permits analytic
profiles and explicit styling. It emits:

- SVG as the authoritative resolution-independent artifact;
- high-resolution PNG for convenient viewing;
- a machine-readable link to the exact `BandModel`; and
- visible or sidecar labeling that distinguishes evidenced and
  geometry-only components.

The initial slice includes only evidenced bands by default. A later explicit
option may show geometry-only plane families for teaching or design studies.

## Architecture

```text
Canonical phase + energy + orientation + detector
                         |
                         v
                 Reflection catalog
                         |
                         v
             Projected angular band corridors
                         |
         Original dynamical detector projection
                         |
                         v
              Band evidence fitting
                         |
                         v
                    BandModel
                  /           \
                 v             v
        gallery-focused    diagrammatic
          float/TIFF/PNG       SVG/PNG

Original projection -> existing scientific-clean branch (unchanged)
```

The shared model keeps scientific identity, geometric prediction, measured
evidence, and presentation style separate. A renderer consumes the model; it
does not rediscover crystallography or silently alter the evidence policy.

## Components

### Reflection catalog

The reflection-catalog adapter consumes the canonical phase, lattice,
structure, space group, electron energy, and an explicit reflection cutoff. It
emits collapsed symmetry families with stable identities and at least:

- representative and symmetry-equivalent `hkl` indices;
- reciprocal-plane normal in the canonical crystal frame;
- interplanar spacing and units;
- Bragg half-angle or equivalent physical band-width parameter;
- multiplicity and any available structure-factor evidence;
- source, phase, energy, software, and cutoff provenance.

The catalog is project-owned even when an upstream library performs reflection
enumeration. Upstream objects do not cross the adapter boundary.

### Band projector

The band projector applies the explicit crystal-to-sample orientation and
detector convention. It evaluates angular distance to each crystal plane and
produces exact band-center and boundary geometry in detector coordinates.

The detector-space proof may serialize sampled paths for rendering, but the
canonical representation retains the crystal normal and angular width. This
keeps the model compatible with future Lambert-sphere, stereographic,
gnomonic, circular, and print-oriented projections.

### Evidence fitter

The evidence fitter receives the immutable floating-point dynamical projection
and the projected corridors. For each symmetry-collapsed plane family it:

1. samples raw intensity in band-normal and band-tangent coordinates;
2. estimates a cross-band profile without modifying the source image;
3. estimates only the tangent variation supported at the configured model
   complexity;
4. records edge locations, edge slopes, width, polarity, light/dark pairing,
   asymmetry, amplitude, uncertainty, and support score; and
5. marks the family as evidenced, ambiguous, unsupported, or occluded by a
   stronger intersection.

Overlapping bands are fitted jointly within intersection regions so the same
intensity is not independently attributed to every family. Stable node
residuals may be retained only inside intersections of evidenced families and
must carry their own support score.

The support threshold is an explicit recipe value. Unsupported and ambiguous
families are recorded rather than silently discarded.

### BandModel

`BandModel` is an immutable, schema-versioned artifact containing:

- source master and detector-projection identities;
- phase, energy, orientation, and detector identities;
- reflection-catalog identity and cutoff policy;
- one entry per plane family with geometry, evidence state, fitted profile,
  uncertainty, and provenance;
- joint intersection or node evidence;
- low-order background-model coefficients;
- evidence-policy and fitting-recipe identities; and
- deterministic content hashes.

The model stores physical or angular values where possible. Detector pixel
coordinates are derived views tied to one detector geometry.

### Focused renderer

The focused renderer evaluates only evidenced model components at the original
detector resolution. Its background is evaluated from the fitted low-order
model, not from a blurred copy of the image. Band contributions use their
measured profiles and bounded tangent variation. Intersection evidence is
evaluated after individual band contributions.

The renderer permits explicit contrast and tone controls but no cleanup stage.
Sharpening, if used, operates on analytic model boundaries or profile slopes;
it does not apply an indiscriminate image-wide unsharp mask.

### Diagrammatic renderer

The diagrammatic renderer maps the same supported geometry into SVG paths and
analytic fills. Style controls are declarative and independent of scientific
identity. The first style exposes:

- charcoal background level;
- luminous band-envelope intensity;
- independent light and dark side weights;
- node emphasis with bounded highlight headroom;
- minimum visible evidence score;
- optional plane-family labels; and
- output projection and crop.

The renderer must not hard-code forsterite symmetry or the selected `[011]`
orientation.

## Provenance and Artifact Layout

The final run bundle gains:

```text
models/
  band-model.json
  reflection-catalog.json
products/
  gallery-focused.npy
  gallery-focused.tif
  gallery-focused.png
  diagrammatic.svg
  diagrammatic.png
diagnostics/
  band-evidence.json
  band-fit-metrics.json
recipes/
  band-model.json
  gallery-focused.json
  diagrammatic.json
```

The manifest records processing lineages independently. `gallery-focused` and
`diagrammatic` reference one `BandModel`; neither appears in the
`scientific-clean` lineage. Run identity includes all geometry, fitting,
selection, and style recipes needed for deterministic reproduction.

## Failure Handling

- A phase, energy, orientation, detector, source, or array identity mismatch
  is fatal. There is no best-effort geometry substitution.
- Missing crystallographic structure or an unavailable reflection catalog is
  fatal for model construction but does not invalidate existing scientific
  products.
- Duplicate symmetry families are collapsed deterministically or rejected if
  their metadata conflicts.
- Insufficient evidence omits a family from `gallery-focused` and records the
  reason. It does not silently lower the support threshold.
- Unresolved overlap marks the involved families ambiguous rather than
  assigning the same evidence multiple times.
- Non-finite fits, out-of-bounds profiles, negative physical widths, or edge
  displacement beyond tolerance invalidate the model.
- Diagrammatic rendering refuses geometry-only families unless its recipe
  explicitly opts into that separately labeled mode.
- A focused or diagrammatic recipe containing a prohibited blur stage fails
  validation before rendering.

## Diagnostics

Frequency-energy reduction is not an acceptance target because a crisp
schematic can legitimately contain strong high-frequency edges. Diagnostics
instead measure whether the model is focused and honest:

- band-center displacement between predicted, measured, and reconstructed
  geometry;
- physical and pixel band-width error;
- band-normal edge-slope ratio after matched tone normalization;
- light/dark polarity and asymmetry agreement;
- evidence score and uncertainty per family;
- supported, ambiguous, unsupported, and omitted family counts;
- reconstruction residual inside and outside evidenced corridors;
- node saturation and retained internal tonal range;
- scientific-product hash equality; and
- deterministic artifact hashes across reproduction.

At supported edges, the reconstructed directional edge slope must not be less
than the input slope after matched tone normalization. Edge centers must remain
within 0.5 detector pixel of their measured input locations. These measurements
are local to model geometry rather than global image-sharpness scores.

## Testing Strategy

Implementation remains test-driven.

### Unit tests

- reflection-family collapse and stable identity;
- orthorhombic metric and plane-normal calculations;
- detector projection under known orientations and projection centers;
- exact band-center and boundary evaluation;
- profile fitting on deterministic bright, dark, paired, asymmetric, and
  crossing synthetic bands;
- unsupported-band rejection;
- joint intersection attribution;
- model schema, hashing, and mismatch rejection;
- SVG geometry and style separation; and
- explicit rejection of blur stages in focused and diagrammatic recipes.

Synthetic fixtures contain sharp edges plus deliberately unsupported granular
components. Tests assert that reconstruction omits the latter without widening
or moving the former.

### Integration tests

- construct a development `BandModel` for the selected forsterite orientation;
- render all three product lineages from one immutable projection;
- prove `scientific-clean` remains byte-identical;
- prove every focused band has an evidenced plane-family record;
- reproduce focused raster and diagrammatic SVG bytes deterministically; and
- validate the expanded bundle and manifest.

### Visual acceptance

The retained forsterite image is reviewed at fit-to-window and 100 percent.
Acceptance requires continuous band hierarchy, quiet unsupported regions,
sharp edges without halos, nodes with internal tonal structure, recognizable
dynamical light/dark pairing in `gallery-focused`, and an intentionally clear
luminous hierarchy in `diagrammatic`.

No new focused output replaces the current retained evidence until the user
approves the comparison.

## Delivery Sequence

1. Define and test project-owned reflection and `BandModel` contracts.
2. Implement detector-space band geometry for the selected forsterite proof.
3. Fit and inspect evidence without rendering a replacement image.
4. Render `diagrammatic` from the validated geometry and evidence.
5. Render `gallery-focused` from measured profiles.
6. Compare original, current blur-based experiment, focused, and diagrammatic
   outputs with local diagnostics and native-scale images.
7. On user acceptance, remove `fine_detail_attenuate` from the promoted recipe
   and update the milestone ledger.

This order makes the diagrammatic product available early while preventing its
analytic styling from being mistaken for evidence reconstruction.

## Non-Goals and Later Work

The first slice does not include:

- master-space fitting or experimental multi-pattern fusion;
- automated indexing or orientation recovery;
- a general color-coding system for orientation or misorientation axes;
- 3D relief or watertight print geometry;
- geometry-only plane-family display by default;
- automatic aesthetic ranking; or
- phase-general acceptance beyond keeping the contracts phase-neutral.

After detector-space validation, the same angular `BandModel` can move to the
Lambert master. That promotion would allow one focused phase model to generate
many detector orientations, a spherical luminous-band map, and later tactile
or 3D-print products without re-estimating each rectangular image.
