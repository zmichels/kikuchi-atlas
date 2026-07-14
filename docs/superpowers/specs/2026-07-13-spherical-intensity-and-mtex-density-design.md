---
title: Spherical Intensity and MTEX Density Bridge Design
date: 2026-07-13
status: review
project_prefix: KIKU
depends_on: KIKU-F002
milestone: Exceptional Forsterite Pattern
---

# Spherical Intensity and MTEX Density Bridge Design

## Purpose

Export the forsterite kinematical master pattern as an explicit scalar field on
the unit sphere and make that field immediately useful in MTEX. The first proof
must support two complementary views of the same data:

1. an exact-node spherical intensity field for colored sphere, contour, and
   projection plots; and
2. a reproducible density cloud in which more vectors occur where the selected
   intensity channel is stronger.

This product is not an orientation distribution function (ODF). Its domain is
direction on the sphere, not crystal orientation in SO(3). A later texture
experiment may rotate and accumulate the single-crystal field under an ODF,
but that would be a distinct aggregate product.

The bridge is additive. Projected stereographic, Lambert, spherical-line, and
detector figures remain the fundamental milestone products. The S2 export adds
a reusable analysis and visualization seam for MTEX, an interactive sphere,
and later print-oriented work without replacing those figures.

## Decisions

1. The authoritative object is a sampled directional scalar field on S2.
2. The source is the both-hemisphere stereographic kinematical master produced
   by the approved `KIKU-F002` pipeline.
3. Source pixels are mapped to unit vectors with orix's public
   `InverseStereographicProjection`, matching kikuchipy's spherical display.
4. The canonical export retains every geometrically valid in-disk source node
   at the selected development resolution. It does not fit harmonics, smooth,
   blur, or resample to a display grid.
5. Raw intensity is immutable and retained. Normalized intensity and density
   weight are named, reproducible derivatives.
6. The full directional sphere is authoritative. An axial field is emitted
   only after an explicit antipodal diagnostic passes a recorded tolerance.
7. MTEX linear spherical interpolation (`S2FunTri`) is the first exact-node
   consumer. Harmonic approximation is a later compression/analysis option,
   never the canonical import.
8. The vector-density cloud is a visualization derivative, not a new physical
   simulation and not a substitute for the source field.
9. No spatial blur or neighborhood cleanup is permitted. Pointwise monotonic
   normalization and spherical interpolation between exact nodes are allowed
   and recorded.
10. The first proof is forsterite and development-scale. Phase-general export
    follows only after the hemisphere, seam, symmetry, and MTEX checks pass.

## Product Boundary

### Canonical directional field

`SphericalIntensityField` owns the exact source-to-vector correspondence. Each
row represents one valid stereographic source sample and records:

| Field | Meaning |
| --- | --- |
| `x`, `y`, `z` | Unit direction in the recorded crystal frame. |
| `hemisphere` | `upper` or `lower`; numeric code may be used in numeric-only interchange. |
| `source_row`, `source_column` | Zero-based source-array coordinates. |
| `intensity_raw` | Unmodified kinematical master intensity. |
| `intensity_normalized` | Recorded pointwise percentile normalization in `[0, 1]`. |
| `density_weight` | Nonnegative pointwise weight derived from `intensity_normalized`. |

The field also owns source-array shape, hemisphere order, projection, phase,
energy, source product ID and hash, coordinate frame, transform owner and
version, equator policy, normalization recipe, and per-channel hashes. Its
plain-data ledger explicitly records:

```text
kind = spherical_scalar_field
domain = S2
domain_semantics = directional
hemisphere_order = [upper, lower]
hemisphere_poles = {upper: -1, lower: +1}
grid = {size, X_formula, Y_formula, row_axis, column_axis}
frame = {name, handedness, vector_units}
phase = {space_group, point_group, contains_inversion}
```

Even when a centrosymmetric field passes the antipodal diagnostic, the
canonical object's domain semantics remain `directional`. Axiality is an
explicit derived interpretation, not a mutation of the source contract.

### Derived axial field

The optional axial field identifies `v` and `-v`. Its intensity is

```text
I_axial(v) = 0.5 * (I(v) + I(-v)).
```

It is never inferred solely from a phase name or space-group label. The
exporter first computes antipodal residuals on exact source pairs and records
maximum absolute, root-mean-square, and normalized residual metrics. The axial
product is eligible only when the phase declares inversion symmetry and the
numeric residual passes the configured tolerance. A failure preserves the
directional field and reports why axialization was refused.

The axial table stores one deterministic representative per antipodal pair:
retain `z > 0`; on the equator retain `x > 0`, plus the single half-axis where
`x = 0` and `y >= 0`. Its intensity channels are the pairwise means. The table
records this representative rule and the source indices of both members.

### Derived density cloud

The density cloud contains directions sampled with probability proportional to
the nonnegative `density_weight` field. It records source-field identity,
sample count, random-number generator, seed, spherical sampling resolution,
MTEX version, and output hash. It is intended for scatter and point-density
figures. Its local jitter and finite point count make it unsuitable as an
authoritative intensity representation.

## Architecture

```text
KIKU-F002 both-hemisphere stereographic master
                         |
                         v
       validate source identity, arrays, and geometry
                         |
                         v
         inverse stereographic mapping through orix
                         |
                         v
             SphericalIntensityField
             /          |           \
            v           v            v
     MTEX-ready CSV   NPZ + JSON   diagnostics
            |                           |
            v                           v
   exact-node S2FunTri          optional axial field
       /          \
      v            v
 contour/3D     density recipe
 figures             |
                     v
          reproducible vector cloud

Projected KIKU-F002 figures remain independent and unchanged.
```

The Python exporter owns validation, coordinate mapping, plain-data contracts,
hashes, and provenance. Orix owns the public inverse stereographic transform.
MTEX owns the exact-node spherical triangulation and the reference density
sampler. No MTEX class becomes a Python-side durable contract.

## Source and Mapping Contract

### Source eligibility

The exporter accepts a `KinematicalSimulation` only when it supplies upper and
lower stereographic master arrays with:

- identical square, odd shapes;
- finite values and explicit upper/lower ordering;
- the same phase, energy, reflection selection, projection, coordinate frame,
  and source product identity;
- an explicit axis convention; and
- a source-grid definition spanning `[-1, 1]` in both coordinates.

The MTEX smoke proof uses a direct `KIKU-F002` simulation at `half_size = 32`
and the first visual acceptance run uses a direct simulation at
`half_size = 128`, yielding `257 x 257` arrays. These are simulator evaluations
at their requested grids, not downsampled images. The existing
`half_size = 256` kinematical visual review and the `half_size = 1024`
production recipe are not imported automatically. They are attempted only
after source export size, MTEX triangulation time, density-sampling time, and
interpolation error are recorded for the smaller ladder.

### Coordinate construction

For a source array of size `N`, zero-based column `j`, and zero-based row `i`:

```text
X(j) = -1 + 2*j/(N - 1)
Y(i) = -1 + 2*i/(N - 1)
```

Only samples satisfying `X^2 + Y^2 <= 1 + disk_tolerance` are eligible, where
`disk_tolerance = 32 * eps(float64)`. Eligibility is geometric; it must not
depend on intensity being nonzero.

With `D = 1 + X^2 + Y^2`, orix's public transform is equivalent to:

```text
vx = 2*X/D
vy = 2*Y/D
vz = -pole*(1 - X^2 - Y^2)/D
```

`pole = -1` maps the upper hemisphere and `pole = +1` maps the lower
hemisphere. The implementation calls orix rather than reimplementing these
equations; the equations are included to make tests and conventions explicit.

### Equator ownership and seam policy

Both stereographic arrays contain the same geometric equator. The combined S2
point set therefore uses one deterministic owner:

- define `inside = r2 <= 1 + disk_tolerance`;
- define `equator = abs(r2 - 1) <= disk_tolerance`;
- retain upper samples where `inside`;
- retain lower samples where `inside and not equator`; and
- record `equator_owner = upper`.

Before omitting the lower equator, the exporter checks upper and lower equator
intensities at the same source indices and requires their range-normalized
maximum residual to be at most `1e-6`. The exact count invariant is
`point_count = 2 * inside_count - equator_count`. Deduplication is performed by
this source-ownership rule, not by coordinate rounding that could collapse
valid near-equator samples. The MTEX preflight independently rejects any
remaining duplicate directions before `S2FunTri` can average them.

### Antipodal correspondence

The antipode of an upper sample at `(X, Y)` is the lower sample at `(-X, -Y)`,
not the lower sample at `(X, Y)`. On the symmetric source grid the paired
indices are:

```text
(i, j) <-> (N - 1 - i, N - 1 - j).
```

Antipodal diagnostics use the mapped vectors or this verified index relation.
They never compare upper and lower arrays element-for-element at the same
indices. In array form the directional residual is exactly:

```text
delta = upper - flip(lower, axes=(row, column)).
```

Seam and antipodal diagnostics are distinct: seam continuity compares
same-index equator samples, while antipodal parity compares the 180-degree
index reversal across the full valid disk.

## Intensity and Density Contract

### Canonical and derived channels

`intensity_raw` is copied directly from the source master and hashed before
derivatives are calculated. The first promoted density recipe is:

```text
low  = percentile(intensity_raw, 5.0)
high = percentile(intensity_raw, 99.85)
n    = clip((intensity_raw - low) / (high - low), 0, 1)
density_weight = n^1.5
```

The recipe is named `quiet-density-v1`. The percentile values and exponent are
presentation parameters, not physical calibration. They are chosen to quiet
the broad low-amplitude background while preserving exact band locations and
the canonical raw channel. `high` must be greater than `low`; otherwise export
fails rather than producing a constant or nonfinite derivative.

No spatial filter, convolution, neighbor average, denoiser, morphological
operation, or downsample-upscale step is allowed. A future linear-weight
diagnostic may be added as a separately named recipe if comparison proves it
useful.

### Density realization

The reference MTEX realization uses:

- point count: `100000`;
- RNG seed: `20260713`;
- MATLAB generator: `twister`;
- MTEX sampling resolution: `0.25 * degree`; and
- the nonnegative `density_weight` field.

MTEX's `discreteSample` evaluates the field on its spherical sampling grid,
clips negative values, samples grid directions by weight, and applies bounded
local random rotations. The generated cloud is therefore reproducible only
for the recorded MATLAB/MTEX implementation and recipe. The exact-node field,
not this cloud, is the cross-version scientific reference.

## Artifact Contract

One successful export writes an atomic standalone directory containing:

| Artifact | Requirement | Role |
| --- | --- | --- |
| `forsterite-s2-intensity.csv` | Required | MTEX-readable numeric node table with vectors and all three intensity channels. |
| `forsterite-s2-intensity.npz` | Required | Lossless arrays, indices, hemisphere codes, channels, and hashes. |
| `forsterite-s2-intensity.json` | Required | Schema, provenance, recipes, coordinate ledger, diagnostics, and artifact hashes. |
| `forsterite-s2-mtex.m` | Required | Self-contained MTEX loader, validation, plotting, and density-sampling script. |
| `forsterite-s2-axial.csv` | Passed axial diagnostic | One representative per validated antipodal pair with averaged intensity channels. |
| `forsterite-s2-density-vectors.csv` | MTEX validation run | MTEX-generated derivative cloud. |
| `forsterite-s2-mtex-preview.png` | MTEX validation run | Fixed-view reference figure. |

The CSV contains a header and only numeric columns. `hemisphere` is encoded as
`+1` for upper and `-1` for lower; this code is not the orix projection-pole
argument. The JSON ledger owns the human-readable mapping. The NPZ is the
lossless Python exchange. The CSV is the immediate MATLAB/MTEX exchange and
uses `%.17g` for floating-point columns so float64 vectors and float32 source
intensities round-trip without material loss.

Large generated arrays and figures are local run artifacts, not source files.
Only recipes, schemas, small fixtures, tests, and acceptance evidence belong in
git.

## MTEX Reference Workflow

The generated script targets the local MTEX 6.1.1 installation and performs
these steps:

```matlab
addpath('/Users/Z/Documents/MATLAB/mtex-6.1.1');
startup_mtex('noMenu');

T = readtable('forsterite-s2-intensity.csv');
xyz = [T.x, T.y, T.z];
nodes = vector3d(xyz, 'normalize');
nodes.antipodal = false;

[uniqueNodes, ~, ~] = unique(nodes(:), 'stable', 'noAntipodal');
assert(length(uniqueNodes) == length(nodes));

sF = interp(nodes, T.intensity_raw, 'linear');
assert(isa(sF, 'S2FunTri'));

nodeError = max(abs(sF.eval(nodes) - T.intensity_raw));
nodeScale = max(max(abs(T.intensity_raw)), eps);
assert(nodeError / nodeScale <= 1e-8);

scatter(nodes, T.intensity_raw, 'complete', 'Marker', '.', 'MarkerSize', 2);
plot(sF, 'complete', 'resolution', 1 * degree);
plot3d(sF, 'resolution', 1 * degree);
axis vis3d;

densityF = interp(nodes, T.density_weight, 'linear');
oldRng = rng;
restoreRng = onCleanup(@() rng(oldRng));
rng(20260713, 'twister');
densityVectors = discreteSample(
  densityF, 100000, 'resolution', 0.25 * degree);
cloudXYZ = densityVectors.xyz;
clear restoreRng;
scatter(densityVectors, 'complete', 'Marker', '.', 'MarkerSize', 2);
```

The final script may use MTEX's `vector3d.load(..., 'columnNames', ...)` when
the local import audit proves equivalent. `readtable` plus the explicit
`vector3d` constructor is the normative path because it makes the named-column
contract visible and avoids depending on delimiter inference.

`interp(..., 'linear')` produces `S2FunTri` and must reproduce source values at
their nodes to the recorded numeric tolerance. The preflight uniqueness check
is mandatory because `S2FunTri` otherwise collapses duplicate directions and
averages their values. Harmonic interpolation is not used in the first proof
because it is an approximation and does not preserve the source node values
exactly.

`scatter(nodes, intensity_raw, ...)` is the exact-node display. `plot` and
`plot3d` evaluate the exact-node interpolant on a requested display grid;
`plot3d(sF)` is the first freely rotatable colored-sphere view, but it is not
misrepresented as a raw-node view. An optional radius-displaced
`surf(sF, 'noScaling', ...)` view is display-only and must be labeled as such;
its geometry is never a fabrication mesh or a modified scientific field.

The canonical script keeps `nodes.antipodal = false`. For an axial artifact,
it loads the separately validated one-representative-per-pair table, marks
those nodes antipodal for construction, and explicitly marks the resulting
`S2FunTri` antipodal after construction. It never toggles the directional field
in place. An antipodal density cloud is plotted with care because MTEX may draw
both `v` and `-v`, doubling visible points without increasing the recorded
sample count.

## Numeric Tolerances

The first proof fixes these validation thresholds so implementations and
reviewers do not have to guess:

| Check | Threshold |
| --- | --- |
| Geometric disk inclusion | `32 * eps(float64)` on `X^2 + Y^2`. |
| Unit-vector norm | maximum `abs(norm(v) - 1) <= 5e-13`. |
| Duplicate directions | Zero duplicates under MTEX `unique(..., 'noAntipodal')` after exact source ownership. |
| Stereo round trip | maximum angular error `<= 1e-10` radians. |
| Equator intensity continuity | range-normalized maximum residual `<= 1e-6`. |
| Axial eligibility | range-normalized RMS `<= 1e-6` and maximum `<= 1e-5`. |
| CSV numeric round trip | vector component and raw-intensity maximum error `<= 1e-12` and `<= 1e-7`, respectively. |
| MTEX exact-node interpolation | maximum absolute error divided by `max(max(abs(raw)), eps)` `<= 1e-8`. |

Range-normalized residuals divide by
`max(max(intensity_raw) - min(intensity_raw), eps(float64))`. Counts and index
relations are exact. A tolerance is never widened automatically after failure.

## Validation and Failure Handling

Export stops without a partial promoted directory when any of these conditions
is found:

- missing, mislabeled, or shape-mismatched hemispheres;
- non-stereographic source projection or unknown source-grid convention;
- nonfinite intensity or a degenerate normalization window;
- inconsistent phase, energy, reflection selection, frame, projection, or
  source identifiers across hemispheres;
- mapped vectors outside the unit-norm tolerance;
- a missing or duplicated equator/seam direction;
- a stereo-to-vector-to-stereo round-trip beyond tolerance;
- a node-table count that disagrees with the geometric mask and seam policy;
- a duplicate direction that MTEX would otherwise collapse and average;
- requested axialization for a phase without declared inversion symmetry;
- antipodal residual above the recorded axial tolerance; or
- an MTEX node-interpolation error above tolerance.

The exporter writes into a temporary sibling directory, computes every hash,
then atomically promotes the completed bundle. A failed optional MATLAB run
preserves the valid Python S2 bundle but records the MTEX preview and density
cloud as unavailable with the command and normalized error; it does not pretend
those artifacts exist.

## Bounded Execution Ladder

No command is allowed to jump directly into the largest render. The workflow
uses these observable stages:

1. pure-Python unit and serialization fixtures;
2. `half_size = 32`, `10000` density points, and `1.0 * degree` MTEX smoke run;
3. `half_size = 128`, `100000` density points, and `0.25 * degree` acceptance
   run; and
4. an explicit later decision on `half_size = 256` or `1024`.

The external MATLAB wrapper writes stage start/end timestamps and a heartbeat
before triangulation, exact-node evaluation, density-grid evaluation, sampling,
and figure export. The smoke run has a five-minute wall-clock limit; the
acceptance run has a fifteen-minute limit. A stage that exceeds its limit is
terminated, retained as failed diagnostic evidence, and investigated before
any larger run. The workflow never retries indefinitely and never increases a
timeout automatically. Headless runs use `startup_mtex('noMenu')`, invisible
figures, `drawnow`, and explicit export commands; alpha-marker options that can
wait indefinitely for graphics handles are excluded.

## Diagnostics and Acceptance Evidence

Each run records at least:

- valid-node counts by hemisphere and total;
- geometric-mask and equator counts;
- min/max/percentiles for raw, normalized, and density channels;
- unit-vector norm error;
- stereo round-trip angular error;
- duplicate-direction count;
- antipodal maximum, RMS, and normalized residuals;
- source and artifact hashes;
- MTEX exact-node interpolation residual when executed; and
- density point count, seed, generator, sampling resolution, MATLAB version,
  MTEX version, and realized-coordinate output hash.

The first visual acceptance sheet shows, from the same source field:

1. upper and lower raw-intensity contours;
2. a fixed-camera 3D colored sphere;
3. the `quiet-density-v1` scatter view;
4. a raw-versus-density-weight channel comparison; and
5. directional-versus-axial comparison when the axial diagnostic passes.

These figures use fixed camera, scalar limits, colormap, point size, and output
dimensions. Interactive rotation is encouraged for inspection but is not the
sole acceptance evidence.

## Test Strategy

### Unit tests

- verify north pole, south pole, center, and representative equator mappings;
- verify every exported vector has unit norm within tolerance;
- verify the geometric disk mask is independent of intensity values;
- verify a zero-valued inside sample is retained and a nonzero outside sample
  is discarded;
- verify upper-owned equator deduplication and
  `2 * inside_count - equator_count`;
- verify seam residual uses same-index equator samples;
- verify antipodal index mapping uses reversed row and column indices;
- verify raw intensity and source-index preservation;
- verify the normalization equation and no-spatial-filter invariant;
- verify immutable arrays, stable IDs, and deterministic serialization; and
- reject every validation failure listed above.

### Adapter and integration tests

- compare exporter vectors with direct public orix calls;
- compare the source arrays and metadata with the `KIKU-F002` execution;
- round-trip CSV and NPZ without material vector or intensity error;
- execute a small end-to-end forsterite export twice and compare hashes;
- verify axial eligibility and antipodal metrics for forsterite;
- retain a synthetic non-centrosymmetric fixture that refuses silent
  axialization and preserves unequal opposite-direction values; and
- when MATLAB and MTEX are available, run the generated script headlessly,
  assert exact-node interpolation tolerance, point count, expected files, and
  the bounded-stage timing record.

### Existing-product isolation

The test suite verifies that adding this exporter does not change the accepted
kinematical projection figures, recipes, source hashes, `scientific-clean`
products, or the existing final-bundle schema.

## Delivery Sequence

This design becomes a separate feature dependent on `KIKU-F002`:
`KIKU-F003: Spherical intensity and MTEX density bridge`. Its implementation
plan should split work into:

1. immutable S2 contracts and recipe;
2. orix mapping, seam policy, and antipodal diagnostics;
3. atomic CSV/NPZ/JSON bundle export;
4. generated MTEX loader and exact-node validation;
5. density-cloud and preview generation; and
6. end-to-end forsterite acceptance evidence and tracker closure.

The feature does not block completion of the projected-image milestone. It can
consume the development-resolution `KIKU-F002` master as soon as that contract
exists, then move to the production source only after the visual and numeric
gate passes.

## Deferred Work

- phase-general and non-centrosymmetric production exports;
- binary or equal-area production interchange after measured CSV size/import
  costs;
- spherical-harmonic compression or analysis with recorded reconstruction
  error;
- ODF-driven rotation and accumulation into an explicitly aggregate texture
  product;
- browser or PyVista interactive sphere and GLB/VTP viewing exchange;
- display-only radius displacement and science-art styles;
- fabrication-ready watertight sphere or band-ribbon meshes;
- dynamical-master input and matched kinematical/dynamical comparison; and
- EBSD-map orientation ensembles and ebsdx/ebsdx-rs integration.

The later ODF experiment must never be labeled a single-crystal EBSD pattern.
It represents a texture-weighted aggregate of rotated spherical intensity
fields and requires its own physical interpretation and validation.

## Definition of Done

The first proof is complete when a cited forsterite development recipe produces
one atomic S2 bundle; Python validation passes; MTEX reconstructs the raw field
at source nodes within tolerance; the directional, optional axial, and density
semantics are explicit; the fixed-view comparison figures are reviewed; and no
existing projected-image or dynamical artifact changes.
