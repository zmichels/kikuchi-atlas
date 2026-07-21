# Ice Ih master-to-detector congruence proof

Status: accepted same-source coordinate-congruence proof, 2026-07-21.

## Objective

Demonstrate the project-owned inverse bridge between the canonical Ice Ih
two-hemisphere master and the declared raw detector geometry. The proof should
make a direct pattern-to-pattern comparison possible without replacing the
source detector with a display treatment or silently fitting the intensity.

## Fixed evidence

| Element | Evidence |
| --- | --- |
| Source run | `kinematical-run-8e0fa453f0869a21`, whose raw detector and master file hashes are checked against its manifest. |
| Master identity | Dictionary `ice-ih-spherical-candidate-v0.1.3` contains a byte-identical copy of the source run's `kinematical-master-stereographic.npy`. |
| Detector geometry | 1536 x 2048, TSL PC `(0.50, 0.72, 0.60)`, 70-degree sample tilt, and zero detector tilt/azimuth/twist from `ice-ih-oxygen-quiet-proof.yml`. |
| Geometry operation | Detector pixel to gnomonic ray through `kikuchipy.EBSDDetector`, then detector-frame ray to sample frame through the explicit inverse transform. |
| Master operation | Bilinear raw upper/lower stereographic-master sampling after the active identity crystal-to-sample pullback. |
| Postprocessing | None for the two detector fields. The residual is shown only after each field's own centering and L2 scaling. |

The 3,145,728-pixel proof reports a centered cosine and Pearson correlation of
`0.998537216`, with normalized RMS difference `0.054088520`.

## Interpretation

This is the missing visual counterpart to the partial-S2 adapter: panels one
and two show recognizably Kikuchi-like detector patterns on the same raw
intensity scale; the residual makes their small coordinate/interpolation
difference visible rather than hiding it. The reusable
`reproject_stereographic_master_to_detector()` primitive can now render a
declared orientation through a canonical master and named detector geometry.

## Claim boundary

- Both fields are products of the same checked kinematical run, so this is not
  independent validation of the simulation physics.
- It has no acquired detector image, microscope calibration, background model,
  saturation treatment, or noise model.
- It establishes neither experimental indexing accuracy nor an `ebsdx-rs`
  matcher capability.
- The image is a raw geometry/provenance diagnostic, not an aesthetic
  postprocessing replacement for the Atlas detector figure.

## Reproduction

```bash
uv run python scripts/run_ice_ih_master_detector_congruence.py \
  --output local/dictionaries/ice-ih-master-detector-congruence-v0.1.1
```

The append-only local bundle preserves the reprojected detector field,
normalized residual, metrics record, checksums, and
`master-detector-congruence.png`.
