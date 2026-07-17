---
title: Spherical Intensity Relief Globe Design
date: 2026-07-17
status: approved-in-conversation
work_item: KIKU-F005
---

# Spherical Intensity Relief Globe Design

## Goal

Turn a validated, both-hemisphere raw Kikuchi master pattern into a reproducible,
provenance-rich, watertight spherical relief suitable for STL export. The first
accepted object is an `80.0 mm` nominal-diameter globe whose strongest raw
master-pattern intensities rise outward by at most `1.2 mm`.

The canonical product is a scientific derived geometry object. It is not a
rendered preview wrapped around a sphere, a hand-drawn band diagram, an MTEX
display surface, or a printer-specific toolpath. Forsterite is the acceptance
example; no forsterite-specific geometry belongs in the production engine.

## Approved Product Direction

The first globe uses:

- raw canonical `MasterPatternProduct` intensity as the authoritative source;
- one shared mapping across north and south hemispheres;
- bright intensity raised outward from a fixed `40.0 mm` base radius;
- robust global `1st` to `99th` percentile normalization;
- monotonic gamma with canonical default `1.0`;
- a manufacture-aware spherical Gaussian low-pass with `0.8 mm` full width at
  half maximum at the base radius;
- a deterministic subdivision-7 icosphere;
- STL as the first fabrication exchange format; and
- process-neutral canonical validation plus advisory FDM observations.

The globe is a solid watertight outer volume. Slicer infill, support placement,
orientation, material, layer height, and physical printing remain operator
decisions.

## Scope Boundaries

### In scope

- arbitrary validated both-hemisphere canonical master products;
- explicit Lambert-square-to-sphere coordinate semantics;
- a reusable spherical scalar-field boundary;
- robust intensity mapping and a recorded physical-scale filter;
- deterministic geodesic topology and radial displacement;
- product-specific star-shaped validation;
- a content-addressed atomic bundle with STL, preview, field ledger,
  validation, and manifest;
- a strict YAML recipe and CLI build command; and
- a real forsterite acceptance build from the retained `501 x 501` master.

### Not in scope

- exact band-ribbon or centerline relief;
- a multiscale intensity-plus-ribbon blend;
- engraving or inward displacement;
- spherical-harmonic fitting;
- crystal-habit-plus-Kikuchi hybrid geometry;
- bases, stands, sockets, holes, labels, split shells, or keyed assemblies;
- automatic support generation or slicer settings;
- 3MF, color textures, GLB, VTP, or interactive UI;
- claiming that slicer ingestion proves a successful physical print; or
- changing the accepted crystal-habit geometry or its validation contract.

## Relationship to Existing Work

`KIKU-F004` established strict recipe identity, deterministic triangle export,
non-mutating Trimesh inspection, atomic content-addressed bundles, fixed-view
previews, and process-neutral/FDM-advisory separation. This feature reuses
those patterns but does not reuse the habit solver's convex-polyhedron model.

The existing spherical-intensity/MTEX design names an exact-node directional
field as the scientific boundary. The relief globe consumes an equivalent
plain-data `SphericalScalarField` interface. Its first adapter reads the
already-supported `MasterPatternProduct` with projection metadata
`Lambert square equal-area`; a later MTEX or stereographic exporter may produce
the same interface without changing relief geometry.

The retained forsterite source is:

```text
local/benchmarks/forsterite-resolution-501/
  COD-9000319-ebsdsim.bundle/master-437f865cd0f68384.npz
```

It is a spatial/source acceptance baseline. Using it does not close the
separate pending planar aesthetic review.

## Architecture

```text
MasterPatternProduct
  raw intensity [north, south, y, x]
  projection/frame/source identity
                 |
                 v
LambertMasterFieldAdapter
  validate source and seam
  map source nodes to unit directions
                 |
                 v
SphericalScalarField
  source directions + raw values + provenance
                 |
                 v
ReliefMapping
  global percentiles -> clamp -> gamma
                 |
                 v
GeodesicSampler
  deterministic subdivision-7 icosphere
  hemisphere-aware inverse Lambert interpolation
                 |
                 v
PhysicalSphericalFilter
  Gaussian FWHM = 0.8 mm at radius 40 mm
                 |
                 v
RadialReliefGeometry
  radius = 40.0 mm + 1.2 mm * filtered value
                 |
                 v
ReliefMeshValidator
  indexed topology + radial certificate + volume checks
                 |
                 v
Atomic Relief Bundle
  STL + PNG + NPZ + validation JSON + manifest JSON
```

Each layer consumes plain project-owned data. Upstream crystallography and
projection classes remain adapter-local and never enter bundle identity or
public geometry types.

## Components and Interfaces

### Strict relief recipe

`ReliefGlobeRecipe` is immutable and loaded from a closed-schema YAML mapping.
Unknown and missing keys are errors at every level. The source path may be
absolute or relative to the recipe; machine-local path text is excluded from
semantic identity while the loaded product ID and file SHA-256 are included.

The canonical semantic content is:

```yaml
schema: kikuchi.relief-globe-recipe/v1
source:
  master_product_sha256: <lowercase sha256>
geometry:
  base_diameter_mm: 80.0
  maximum_relief_mm: 1.2
  topology: icosphere
  subdivisions: 7
mapping:
  lower_percentile: 1.0
  upper_percentile: 99.0
  gamma: 1.0
  direction: bright_outward
filter:
  kind: spherical_gaussian
  fwhm_mm: 0.8
  cutoff_sigma: 3.0
export:
  formats: [stl]
fdm_context:
  process: filament_fdm
```

The file path is supplied by the CLI rather than embedded in semantic recipe
identity. The loader verifies its SHA-256 and the reconstructed canonical
master-product identity before geometry work begins.

### Spherical scalar field

`SphericalScalarField` owns:

- a stable field ID;
- unit directions in the recorded crystal frame;
- raw finite intensity values;
- source hemisphere and source-grid indices;
- source master product ID and array hash;
- projection name and coordinate-frame label;
- equator ownership and seam diagnostics; and
- source-array shape and intensity units.

Arrays are immutable project-owned NumPy arrays. This field preserves raw
values; percentile mapping and manufacturing filtering are later derivations.

### Lambert master adapter

The initial adapter accepts only:

- shape `(2, N, N)` with identical odd square hemisphere grids;
- hemisphere order `north`, then `south`;
- projection `Lambert square equal-area`;
- finite raw intensity;
- a non-empty crystal coordinate-frame label; and
- internally consistent product, source, recipe, and array identities.

It maps each source grid node to one unit direction with an explicit reviewed
Lambert square equal-area transform. Direction-to-square interpolation uses the
inverse of that same transform. Tests compare the transform to independent
analytic landmarks and the installed scientific projection reference at
corners, axes, poles, random interior points, and the equator.

North and south grids both represent the equatorial boundary. The adapter uses
north as the canonical equator owner, compares paired raw values before
deduplication, and rejects a range-normalized maximum seam residual greater
than `1e-6`. Ownership, paired indices, and residuals are recorded; no
coordinate rounding is used to hide duplicates.

### Geodesic topology

The canonical base mesh is a deterministic subdivision-7 icosphere with:

- `163842` vertices;
- `327680` triangular faces;
- one stable seed-vertex and face order;
- midpoint deduplication by sorted parent-edge identity;
- unit-length direction vertices stored in float64; and
- outward face order established once on the unit sphere.

The nominal average edge length at `40.0 mm` radius is approximately
`0.38 mm`, giving more than two samples across the `0.8 mm` manufacturing
feature floor. Lower subdivisions may be generated for diagnostics and
previews, but are not canonical STL products under recipe version 1.

### Intensity mapping

Percentiles are computed once over all geometrically valid raw north and south
source samples after canonical equator ownership. Per-hemisphere normalization
is prohibited. Let `p1` and `p99` be the configured percentiles:

```text
clamped = clip(raw, p1, p99)
unit = (clamped - p1) / (p99 - p1)
mapped = unit ** gamma
```

`p99` must be strictly greater than `p1`; a constant or collapsed source is an
error. Gamma must be finite and positive. Version 1 permits gamma as an
explicit recipe lever but the acceptance recipe uses `1.0`.

### Directional sampling

Each unit icosphere vertex is assigned deterministically to north, south, or
equator from its signed crystal-frame `z` coordinate. The reviewed inverse
Lambert transform yields square-grid coordinates, followed by deterministic
bilinear interpolation in float64. Equatorial directions evaluate both source
grids and require agreement within the same seam tolerance before using the
canonical north value.

The field ledger retains for every output vertex:

- unit direction;
- hemisphere decision;
- four source-grid indices and interpolation weights;
- interpolated raw intensity; and
- mapped pre-filter value.

This makes resampling inspectable without bloating the JSON manifest.

### Physical spherical filter

The filter operates on mapped icosphere values, not on previews or 8-bit data.
Its angular full width at half maximum is:

```text
fwhm_rad = fwhm_mm / base_radius_mm
sigma_rad = fwhm_rad / (2 * sqrt(2 * ln(2)))
```

A `scipy.spatial.cKDTree` over unit directions selects neighbors within
`cutoff_sigma * sigma_rad`, converted exactly to chord distance. Neighbors are
sorted by stable vertex index before Gaussian accumulation. Weights use true
angular distance, are normalized per vertex, and accumulate in float64.

The filter must preserve a constant field within `1e-12`, attenuate a reviewed
sub-`0.8 mm` analytic feature, retain a reviewed broad band, and commute with
rotation to the tolerance permitted by the finite icosphere sampling. No
unrecorded blur, denoising, clipping, or morphological operation is allowed.

### Radial geometry

For unit direction `u_i` and filtered value `q_i`:

```text
r_i = 40.0 mm + 1.2 mm * q_i
v_i = r_i * u_i
```

The base sphere is never cut inward. Every radius must be finite and lie in
`[40.0, 41.2] mm` within `1e-10 mm`. Connectivity is copied unchanged from the
canonical icosphere; relief generation may not retriangulate, simplify, weld,
or repair the mesh.

## Validation Contract

The convex-habit validator is not applied wholesale because an intensity
relief may be locally non-convex. The relief validator constructs Trimesh only
from copied arrays with `process=False, validate=False` and requires:

- exact canonical vertex and face counts;
- unchanged canonical connectivity and face order;
- one connected body;
- watertightness;
- consistent outward winding;
- positive finite volume;
- Euler characteristic `2`;
- no duplicate faces or degenerate triangles;
- finite bounds and exact configured radial range;
- the origin strictly inside the volume; and
- a positive radial-projection certificate for every face.

For a base spherical face with ordered unit directions `(u0, u1, u2)` and its
relief vertices `(v0, v1, v2)`, the face must retain the base orientation and
its plane must face away from the origin:

```text
dot(cross(v1 - v0, v2 - v0), v0) > radial_tolerance
```

Because connectivity is the unchanged triangulation of the unit sphere,
radii are strictly positive, and every face projects with the same positive
orientation onto its unique base spherical triangle, radial projection is a
bijective certificate: the relief has no foldovers and each ray from the
origin intersects the boundary exactly once. A failed certificate is rejected;
the validator never repairs it.

Advisory FDM observations report minimum edge length, triangle altitude,
local relief slope, radial dynamic range, downward-face distribution for a
chosen inspection orientation, and the configured `0.8 mm` feature floor.
They do not alter pass/fail geometry or mutate the mesh.

Binary STL duplicates facet vertices by format. The indexed pre-export mesh
and validation ledger remain canonical. A test-only STL reload may use
`process=True` solely to demonstrate slicer-style welding, matching the
already-approved habit exception; production validation may not.

## Atomic Bundle and Identity

The CLI surface is:

```bash
kikuchi-lab relief globe build \
  --master-pattern path/to/master-*.npz \
  --recipe recipes/relief/forsterite-intensity-globe.yml \
  --output local/relief-globes
```

The build identity includes:

- recipe semantic identity;
- master product ID, array SHA-256, and complete input-file SHA-256;
- spherical-field and seam contracts;
- icosphere seed and subdivision contract;
- interpolation, mapping, filter, and radial-geometry contracts;
- validation and serialization contracts; and
- captured runtime software versions.

The workflow performs source validation, field construction, mapping,
sampling, filtering, geometry, and canonical validation before creating the
output root. It then writes a fresh `<build-id>.partial` directory, flushes
files and directories, and publishes with one atomic `os.replace`. Existing
partial or completed destinations are refused. Any error removes the partial
tree and publishes nothing.

The five-file bundle is:

| File | Role |
| --- | --- |
| `<phase>-intensity-relief-globe.stl` | Binary STL in millimetres. |
| `<phase>-intensity-relief-preview.png` | Fixed-camera, fixed-lighting inspection preview. |
| `relief-field.npz` | Directions, source interpolation ledger, raw/mapped/filtered values, radii, and canonical faces. |
| `mesh-validation.json` | Canonical geometry checks and advisory FDM observations. |
| `relief-manifest.json` | Identity, provenance, contracts, metrics, versions, and complete non-self file inventory. |

The NPZ uses fixed array names, dtypes, shapes, and deterministic uncompressed
`.npy` payload ordering inside a project-owned ZIP writer so byte identity does
not depend on timestamps or library-default archive metadata.

## Preview Contract

The preview is generated from the accepted indexed mesh with a fixed camera,
lighting, background, image size, and colormap. It includes an inset legend
showing base radius, relief range, percentile range, gamma, and filter FWHM.
Lighting may reveal relief but may not change geometry or substitute for the
numeric validation ledger. A second exaggerated-relief image is not part of
the canonical bundle.

## Failure Semantics

The build fails before publication for:

- unknown or missing recipe keys;
- source SHA or reconstructed product-identity mismatch;
- unsupported projection, hemisphere order, shape, or coordinate frame;
- non-finite intensity or invalid percentile range;
- seam residual above tolerance;
- invalid interpolation indices or weights;
- a filter that violates constant-field or finite-output invariants;
- vertex/face count or connectivity drift;
- radius outside the configured range;
- a failed radial-projection certificate;
- non-watertight, inconsistent, disconnected, degenerate, duplicate, or
  non-positive-volume geometry;
- non-finite JSON or NPZ content;
- an incomplete inventory; or
- an existing partial or complete content-addressed destination.

Domain failures return one concise CLI error without a traceback. Programmer
errors are not swallowed.

## Testing Strategy

### Recipe and identity

- exact canonical recipe values and closed mapping schemas;
- missing, unknown, null, boolean, non-finite, and invalid range cases;
- path-independent recipe identity;
- source SHA and product-ID mismatch rejection; and
- runtime-version changes producing different build IDs.

### Coordinate and seam science

- Lambert transform landmarks at poles, axes, corners, and equator;
- inverse/forward round trips over deterministic random directions;
- independent reference comparison;
- exact source-node recovery;
- north/south hemisphere ordering;
- deterministic equator ownership; and
- seam mismatch rejection above `1e-6`.

### Mapping and filter

- shared rather than per-hemisphere percentiles;
- monotonic clamp and gamma behavior;
- constant/collapsed source handling;
- constant-field preservation;
- attenuation of an analytic narrow spherical feature;
- retention of an analytic broad band;
- deterministic neighbor order and weights; and
- bounded rotational equivariance error.

### Topology and geometry

- subdivision ladder counts and deterministic hashes;
- canonical subdivision-7 counts: `163842` vertices and `327680` faces;
- Euler characteristic `2`;
- exact connectivity preservation;
- radius bounds and outward-only mapping;
- radial-projection certificate and deliberate foldover rejection;
- watertightness, winding, body count, volume, duplicates, and degeneracy;
- non-mutation of input field and geometry arrays; and
- deterministic STL and preview output.

### Workflow

- identical builds in separate roots producing identical IDs and file hashes;
- complete manifest inventory and no self-hash cycle;
- failure before output-root creation;
- cleanup after staged failure;
- concise CLI domain errors; and
- test-only processed STL reload proving one slicer-style volume.

## Acceptance Example

The first real acceptance recipe uses
`master-437f865cd0f68384`, the retained `501 x 501` forsterite master product.
Acceptance requires:

- source SHA and product identity verified;
- seam diagnostics passing;
- raw global percentile metrics recorded;
- exactly `163842` vertices and `327680` triangles;
- radii within `[40.0, 41.2] mm`;
- one watertight, consistently wound, positive-volume body;
- Euler characteristic `2` and every radial certificate positive;
- zero duplicate and degenerate triangles;
- complete five-file bundle with reproducible hashes;
- fixed preview reviewed against the raw spherical field; and
- STL opened in the FlashForge-oriented slicer workflow as one unmodified
  solid with an `82.4 mm` maximum possible relief diameter.

Slicer acceptance records orientation, automatic changes, reported dimensions,
body count, and warnings. It does not claim a physical print, acceptable
supports, or a final material profile.

## Future Extensions

The design intentionally leaves room for:

- exact band-ribbon relief as a separately labeled source semantics;
- a multiscale blend with independently inspectable channels;
- lower-resolution preview or web-view meshes derived from the canonical field;
- 3MF with units and metadata;
- hollow or split-shell assemblies with explicit wall and joinery contracts;
- a stand or keyed mounting socket;
- spherical-harmonic or MTEX field adapters; and
- Kikuchi relief mapped onto a crystal habit rather than a sphere.

None of those extensions may silently change the version-1 recipe or bundle
semantics.
