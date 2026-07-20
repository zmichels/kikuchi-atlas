---
title: Ice Ih Near-Depth Stepped Rendering Design
date: 2026-07-14
status: approved
project_prefix: KIKU
depends_on: KIKU-T025
---

# Ice Ih Near-Depth Stepped Rendering Design

## Purpose

Add a crisp depth-bearing presentation derivative to the accepted Ice Ih
oxygen-sublattice kinematical master. The treatment makes genuine multi-band
overlaps advance through luminance and gives selected band edges a subtle
shadow-like separation, without blurring, displacing, resampling, or replacing
the existing quiet render.

The accepted `etched-master-quiet.png` remains the immutable control. The new
product is explicitly presentation-oriented, crystallographically registered,
and separately ledgered. It does not become a new claim of dynamical EBSD
realism.

## Approved Visual Direction

The browser study established these decisions:

1. Brightness represents nearness: stronger genuine overlaps advance toward
   the viewer.
2. The inverse, internally backlit treatment is retired.
3. The near-light effect should be slightly stronger than the first mockup but
   must retain internal highlight gradation.
4. Symmetric stepped relief is selected over a simple dark under-stroke.
5. The step consists of broad band body, paired dark boundary seams, and a
   narrower luminous center trace.
6. Edge contrast remains symmetric; no arbitrary virtual light direction is
   introduced.

## Product Boundary

The implementation adds a separate depth-treatment recipe and run bundle. It
does not add fields to `KinematicalRecipe`, change existing recipe IDs, append
files to accepted kinematical manifests, or overwrite any prior figure.

The first recipe references the Ice Ih source and
`ice-ih-oxygen-quiet-proof.yml`. A future phase may reuse the treatment only
after its own visual and scientific review; the Ice parameters are not a
universal style default.

```text
tracked structure + existing kinematical recipe
                    |
                    v
       unchanged KinematicalSimulation
          /                         \
         v                           v
accepted quiet figure       exact selected reflectors
         |                    /                 \
         |                   v                   v
         |          overlap-depth field   exact vector paths
         |                   |           boundaries + centers
         +-------------------+-------------------+
                             v
                 near-depth stepped renderer
                             |
          figure + overlap diagnostic + depth ledger
```

## Separate Contracts

`NearDepthTreatmentRecipe` records:

- referenced kinematical recipe path and expected recipe ID;
- overlap reflector threshold relative to maximum `abs(F_hkl)`;
- overlap weighting exponent;
- overlap normalization percentile;
- optical-depth gain and luminance ceiling;
- center-trace threshold, width, alpha, casing width, and casing alpha;
- boundary threshold, width, alpha, casing width, and casing alpha; and
- figure size and background color.

The parser rejects unknown fields and invalid ranges. Serialization is plain
data and content-addressed. The treatment recipe references, rather than
copies, the source kinematical identity.

`NearDepthResult` contains the valid-disk overlap array, rendered PNG bytes,
diagnostic PNG bytes, and a plain depth ledger. Upstream kikuchipy or
matplotlib objects remain private and are never serialized.

## Exact Overlap Field

The overlap channel must distinguish a single strong band from multiple bands;
it may not infer overlap by thresholding the finished PNG.

1. Start from the selected reflector catalog and collapse antipodal `hkl` and
   `-h-k-l` entries to unique axial planes.
2. Convert the validated upper-hemisphere stereographic grid to unit sphere
   directions using the existing projection contract.
3. Convert each unique reciprocal-lattice vector to a unit Cartesian plane
   normal in the crystal frame.
4. A direction lies inside a band when
   `abs(dot(direction, normal)) <= sin(theta_B)`. A parity test must confirm
   this analytic membership against kikuchipy's exact plotted Bragg
   boundaries.
5. Give each band weight
   `w_i = (abs(F_i) / max(abs(F))) ^ 2`, matching the kinematical intensity
   meaning while retaining an explicit exponent in the recipe.
6. Accumulate only `sum_weight` and `max_weight` on the valid disk. No
   pixels-by-reflectors cube is retained.
7. Define additional overlap as
   `overlap_raw = max(sum_weight - max_weight, 0)`. It is exactly zero where
   zero or one unique band contributes.
8. Normalize by the configured valid-disk percentile and clip only this
   presentation channel to `[0, 1]`. The raw array and normalization value are
   retained in the ledger.

The initial Ice proof uses the quiet reflector threshold `0.22`, squared
structure-factor weighting, and the `99.5` percentile for overlap
normalization.

## Near-Light Compositing

The unchanged quiet master tone map supplies base luminance `B`. For a
luminance ceiling `L_max = 0.985`, convert the base to optical depth:

```text
tau_base = -log(1 - B / L_max)
tau_final = tau_base + gain * overlap_normalized
L_final = L_max * (1 - exp(-tau_final))
```

The initial gain is `0.28`. This multiplies remaining darkness rather than
adding arbitrary white, preserves ordering, and approaches the ceiling
asymptotically. Pixels with zero additional overlap remain identical to the
base field before the vector relief layer is drawn.

Outside the stereographic disk remains the existing background. All array
operations are pointwise after exact band-membership evaluation; no spatial
filter is permitted.

## Symmetric Stepped Relief

The vector layer uses kikuchipy's exact public plotting geometry rather than
raster edge detection.

- Quiet center traces use the existing relative threshold `0.22`, a pale
  `0.42 pt` spine at alpha `0.62`, and a coincident charcoal `0.82 pt` casing
  at alpha `0.38`.
- Bragg-boundary seams use relative threshold `0.34`. In the Ice proof this
  retains 24 signed reflectors before kikuchipy path generation. Both exact
  boundaries are drawn with a `0.38 pt` charcoal seam at alpha `0.48` and a
  coincident `0.82 pt` darker casing at alpha `0.30`.
- Boundary and center paths are symmetric and undisplaced. Path casing is a
  wider coincident vector stroke, not a raster drop shadow.
- The circular rim remains separate and unchanged.
- Vector paths are rasterized once at the requested final resolution. Coverage
  antialiasing is permitted; intermediate resizing and spatial filtering are
  not.

These values reproduce the approved browser mockup. The threshold, not the
observed count of 24, is the durable selection rule.

## Outputs and Provenance

The command `kikuchi-lab render-kinematical-depth` writes a new content-addressed
bundle containing:

- `figures/etched-master-near-depth-stepped.png`;
- `figures/quiet-vs-near-depth-stepped.png`;
- `diagnostics/overlap-additional-depth.npy`;
- `diagnostics/overlap-additional-depth.png`;
- `diagnostics/depth-render-ledger.json`;
- a copied plain treatment recipe; and
- `manifest.json` with sizes and SHA-256 hashes.

The ledger records source ID and checksum, base recipe and product IDs,
reflector thresholds, axial-collapse rule, grid and frame conventions,
membership equation, weight equation, normalization statistic, optical-depth
equation, all vector stroke parameters, package versions, and output hashes.

## Failure Behavior

The workflow fails before rendering when:

- the referenced base recipe ID does not match;
- the source projection is not an upper stereographic square grid;
- axial canonicalization finds inconsistent antipodal strengths or angles;
- no positive additional-overlap samples exist;
- the configured normalization percentile has zero width;
- luminance exceeds the configured ceiling before conversion; or
- any output array contains non-finite values.

No fallback silently substitutes raster thresholds, image morphology, blur,
or a pointwise brightness proxy.

## Verification

Tests must establish:

- deterministic antipodal collapse and permutation-order independence;
- zero additional depth for empty and single-band fields;
- positive, strength-ordered depth at controlled intersections;
- analytic band membership parity with plotted Bragg boundaries;
- pointwise identity wherever additional overlap is zero;
- monotonic brightening, finite output, and strict luminance-ceiling retention;
- exact vector parameter propagation for center and boundary layers;
- stable bundle identity and complete provenance links; and
- unchanged hashes for the accepted quiet Ice and forsterite products.

A bounded smoke render precedes one `2400 x 2400` review candidate. Native
scale and magnified edge crops are reviewed together. The depth derivative is
not promoted until the user approves that candidate.

## Non-Goals

- Replacing the quiet render or its accepted treatment.
- Claiming added overlap brightness is quantitatively experimental intensity.
- Blur, glow kernels, depth of field, spatial denoising, emboss filters, or
  directional drop shadows.
- Generalizing the treatment to every phase before additional review.
- Changing detector overlays, dynamical simulation, orientation sampling, or
  spherical/MTEX exports in this slice.
