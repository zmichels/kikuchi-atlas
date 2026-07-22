# Ice Ih named photometric stress sheet

Status: accepted synthetic stress diagnostic, 2026-07-22.

## Objective

Make simple detector-image perturbations visible and measurable without
quietly promoting any of them to a recommended preprocessing pipeline. Each
condition retains the same declared detector geometry and runs through the
same partial-S2 sampler and frozen coarse Ice Ih cache.

## Conditions and result

| Named synthetic input | Top entry | Masked cosine | Top error |
| --- | ---: | ---: | ---: |
| Identity | 6577 | 0.999550 | 0.000 degrees |
| Affine contrast (1.6x about the mean) | 6577 | 0.999550 | 0.000 degrees |
| Row illumination ramp (0.8 sigma) | 6577 | 0.942825 | 0.000 degrees |
| Column illumination ramp (0.8 sigma) | 6577 | 0.955061 | 0.000 degrees |
| Upper saturation (source 92nd percentile) | 6577 | 0.861751 | 0.000 degrees |
| Seeded additive noise (0.35 sigma) | 6577 | 0.987060 | 0.000 degrees |

The exact invariance of the affine case follows from the mask-specific
mean-centered cosine metric. The other cases lower score but, within this
narrow source-bound set, do not yet change the coarse winner.

## Claim boundary

- These are deterministic image transformations, not measured detector
  behaviors, preprocessing recommendations, or calibrated noise/illumination
  models.
- The source image and geometry are simulated and matched against the same
  Ice Ih family, so this is not acquired-pattern robustness or phase-
  discrimination evidence.
- No blur is used in any condition.

## Reproduction

```bash
uv run python scripts/run_ice_ih_photometric_stress.py \
  --output local/dictionaries/ice-ih-photometric-stress-v0.1.0
```
