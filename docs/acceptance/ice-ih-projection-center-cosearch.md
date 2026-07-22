# Ice Ih finite projection-center co-search

Status: accepted synthetic geometry-candidate proof, 2026-07-22.

## Objective

Advance the projection-center sensitivity diagnostic into a safe finite
candidate comparison. The central rule is that every proposed geometry must be
scored on the same S2 directions; otherwise score changes can merely reflect a
different detector footprint rather than a better geometric explanation.

## Fixed method

| Element | Evidence |
| --- | --- |
| Source | Checked simulated Ice Ih detector field and its source detector recipe. |
| Candidate set | 81 PCx/PCy candidates: -0.08 to +0.08 offsets in 0.02 increments; PCz fixed. |
| Common signal support | Intersection of all 81 detector-to-S2 coverage masks: 231 of the fixed 1,946 sample-frame directions. |
| Per-candidate match | Same raw detector pixels sampled through each proposed geometry, then ranked against the frozen Ice Ih cache with the shared mask. |
| Result selection | Stable descending top-candidate score, then candidate-order tie break. |

## Result

The best finite candidate is the source-declared offset `(delta PCx, delta
PCy) = (0.000, 0.000)`. It returns identity cache entry `6577` with comparable
masked cosine `0.998847246`. The retained figure distinguishes the common
231-direction support used for ranking from each candidate's native coverage
count.

## Claim boundary

- This is a discrete source-bound candidate-grid proof, not a continuous
  projection-center optimizer, a detector calibration result, or a physical
  uncertainty estimate.
- No acquired pattern, external reference geometry, detector distortion,
  background model, or phase competition is included.
- PCx/PCy are the only varied variables. Pixel orientation, tilts, PCz,
  binning, and distortion remain future explicitly declared search dimensions.

## Reproduction

```bash
uv run python scripts/run_ice_ih_projection_center_cosearch.py \
  --output local/dictionaries/ice-ih-projection-center-cosearch-v0.1.0
```
