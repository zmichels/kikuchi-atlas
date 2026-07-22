# Ice Ih projection-center sensitivity

Status: accepted synthetic geometry-sensitivity diagnostic, 2026-07-21.

## Objective

Make the projection-center dependency of the current detector-to-S2 adapter
visible before anyone treats its dictionary score as a detector-agnostic
quantity. Hold one source-bound simulated Ice Ih detector field fixed and
independently resample it through a grid of declared PCx/PCy values.

## Fixed method

| Element | Evidence |
| --- | --- |
| Detector image | Checked raw `kinematical-detector.npy` from the Ice Ih source run. |
| Nominal geometry | The declared 1536 x 2048 TSL PC recipe (`PCx=0.50`, `PCy=0.72`, `PCz=0.60`). |
| Perturbation | PCx and PCy offsets from -0.08 to +0.08 in 0.02 increments; PCz and the detector image remain fixed. |
| Observation | Each perturbed camera geometry creates its own bilinearly sampled fixed-S2 signal and coverage mask. |
| Ranking | Frozen Ice Ih cache, coverage-specific mean-centered normalized cosine; top entry compared with the nominal identity orientation. |

## Result

At the declared projection center, the nominal identity candidate (`6577`)
is recovered with masked cosine `0.999549817` and zero direct quaternion
error. Across the intentionally broad synthetic grid, the top-entry angular
error reaches `88.129` degrees. The figure preserves three distinct facts:

- score changes across the PCx/PCy grid;
- some perturbations change the winning coarse orientation rather than merely
  lowering its score; and
- changing the declared camera geometry also changes how many of the fixed S2
  directions lie in the detector footprint.

The response is structured rather than a smooth tolerance curve because this
is a sparse fixed-S2 representation with a discrete cache and coverage mask.
That makes the diagnostic useful as an explicit calibration gate, not as a
universal numerical tolerance.

## Claim boundary

- The offset grid is a sensitivity probe in the recipe's declared PC units. It
  is not a fitted projection center, a measurement uncertainty, or an
  experimentally justified error range.
- The source detector is simulated and source-bound. No acquired calibration
  pattern, noise, background correction, or phase competition is included.
- This does not replace a future geometry-aware detector indexing interface;
  it shows why that interface must require named geometry.

## Reproduction

```bash
uv run python scripts/run_ice_ih_projection_center_sensitivity.py \
  --output local/dictionaries/ice-ih-projection-center-sensitivity-v0.1.0
```
