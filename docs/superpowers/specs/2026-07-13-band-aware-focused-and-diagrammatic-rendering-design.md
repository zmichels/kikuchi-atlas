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

The first implementation slice exposes kikuchipy's existing kinematical
simulation surfaces as reproducible project products before introducing custom
reconstruction. This gives us crisp, crystallographically generated reference
figures immediately and establishes an upstream baseline that our code must not
silently duplicate.

The later evidence model will support two deliberately different custom
products:

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
9. The project reuses the pinned diffsims and kikuchipy reflection, master-
   pattern, spherical, and detector-projection APIs. Project code owns recipes,
   selection policy, plain-data contracts, provenance, and validation rather
   than duplicating those libraries' crystallographic mathematics.
10. Every projection records a source/method/coordinate ledger: crystal,
    sample, and detector frames; angular and detector units; hemisphere;
    projection; origin and wrap convention; transform owner; and known-axis
    spot checks.
11. Any generated visual polish is a separate, explicitly decorative
    derivative. Deterministic Kikuchi bands, zone axes, dimensions, labels,
    data, and print geometry remain owned by scientific code.

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

### Kinematical reference products

The first slice wraps kikuchipy's public kinematical APIs to emit:

- upper- and lower-hemisphere stereographic master patterns;
- spherical line and band views;
- Lambert master-pattern arrays; and
- detector-projected kinematical patterns for explicit orientations and
  detector geometry.

These products may expose structure-factor amplitude, structure-factor
intensity, or uniform geometric weighting. Their reflection-selection policy
is explicit and inspectable. They are crisp crystallographic references and
schematics, not quantitatively equivalent substitutes for dynamical EBSD
intensity.

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
       diffsims reflection enumeration and factors
                         |
                         v
          kikuchipy kinematical simulator adapter
           /          |          |          \
          v           v          v           v
  stereographic   spherical    Lambert     detector
      master      lines/bands   master     projection
                         |
                         | optional later hybrid
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

### Kinematical simulator adapter

The adapter follows the public diffsims and kikuchipy pipeline:

1. enumerate reciprocal-lattice vectors from an explicit minimum spacing;
2. keep allowed reflections;
3. collapse and symmetrise equivalent families;
4. sanitise the phase;
5. calculate structure factors and Bragg angles at the explicit beam energy;
6. apply a recorded reflector-selection rule; and
7. construct `KikuchiPatternSimulator` products through
   `calculate_master_pattern()`, `plot()`, `as_lambert()`, `get_patterns()`,
   and `on_detector()` as appropriate.

The project adapter converts upstream results to project-owned recipes,
arrays, tables, and ledgers. It also provides parity checks against direct
public-library calls. Upstream simulator objects do not become durable project
contracts.

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

The catalog schema and selection record are project-owned while diffsims
performs reflection enumeration and structure-factor calculation. Upstream
objects do not cross the adapter boundary. The first visual checkpoint compares
candidate cutoff policies because retaining every allowed reflection can make a
line rendering visually impenetrable even when it is crystallographically
valid.

### Band projector

The band projector first reuses kikuchipy's master-pattern and `on_detector()`
projection paths. Project-owned projection code is added only for a required
geometry field or export that the public API does not expose. Any custom path
must be checked against kikuchipy at known orientations and detector centers.

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

## Projection and Coordinate Ledger

The sphere and detector products are map-like scientific projections because
angular position, adjacency, hemisphere, and distortion materially affect the
meaning of the figure. They therefore use cartographic discipline without
introducing a terrestrial web-map stack.

Each artifact records:

- authoritative source phase and reflection-selection recipe;
- crystal, sample, and detector coordinate frames and handedness;
- orientation convention and transform direction;
- angular, reciprocal-space, and detector units;
- projection name, hemisphere, origin, axis direction, and wrap convention;
- the library or project component responsible for each transform;
- spot checks for known zone axes and selected band traces; and
- which marks are geometric data and which strokes or labels are
  screen-stable presentation.

Spherical or projected band geometry stays in scientific map space. Labels,
minimum stroke widths, and interaction affordances may be presentation-stable,
but they may not move the underlying geometry.

## Creative Derivative Boundary

The canonical kinematical, scientific-clean, focused, diagrammatic, and future
print-source artifacts are deterministic. If a later science-art treatment
uses ImageGen or a generative-polish workflow, the generated layer is limited
to atmosphere, background texture, material suggestion, lighting, or
presentation depth. It must not generate or repaint Kikuchi bands, zone axes,
labels, dimensions, scalar data, or fabrication geometry.

Generated layers are stored separately with their prompt and provenance, then
combined with the deterministic foreground by a repeatable composition step.
They are labeled `art-polished` and are never accepted as scientific or print
source. The first implementation slice performs no image generation: its
figures are direct, reviewable outputs from scientific code.

## Provenance and Artifact Layout

The final run bundle gains:

```text
models/
  band-model.json
  reflection-catalog.json
products/
  kinematical-master-stereographic.npy
  kinematical-master-stereographic.png
  kinematical-master-lambert.npy
  kinematical-master-lambert.png
  kinematical-spherical-bands.svg
  kinematical-spherical-bands.png
  kinematical-detector.npy
  kinematical-detector.png
  gallery-focused.npy
  gallery-focused.tif
  gallery-focused.png
  diagrammatic.svg
  diagrammatic.png
diagnostics/
  projection-ledger.json
  reflector-selection.json
  band-evidence.json
  band-fit-metrics.json
recipes/
  kinematical.json
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

- kinematical recipe, reflector-selection, and projection-ledger validation;
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

- compare adapter outputs with direct pinned kikuchipy public calls;
- verify known zone-axis positions and hemisphere/frame conventions;
- reproduce stereographic, spherical, Lambert, and detector kinematical
  artifacts deterministically;
- construct a development `BandModel` for the selected forsterite orientation;
- render all three product lineages from one immutable projection;
- prove `scientific-clean` remains byte-identical;
- prove every focused band has an evidenced plane-family record;
- reproduce focused raster and diagrammatic SVG bytes deterministically; and
- validate the expanded bundle and manifest.

### Visual acceptance

Visual review begins with contact sheets comparing reflector-selection
policies across stereographic or spherical lines, master intensity, and one
detector projection. The selected kinematical products are inspected at native
scale with known-axis overlays before any hybrid reconstruction begins.

The retained forsterite dynamical image is then reviewed at fit-to-window and
100 percent. Hybrid acceptance requires continuous band hierarchy, quiet
unsupported regions, sharp edges without halos, nodes with internal tonal
structure, recognizable dynamical light/dark pairing in `gallery-focused`, and
an intentionally clear luminous hierarchy in `diagrammatic`.

No new focused output replaces the current retained evidence until the user
approves the comparison.

## Delivery Sequence

1. Define and test project-owned kinematical recipes, reflector-selection
   records, projection ledgers, and plain-data product contracts.
2. Wrap the pinned diffsims and kikuchipy public APIs without duplicating their
   crystallographic or projection mathematics.
3. Compare reflector-selection policies with stereographic, spherical, master,
   and detector figures; retain the visual and numeric diagnostics.
4. Emit a reproducible forsterite kinematical artifact bundle and review it at
   native scale with frame and known-axis checks.
5. Decide from those figures whether custom evidence-guided reconstruction is
   still needed for the desired dynamical light/dark aesthetic.
6. If needed, implement detector-space `BandModel` geometry and inspect fitted
   evidence before rendering a replacement image.
7. Render and compare `diagrammatic` and `gallery-focused` products with the
   kinematical and original dynamical references.
8. Only on user acceptance, remove `fine_detail_attenuate` from the promoted
   recipe and update the milestone ledger.

This order captures kikuchipy's low-hanging fruit immediately and makes the
custom hybrid an evidence-based decision rather than a foregone conclusion.

## Non-Goals and Later Work

The first slice does not include:

- master-space fitting or experimental multi-pattern fusion;
- automated indexing or orientation recovery;
- a general color-coding system for orientation or misorientation axes;
- 3D relief or watertight print geometry;
- geometry-only plane-family display by default;
- automatic aesthetic ranking; or
- phase-general acceptance beyond keeping the contracts phase-neutral;
- a Leaflet, MapLibre, or other terrestrial web-map stack; or
- generated imagery in scientific, schematic-source, or fabrication-source
  products.

After detector-space validation, the same angular `BandModel` can move to the
Lambert master. That promotion would allow one focused phase model to generate
many detector orientations, a spherical luminous-band map, and later tactile
or 3D-print products without re-estimating each rectangular image.
