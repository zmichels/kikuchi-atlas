# Forsterite Milestone Acceptance Ledger

- Status: In progress
- Work item: [KIKU-T011](../work/KIKU-T011.md)
- Orientation selection: `orientation-selection-0903bbee65fa3896`
- Current user acceptance: Pending

## Kinematical native-scale gate

The half-size 1024 production bundle
`kinematical-run-d1dab780ec480f72` is retained locally with its manifest and
native-scale review inventory. The promoted style remains `quiet`, while
`balanced` remains a density diagnostic. Machine evidence and the still-empty
human review checklist are recorded in the
[forsterite kinematical acceptance draft](kinematical-forsterite.md).

Human visual decision: **pending**. The draft does not yet choose
`pure-kinematical-refinement` or `plan-evidence-guided-hybrid`.

## Resolution-only source experiment

The first bounded production-source rung changed only Lambert sampling from
257 x 257 to 501 x 501. Both sources use `dmin = 0.08 nm`, Smith rank 8, one
20 keV bin, the same Monte Carlo controls, the same accepted `[011]`
orientation, and the same final detector and processing recipes.

| Evidence | 257 baseline | 501 resolution rung |
| --- | --- | --- |
| Master product | `master-3042267c1739a530` | `master-437f865cd0f68384` |
| Final run | `run-ec3991afa700bc0c` | `run-4088ff482ebb77a2` |
| Master directions | 17,003 | 63,701 |
| Reflections | 2,361 | 2,361 |
| GPU dynamical wall | 532.774 s | 2,104.13 s |
| Gallery mean gradient | 0.009534 | 0.014194 |
| Gallery mid-frequency energy | 0.002224 | 0.003962 |
| Gallery high-frequency energy | 0.000829 | 0.000880 |

The measured runtime ratio is 3.949, close to the 3.746 direction-count ratio.
The 501 projected image correlates strongly with the baseline (`r = 0.9233`),
showing the same broad physical organization rather than a changed
orientation. The final gallery products remain closely related (`r = 0.8646`)
while the 501 rung increases mean gradient by about 49% and resolves finer
within-band structure.

## Runtime and integrity evidence

- CPU-only plan: one bin, 63,701 directions, 2,361 reflections, 7,963 chunks,
  rank 8, and no in-run resumability claim.
- Persistent journal:
  `../../local/benchmarks/forsterite-resolution-501/progress.log`.
- The journal records every chunk, `state=completed`, 2,104.13 s of dynamical
  work, and one completed 20 keV bin.
- Canonical master bundle:
  `../../local/benchmarks/forsterite-resolution-501/COD-9000319-ebsdsim.bundle/`.
- The native master is finite with shape `[2, 501, 501]`; ebsdsim reports the
  requested Metal/GPU path as `gpu_fly_first`, 786,432 Monte Carlo
  trajectories, and convergence.
- Final rendering completed in 18.47 s at a 3072 x 4096 supersampled detector
  projection and 1536 x 2048 final product size.

## Resolution-rung visual review

Resolution alone clearly removes some coarse source sampling and makes narrow
bands and fine crossings more continuous. It also exposes substantially more
fine simulated texture. The result remains more granular than the desired
clarity-forward references, and the brightest zone-axis cores still appear
visually clipped. The rung therefore proves a better-resolved source, but does
not by itself close the aesthetic acceptance gate.

![257-grid gallery baseline](../../local/runs/run-ec3991afa700bc0c/products/gallery-crisp.png)

![501-grid gallery rung](../../local/runs/run-4088ff482ebb77a2/products/gallery-crisp.png)

## Deliberately idealized gallery treatment

The retained 501 master now feeds two explicit processing lineages. The
`scientific-clean` product remains a restrained scientific rendering. The
separately labeled `gallery-crisp` product adds a bounded fine-detail
attenuation stage before contrast and thresholded sharpening. This calms
pixel-scale simulated texture without drawing bands or changing the simulated
orientation.

The first cleanup candidate (`run-aec1bcc29b178f05`) reduced the gallery
95th-percentile gradient from 0.03361 to 0.01724 and was judged too soft. The
balanced candidate, promoted as final run `run-5d91b13abae36c22`, retains half
of the fine residual, restores more mid-frequency energy than the soft
candidate (0.002629 versus 0.002075), and reserves highlight headroom: its
floating-point gallery maximum is 0.9603 rather than a clipped 1.0. It is
therefore the promoted default gallery recipe.

![Original 501 gallery treatment](../../local/runs/run-4088ff482ebb77a2/products/gallery-crisp.png)

![Balanced idealized gallery treatment](../../local/runs/run-5d91b13abae36c22/products/gallery-crisp.png)

## Pending decision

User review should decide whether the balanced idealized treatment closes the
first-pattern aesthetic gate. The 501 source is retained as the spatial
baseline for that review. No `dmin`, rank, or multi-energy promotion is
approved yet; further solver cost remains parked until the source-detail versus
processing-scale tradeoff warrants another rung.
