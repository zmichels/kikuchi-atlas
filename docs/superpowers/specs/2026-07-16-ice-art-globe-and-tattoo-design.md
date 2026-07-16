# Ice Art Globe and Tattoo Design

- Status: approved design
- Date: 2026-07-16
- Source milestone: [KIKU-T027](../../work/KIKU-T027.md)
- Source acceptance: [Ice Ih oriented spherical-master review](../../acceptance/ice-ih-oriented-spherical-master.md)
- Product boundary: derived science-art with explicit provenance, not simulated-intensity truth

## Purpose

Create two sibling art products from one validated Ice Ih master-pattern source:

1. a complete, watertight spherical relief suitable for STL fabrication; and
2. a simplified rotated-Ice vector composition suitable for development with a
   tattoo artist.

The products share source evidence and a ranked crystallographic band catalog,
but they deliberately do not share one rendering transform. The globe uses the
canonical crystal-frame sphere. The tattoo uses the approved rotated specimen
view because orientation materially controls its two-dimensional composition.

Neither product is traced from a PNG. Projected and spherical images remain
fundamental outputs and are not replaced by these art derivatives.

## Approved product decisions

### Relief globe

- Complete sphere with no flat spot, hole, attached pedestal, or integrated
  stand.
- Separate optional cradle may be designed later under its own identity.
- Canonical Ice crystal frame; rotation is optional pose metadata only.
- Parameterized size with a default maximum diameter of `150 mm`.
- Five total radial tiers: background plus four band-strength levels.
- Total radial relief span of `7 mm`.
- Brightest and strongest bands sit nearest the `75 mm` outer radius.
- Background sits at the `68 mm` radius.
- Band overlaps use the maximum occupied tier and never add above the cap.
- Broad plateaus and controlled geometric shoulders prevent spikes and lumps.
- Fine grayscale texture does not become surface geometry.

The default radial offsets above the background are:

```text
[0.00, 1.75, 3.50, 5.25, 7.00] mm
```

The default shoulder transition is `1.5 mm` measured geodesically on the
outer sphere. A recipe may vary the transition from `0.8` through `2.0 mm`,
but it may not introduce spatial filtering, image blur, or uncapped additive
height.

### Tattoo artwork

- Physical design range of `127-152 mm` (`5-6 inches`) with a default
  `145 mm` artboard.
- Uses the accepted active crystal-to-sample Bunge orientation `(17, 31, 43)`
  degrees.
- Open silhouette with no enclosing circle or detector rectangle.
- Approximately `10-12` retained structural band paths.
- Single-stroke hierarchy; there are no doubled band-edge outlines.
- A few dominant paths become broad, ribbon-thick strokes.
- Secondary paths remain medium or fine single strokes.
- Natural crossings only; no node dots, flares, rings, or halo symbols.
- Canonical palette is black ink plus untouched skin.
- A secondary-priority gray-wash/dotwork derivative may reuse the same line
  network without changing it.

The approved artwork density is between the explored sparse and balanced
options: sparse enough for immediate readability and aging, but with a
restrained second tier that preserves recognizable Kikuchi complexity.

## Scientific and artistic claims

The Ice phase, source record, energy, reflector enumeration, hemisphere
semantics, spherical coordinates, and active orientation retain their existing
identities and ledgers. The shared band catalog records every reflector used by
either product.

The products are labeled `science_art` and `presentation_only`:

- Globe height is a designed tier encoding of ranked band evidence, not a
  physical mineral surface or direct electron-density scale.
- Tattoo stroke width is a graphic encoding of ranked band importance, not a
  literal Bragg width, detector intensity, or medical tattooing prescription.
- Optional gray wash and dotwork are atmosphere/tonal derivatives, not
  additional crystallographic evidence.

## Shared architecture

```text
validated Ice master + reflector inventory
                    |
          ranked band catalog
          /                   \
canonical crystal sphere   approved specimen rotation
          |                   |
five-tier relief mapper    10-12-path vector composer
          |                   |
watertight globe bundle    tattoo-art bundle
```

The shared catalog is the only common art-selection component. Globe and tattoo
transforms, recipes, validation, products, and identities remain independent.

### Shared band catalog

Each catalog member records:

- reflector identity and Miller indices;
- crystal-frame axial normal;
- structure-factor magnitude and normalized rank weight;
- Bragg half width where available;
- source recipe and source structure identities;
- whether the band is eligible for globe tiers, tattoo paths, or both; and
- any human acceptance decision with its reason.

After the eligibility threshold is applied, globe bands are partitioned into
four nonempty, tie-aware rank cohorts. Cohort boundaries and membership are
written to the recipe snapshot and ledger. Tattoo candidates use the same rank
evidence but add composition-aware redundancy and coverage checks.

## Globe product design

### Direction sampling and tier assignment

Generate unit directions directly on the target sphere topology and evaluate
the validated band/presentation evidence at those directions. Do not resample a
rendered sphere or projected PNG.

For each mesh vertex:

1. determine all eligible bands containing the direction;
2. map each band to its recorded strength cohort;
3. assign the maximum occupied tier;
4. apply the deterministic geometric shoulder transition at band boundaries;
5. displace the unit direction to its tier radius; and
6. cap the result at `75 mm`.

Intersections may broaden or merge high plateaus naturally, but they cannot
accumulate extra height. The output therefore has distinct levels without
zone-axis spikes.

### Sphere topology

Two deterministic topologies are required:

| Profile | Longitudes | Interior latitude rings | Unique vertices | Triangles |
| --- | ---: | ---: | ---: | ---: |
| reference-density | 170 | 170 | 28,902 | 57,800 |
| fine | 340 | 340 | 115,602 | 231,200 |

Each topology uses one north pole, one south pole, closed longitude rings,
explicit seam welding, pole fans, and consistently outward triangle winding.
The profiles describe the same field, tiers, dimensions, and relief mapping;
mesh density cannot alter the product semantics.

The reference-density profile intentionally matches the observed topology
scale of the user-supplied tetragonal STL without copying its geometry. That
reference has unknown units and licensing and is never redistributed.

### Globe outputs

The canonical bundle contains:

- `ice-ih-relief-globe-reference.stl`;
- `ice-ih-relief-globe-fine.stl`;
- one rotatable `GLB` inspection model using the fine geometry;
- fixed front, rear, and tier-colored diagnostic PNGs;
- the globe recipe snapshot;
- the shared band-catalog snapshot;
- a geometry/provenance ledger;
- a mesh-validation report; and
- a content-hashed manifest.

The STL files are binary and geometrically unitless. The recipe and ledger
state that coordinates are millimeters. A later 3MF derivative may carry units
intrinsically but is not required for the first proof.

### Globe validation

Hard validation before publication requires:

- finite vertex coordinates and unit input directions;
- exact vertex/triangle counts for the selected topology;
- every undirected mesh edge incident to exactly two faces;
- outward and consistent winding;
- zero degenerate or duplicate triangles;
- no self-intersections;
- one connected closed component;
- seam and pole continuity;
- maximum diameter `150 mm` within `0.01 mm`;
- all radii within `[68, 75] mm`;
- all five tiers occupied;
- no uncapped intersection height; and
- deterministic geometry and file hashes.

Minimum printable feature size and support behavior are reported separately as
fabrication warnings. They do not redefine the printer-neutral canonical mesh.

## Tattoo product design

### Candidate selection

Apply the approved orientation to the catalog and project candidate center
traces into the upper specimen-frame hemisphere. Candidate scoring combines:

- normalized band strength;
- angular/path width;
- nonredundancy with already selected paths;
- coverage of the available composition;
- preservation of several meaningful zone-axis relationships; and
- line-weight diversity.

The deterministic scorer emits a ranked candidate sheet. Human art review may
select from that sheet, but the final product must store the exact reflector
IDs, score components, exclusions, and selection reasons. Rebuilding from that
record reproduces the same vector geometry.

### Vector construction

The canonical vector master uses projected crystallographic center traces, not
raster edge detection. Path endpoints are cropped and rounded as part of the
open composition; no invisible enclosing circle remains in the output.

Target path allocation is:

- `3-4` dominant ribbon-thick paths;
- `4-5` structural secondary paths; and
- `3-4` fine retained paths;

for a total of `10-12` paths.

Default design-space widths are:

- dominant: `3.0-5.0 mm`;
- structural secondary: `1.5-2.5 mm`; and
- fine retained: `0.8-1.2 mm`.

All paths use rounded caps and joins. Natural overlaps remain untreated: the
composition adds no node symbols and no localized intersection embellishment.
Nonintersecting paths must retain at least `1.5 mm` of clear design-space gap.
Each open endpoint must remain at least `2.0 mm` from an unrelated path; true
crystallographic crossings are exempt from both clear-gap requirements.

These measurements are artwork constraints only. A qualified tattoo artist
must review placement, stencil behavior, healed line spread, aging, and any
necessary changes before use on skin.

### Tattoo outputs

The primary black/skin bundle contains:

- editable SVG vector master;
- print-ready PDF at the default physical scale;
- black-on-skin visual mockup PNG;
- stencil-style PNG;
- band-selection and path-geometry ledger;
- stroke-width and minimum-gap diagnostic; and
- a content-hashed manifest.

The secondary gray-wash/dotwork bundle references the primary product identity
and reuses its path geometry byte-for-byte. It may add deterministic dot or wash
regions around selected dominant paths, but it may not change, remove, or add a
structural path. It is not the canonical stencil.

### Tattoo validation

Hard validation before publication requires:

- exact accepted orientation identity;
- `10-12` uniquely identified structural paths;
- no enclosing-circle path;
- no node-symbol layer;
- all vectors derived from catalog members;
- physical artboard size within `127-152 mm`;
- stroke widths within the approved tier bounds;
- minimum-gap and endpoint-clearance checks;
- black/skin-only primary palette;
- deterministic SVG/PDF geometry and ledger hashes; and
- a visible tattoo-artist-review disclaimer.

## Component boundaries

Implementation should keep the following responsibilities separate:

- `catalog`: source verification, reflector ranking, eligibility, and snapshot;
- `globe relief`: tier membership, shoulder transitions, and radial mapping;
- `sphere mesh`: topology construction, winding, and geometric serialization;
- `tattoo composition`: rotation, candidate scoring, path selection, and crop;
- `tattoo vector`: physical-scale path geometry and SVG/PDF serialization;
- `validation`: mesh, scale, stroke, gap, and provenance checks; and
- `publication`: atomic no-replace bundles, manifests, and deterministic files.

No renderer owns scientific state. Recipes and immutable product contracts are
usable from workflows, CLI, notebooks, and later interactive viewers.

## Failure and publication behavior

All source, scientific, geometric, and physical-scale validation completes
before the requested output root is mutated. Publication follows the existing
repository pattern: content-derived run identity, unique partial directory,
file and directory fsync, manifest last, and atomic no-replace promotion.

Hard failures include:

- missing or mismatched source/recipe identity;
- incomplete hemisphere or seam semantics;
- empty catalog or fewer than four nonempty globe strength cohorts;
- nonfinite evaluation or geometry;
- non-manifold, open, inverted, intersecting, or degenerate mesh;
- relief outside the approved range;
- invalid tattoo orientation or path count;
- untraceable tattoo paths;
- tattoo stroke/gap violations; and
- collision with an existing completed or partial bundle.

Fabrication-process observations, such as anticipated FDM supports or slicer
orientation, remain warnings unless a later recipe explicitly names a printer
and promotes those checks to acceptance requirements.

## Verification strategy

### Unit and property tests

- Synthetic bands exercise cohort partitioning, maximum-tier overlap, capped
  radial mapping, and deterministic shoulders.
- Sphere topology tests prove exact counts, pole/seam ownership, manifold edge
  incidence, winding, and scale.
- Synthetic vector candidates exercise ranking, redundancy, path allocation,
  open cropping, widths, gaps, and absence of node/rim layers.
- Serialization tests require byte-deterministic STL, SVG, PDF, JSON, and
  manifest output.
- Corruption tests reject self-consistent forged source, catalog, tier, mesh,
  orientation, and path identities before filesystem mutation.

### Real Ice integration

- One bounded low-resolution globe proof runs before the fine mesh.
- The fine globe is generated once and inspected in both rotatable and fixed
  views.
- One candidate sheet precedes the primary tattoo vector master.
- Primary tattoo geometry is reviewed at actual `127-152 mm` scale and reduced
  thumbnail scale.
- The gray-wash/dotwork derivative runs only after primary tattoo acceptance.

### Human review gates

- Globe review checks distinct readable tiers, smooth broad plateaus, absence
  of spikes/lumps, coherent spherical band organization, and manufacturable
  appearance.
- Tattoo review checks open composition, recognizable Ice-derived hierarchy,
  natural crossings, appropriate negative skin, and clear dominant/secondary
  separation.
- Tattoo-artist review is mandatory before calling any output stencil-ready.

## Implementation sequence

1. Promote two sibling repo-native tasks under a shared Ice art-products
   feature: primary tattoo proof and relief globe proof.
2. Implement and approve the shared band catalog.
3. Implement the primary black/skin tattoo proof.
4. Implement the reference-density and fine relief globes.
5. Implement the secondary gray-wash/dotwork tattoo derivative.
6. Consider a separate cradle only after the unmodified sphere is accepted.
7. Generalize phase and orientation inputs only after both Ice products pass
   their review gates.

This order gives the lower-complexity tattoo product an early proof without
making it architecturally primary over the globe.

## Explicit non-goals

- Deriving geometry or vectors from an 8-bit preview.
- Treating relief height as physical electron density or a natural Ice surface.
- Treating tattoo artwork measurements as medical or tattooing instructions.
- Attaching a flat spot, stand, cradle, hole, or pedestal to the first globe.
- Allowing zone-axis overlap to create uncapped peaks.
- Making gray wash or dotwork part of the canonical tattoo stencil.
- Copying or redistributing the user-supplied tetragonal STL.
- Replacing projected Kikuchi images with either art product.
- Phase-general, detector-projected, dynamical, or experimental-fidelity
  claims in the first Ice art proofs.

## Acceptance summary

The design is ready for implementation planning when:

- both products demonstrably derive from the same validated Ice evidence;
- the globe remains canonical-frame, complete, watertight, `150 mm`, five-tier,
  and capped to `7 mm` relief;
- the tattoo remains rotated, open, black/skin, natural-crossing, and limited
  to `10-12` hierarchically weighted paths;
- the secondary tattoo treatment cannot alter primary geometry;
- source, transform, geometry, and art-product identities remain explicit; and
- both products retain separate machine and human review gates.
