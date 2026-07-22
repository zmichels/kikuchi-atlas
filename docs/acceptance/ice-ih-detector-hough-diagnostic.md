# Ice Ih detector Hough-space diagnostic

Status: accepted native-resolution image-space diagnostic, 2026-07-21.

## Objective

Expose the actual Hough/Radon-like representation of the checked Ice Ih
detector pattern. The product must distinguish a detector-image line
accumulator from the spherical dictionary's sparse S2 feature vector and keep
all image processing explicit.

## Fixed method

| Element | Evidence |
| --- | --- |
| Source image | Checked raw `kinematical-detector.npy` from `kinematical-run-8e0fa453f0869a21`. |
| Native detector shape | 1536 x 2048 pixels; no downsampling before edge selection or Hough accumulation. |
| Edge signal | Finite-difference gradient magnitude of the raw detector field. |
| Edge selection | Top `0.8%` of gradient magnitudes (`99.2` percentile), retaining 25,166 detector pixels. |
| Smoothing | None. No Gaussian, Canny, tone map, or background operation contributes to the accumulator. |
| Accumulator | Standard image-space line Hough transform across 360 normal-angle samples at 0.5-degree spacing. |
| Output | Gradient field, binary support, raw line accumulator, coordinate vectors, peak records, checksums, and a four-panel figure. |

The native accumulator has shape `5121 x 360`. Its detected peaks are line
hypotheses in image coordinates; the figure shows their connection to the
brightest raw-pattern bands.

## Interpretation

The accumulator has the expected continuous curves and peaks from a real
detector-image line transform, rather than resembling the sparse cache-vector
panel. That visual distinction was intentional: this product is an image-space
diagnostic, while the current candidate matcher has a different
representation and no Hough input path.

## Claim boundary

- Hough peaks are not yet assigned to crystal reflectors or band normals.
- This diagnostic does not incorporate projection-center geometry, phase
  constraints, orientation scoring, or detector calibration.
- It uses a simulated source pattern and provides no acquired-EBSD result.
- The Hough transform is a new diagnostic product, not a silent preprocessing
  replacement for the dictionary adapter.

## Reproduction

```bash
uv run python scripts/run_ice_ih_detector_hough_diagnostic.py \
  --output local/dictionaries/ice-ih-detector-hough-diagnostic-v0.1.0
```

The local bundle is append-only and checksum-bearing.
