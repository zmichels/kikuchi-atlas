# Texture-Weighted Spherical Intensity

- Status: Incubating
- Boundary: aggregate texture experiment, not a single-crystal EBSD pattern and not part of `KIKU-F003`

## Motivation

Once a single-crystal Kikuchi intensity field is explicit on S2, a later study
could rotate that field under a synthetic or measured orientation distribution
and accumulate a texture-weighted spherical intensity product. MTEX unimodal,
fibre, Bingham, and uniform ODF components provide a useful way to specify the
orientation weights, but the output would remain a derived aggregate field,
not an ODF and not one detector pattern.

## Current evidence

- The approved [S2/MTEX design](../superpowers/specs/2026-07-13-spherical-intensity-and-mtex-density-design.md) separates directional scalar intensity, axial interpretation, and vector-density visualization.
- [KIKU-F003](../work/KIKU-F003.md) will provide a source-neutral exact-node field and explicit frame/projection ledger suitable for later rotation experiments.
- The local MTEX 6.1.1 installation supports spherical functions and ODF components, but no aggregate physical interpretation or validation dataset has been admitted here.

## Dependencies

- One accepted `KIKU-F003` field with stable crystal-frame semantics.
- An explicit SO(3) orientation convention and quadrature/weight normalization.
- A test proving uniform-ODF and single-orientation limiting behavior.
- Clear labels separating single-crystal, aggregate, directional, and axial products.

## Unresolved questions

- Should the first aggregate rotate raw intensity, normalized intensity, or a physically calibrated channel?
- Should accumulation occur on an equal-area S2 grid, an exact-node triangulation, or a harmonic representation with measured reconstruction error?
- Which synthetic texture gives the clearest scientific and visual proof without implying a detector acquisition?

## Linked decisions and experiments

- [S2 and MTEX bridge plan](../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md)
- [SHT and spherical harmonics](sht-spherical-harmonic.md)
- [EBSD-map orientations](ebsd-map-orientations.md)

## Promotion trigger

Promote only after `KIKU-F003` is accepted and one reviewed note defines the
aggregate field's physical meaning, orientation convention, normalization, and
two limiting-case tests.

## Present non-goals

- Calling the spherical intensity field an ODF.
- Labeling a texture-weighted aggregate as a single-grain EBSD pattern.
- Adding texture convolution to the first forsterite S2 proof.
- Using an aggregate art view as calibration or detector evidence.
