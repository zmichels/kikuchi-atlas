---
title: Ice Ih Intensity and Reflector-Ridge Globes Design
date: 2026-07-17
status: approved-in-conversation
work_item: KIKU-F006
---

# Ice Ih Intensity and Reflector-Ridge Globes Design

## Goal

Publish two explicitly separate, reproducible, watertight Ice Ih globe
products at a common physical scale:

1. an intensity-relief globe derived from a validated Ice Ih kinematical
   master pattern; and
2. a reflector-ridge globe derived directly from a selected catalog of Ice Ih
   reflector families.

The ridge globe must be an analytic crystallographic model, not a thresholded
or filtered raster. Its raised bands must be much more legible than raw
master-pattern texture while retaining a complete, inspectable source-to-mesh
lineage.

The initial Ice model is intentionally the oxygen sublattice of hexagonal Ice
Ih, not a claim about a complete ordered hydrogen structure. Its retained
source record is `COD-1572233-O-sublattice`, COD source 1572233, `P 63/m m c`,
with the source checksum and scope restored from the repository's retained Ice
science-art lineage.

## Approved Direction

The user approved all of the following:

- keep the intensity and reflector-derived products separate; do not create a
  hybrid in this slice;
- use Ice Ih and the same dominant-reflector evidence as the prior Ice tattoo
  work;
- select the `15` members that pass the prior catalog's inclusive normalized
  strength floor of `0.08`, rather than the full 30-member axial catalog;
- preserve equal-strength blocks during selection and express the retained
  evidence through four visible strength cohorts; and
- displace bands outward as raised ridges, not inward as engraved grooves.

The existing forsterite intensity-relief globe remains unchanged. This is a
new Ice product family and a phase-neutral source capability, not a retrofit
that changes the semantic identity of prior output.

## Product Boundary

### Ice intensity-relief globe

The intensity product reuses the existing `SphericalScalarField`, filtering,
icosphere, validation, preview, and atomic bundle contracts. Its source is an
Ice kinematical master produced by the restored project-owned phase and
reflector path. Its raw-value field remains its geometry authority.

This product may retain fine kinematical texture. It is explicitly distinct
from a diagrammatic or reflector-defined product.

### Ice reflector-ridge globe

The reflector product consumes immutable reflector records and evaluates a
continuous band field directly on unit directions. It does not consume a PNG,
SVG, sampled detector image, master-pattern intensity, edge detector, or
spatial denoiser.

Each retained record supplies at least:

- stable member identity and Miller indices;
- crystal-frame unit plane normal;
- Bragg half-width in radians;
- structure-factor magnitude and normalized selection weight;
- source phase, beam energy, catalog, and frame identity; and
- tie-preserving cohort and eligibility provenance.

The product is an interpretable science-art geometry derivative. It is not
labeled as a dynamical EBSD intensity simulation or a measurement.

## Architecture

```text
Ice source record + explicit energy
              |
              v
Project-owned reflection adapter
  enumerate / calculate evidence / axial collapse
              |
              v
ReflectorCatalog
  members + strengths + Bragg widths + frame provenance
              |
              +-------------------------------+
              |                               |
              v                               v
Ice kinematical master                 15-member ridge selection
              |                               |
              v                               v
SphericalScalarField                  AnalyticSphericalBandField
              |                               |
              v                               v
existing intensity mapping              bounded raised-ridge mapping
              |                               |
              +---------------+---------------+
                              v
             deterministic geodesic radial mesh
                              |
                              v
      independently identified atomic STL bundles
```

All boundaries consume project-owned plain data. `diffsims`, `orix`, and
`kikuchipy` objects remain adapter-local and are never serialized as durable
catalog or mesh contracts.

## Shared Reflector Core

The historical Ice tattoo implementation is a validated source of policy and
data semantics, but it will not be copied back as an Ice-only art subsystem.
The new core is phase-neutral and owns strict records, catalog snapshots,
closed-schema recipes, and source-independent identities.

For the initial Ice recipe, selection uses the historical policy:

```yaml
source_master_relative_factor: 0.03
selection_relative_factor: 0.22
weight_exponent: 2.0
eligibility_min_weight: 0.08
tie_policy: keep_equal_weights_together
ranking: normalized_structure_factor_weight
cohort_count: 4
```

The recovered tattoo/art lineage came through a bounded master recipe with
`source_master_relative_factor: 0.03`, then retained signed reflectors with
`abs(F) >= 0.22 * max(abs(F))`, then collapsed exact antipodal HKL pairs, and
then used squared normalized structure-factor weights. The `0.22` gate is the
effective catalog gate; the `0.03` value is retained provenance from the source
master lineage. That yields a full axial catalog of 30 members; 15 satisfy the
inclusive `0.08` eligibility floor.
The recipe refers to the policy, rather than hard-coding a positional list of
15 entries. A changed phase, energy, cutoff, strength, exponent, threshold, or
tie rule therefore creates a new catalog and product identity.

## Analytic Raised-Band Field

For a unit sphere direction `u` and a retained unit plane normal `n`, the
signed angular distance from the band's center plane is:

```text
d(u, n) = asin(dot(u, n))
```

The band interior is a corridor about that great-circle center plane. Its
half-width begins with the record's Bragg half-width and receives an explicit
recipe-controlled visual/print scaling factor and physical minimum-width
constraint. The latter makes fine families survive at the chosen globe size;
it does not change the catalog's physical Bragg evidence.

A raised, filleted corridor profile `q_i(u)` maps each signed distance to
`[0, 1]`. It is one at the center of the band, smoothly descends through a
recorded edge-filleting interval, and is zero outside the corridor. The first
profile is a symmetric raised strip, not a pair of independently inferred
bright/dark Kikuchi edges.

Each cohort maps to explicit physical height and width multipliers. Four
dominant-through-delicate tiers remain visually distinct, while exact cohort
membership is derived by the tie-preserving selection policy rather than an
arbitrary fixed count per tier. Exact values are recipe fields in millimetres,
not visual constants embedded in rendering code.

Individual contributions combine through a bounded union:

```text
Q(u) = 1 - product_i (1 - h_i * q_i(u) / H_max)
r(u) = R_base + H_max * Q(u)
```

where each `h_i` is no greater than the positive `H_max`. This keeps all
crossings visibly reinforced while preventing arbitrary additive spikes. The
geometry is therefore a star-shaped, outward-only radial deformation with
`R_base <= r(u) <= R_base + H_max`.

## Physical Recipe Defaults

The first review recipe targets the existing 80 mm nominal base diameter and
uses a dominant ridge ceiling of about 3 mm. The exact committed defaults are
validated outputs of the implementation, but the recipe will expose:

- base diameter and maximum relief in millimetres;
- topology subdivision;
- inclusion threshold and tie policy;
- four height values and four width multipliers;
- Bragg-width multiplier, physical minimum width, and edge fillet;
- bounded-union rule;
- explicit `raised_outward` direction; and
- printer context as advisory `filament_fdm` metadata only.

No slicer settings, support geometry, infill, material, multi-part split,
color, or physical-print success claim belongs in this contract.

## Artifacts and Provenance

Each content-addressed bundle contains its own:

- binary STL and deterministic fixed-view preview;
- validated radial geometry and mesh-validation report;
- strict resolved recipe snapshot;
- source and catalog/selection ledger;
- sampled scalar-field data and sampling diagnostics; and
- manifest written last through the existing atomic publication mechanism.

The ridge bundle records the exact 15 member IDs, the rejected 15 members and
their policy reasons, all cohort assignments, profile parameters, and the
analytic-field identity. The intensity bundle records its Ice master product
and intensity-field identity. Neither bundle is allowed to imply that it was
derived from the other.

## Validation

In addition to existing mesh validation, the new source and field layers must
prove:

- source checksum, phase setting, and oxygen-sublattice claim boundary;
- finite, unit-length normals and positive finite Bragg half-widths;
- stable catalog and recipe identities independent of machine-local paths;
- 15 selected members under the approved policy, with ties never split;
- antipodal band-field equivalence and analytic landmark values;
- monotonic ridge profiles, bounded intersection relief, and no inward radius;
- deterministic field, preview, JSON, and STL outputs on repeat builds; and
- one watertight, consistently wound, positive-volume, single-body STL with no
  repair performed by validation.

Visual review is a separate acceptance gate: the 15-family hierarchy must read
as deliberate broad-to-fine raised bands at native preview scale. Physical
printing and slicer behavior remain external/operator validation.

## Non-Goals

- hybrid intensity-plus-ridge geometry;
- deriving geometry from tattoo SVG/PDF paths or any raster;
- detector-projected band fitting or dynamical-intensity claims;
- automatic aesthetic ranking or hidden reflector selection;
- engraving, double-edge band treatment, or later tonal material effects;
- support generation, printer toolpaths, or a claim of successful FDM output;
- modifying prior forsterite relief identities or the accepted quartz habit.
