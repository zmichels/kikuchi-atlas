# Ice Ih detector-to-S2 adapter proof

Status: accepted same-source geometry proof, 2026-07-21.

## Objective

Demonstrate that the declared Ice Ih detector geometry can map raw detector
pixels to the correct covered subset of the package's fixed sample-frame S2
grid, then rank that subset against the Ice candidate cache without silently
inventing values outside the camera's field of view.

## Contract

| Element | Fixed evidence |
| --- | --- |
| Detector source | `kinematical-run-8e0fa453f0869a21/products/kinematical-detector.npy`, hash-checked against the source run manifest. |
| Geometry | `recipes/kinematical/ice-ih-oxygen-quiet-proof.yml`: 1536x2048, TSL PC `(0.50, 0.72, 0.60)`, 70-degree sample tilt, zero detector tilt/azimuth/twist. |
| Direction transform | `kikuchipy.EBSDDetector.sample_to_detector`; sample directions map to gnomonic coordinates and then detector pixels via `to_pixel_coords`. |
| Sampling | Bilinear detector sampling at only in-frame locations; uncovered cache directions are `NaN` plus a false coverage mask. |
| Ranking | Per-mask mean-centered normalized cosine against the candidate cache; this metric is separate from the package's full-S2 metric. |

The proof covers 308 of 1,946 exact package directions. The simulated source
detector ranks the exact identity cache entry `6577` first at `0.999549817`,
with zero angular error from the source run's identity orientation.

## Claim boundary

- This is a same-source simulated geometry proof, not a test against acquired
  EBSD patterns.
- It does not model detector noise, optical response, background, saturation,
  masking policy, or experimental calibration uncertainty.
- The partial-S2 score depends on its coverage mask and cannot be compared
  directly with full-sphere scores or used by the current Rust CLI.
- It does not establish phase-discrimination performance or a general-purpose
  experimental indexing result.

## Reproduction

```bash
uv run python scripts/run_ice_ih_detector_to_s2_adapter_proof.py \
  --output local/dictionaries/ice-ih-detector-to-s2-proof-v0.1.0
```

The append-only output bundle contains the detector-derived partial-S2 values,
coverage mask, detector pixel coordinates, JSON result record, checksums, and
the `detector-to-s2-adapter-overview.png` figure.
