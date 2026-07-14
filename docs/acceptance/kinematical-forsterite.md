# Forsterite Kinematical Native-Scale Review

- Work item: [KIKU-T018](../work/KIKU-T018.md)
- Production state: Machine-verified bundle retained locally
- Human visual decision: **pending**
- Promoted style fixed before this gate: `quiet`
- Retained density diagnostic: `balanced`

No reviewer observations or next-slice choice are recorded here yet. The files
below must be presented at fit-to-window and 100 percent before this acceptance
record can be completed.

## Objective production run metadata

| Field | Recorded value |
| --- | --- |
| Command | `uv run kikuchi-lab render-kinematical --recipe recipes/kinematical/forsterite-etched-master.yml --output local/runs/kinematical` |
| Recipe | `recipes/kinematical/forsterite-etched-master.yml` |
| Recipe SHA-256 | `83cc714820507e41e8eaee7194dd05d49d78c29a8253a6de1bae362ddc9b9e5d` |
| Recipe ID | `recipe-548d8161fd9e4b3e` |
| Run ID | `kinematical-run-d1dab780ec480f72` |
| Run path | `local/runs/kinematical/kinematical-run-d1dab780ec480f72` |
| Manifest | `local/runs/kinematical/kinematical-run-d1dab780ec480f72/manifest.json` |
| Manifest SHA-256 | `651e7a905343038f0c6075ad717f9b01d2151562def3f6f12267d83311964bd8` |
| Master half size | `1024` |
| Detector shape | `1536 x 2048` |
| Figure size | `2400 x 2400` pixels for raster review figures |
| Master reflector count | `2546` |
| Canonical bundle file count | `16` files before `manifest.json` |
| Observed command wall time | Approximately `119.37 s` in the controllable terminal session |

The single authorized production process reported `0/2`, `1/2` at 50.46 s,
and `2/2` at 100.42 s before completing its detector-coordinate and bundle
publication work with exit status 0. Because visible progress occurred inside
every 60-second interval, no process inspection or stop was required. The
production command was not retried or duplicated.

## Native-scale review inventory

All paths are inside
`local/runs/kinematical/kinematical-run-d1dab780ec480f72`.

| Review asset | Native dimensions | SHA-256 |
| --- | --- | --- |
| `figures/etched-master-balanced.png` | `2400 x 2400` | `4440ccc0e27511aa922f8e9a61d84dc3968109cd100be9a8a8ac5c683171512f` |
| `figures/etched-master-quiet.png` | `2400 x 2400` | `3786dccba0643f775e5add4dc52069b0ceb6c9d6a0e386aac294befd72efb49c` |
| `products/kinematical-master-stereographic.png` | `4098 x 2049` | `5a90c5cbb84c2be8e598b41aca9037923c5ab634aafa41a2e8852c4e51b667ef` |
| `products/kinematical-master-lambert.png` | `4098 x 2049` | `b0c102f6baf2898eb7725cb4905a84518c8d986cd133e12d277bdbdd2e1ce2a3` |
| `products/kinematical-detector.png` | `2048 x 1536` | `5407214b92d4b41b746e3f0ba6ef2fafd2426eb5365266d353e60ad4d5c8f0fc` |
| `figures/kinematical-stereographic-bands.svg` | `1728 x 1728 pt` view box | `a5a2576f8fe8bcb9c2d8804f797c984dbfbe57d317b53fbd282d61e4253da063` |
| `figures/kinematical-spherical-bands.png` | `2400 x 2400` | `091c25260b6805bc4ba38464fc9eb2214a2744f8e5e7ec2eb7eaaa77dd676cf5` |
| `figures/reflector-selection.png` | `2400 x 2400` | `ddad1b915b03afdde18b312856df15e0d21afbbbbad62585b5fec933a4d813e3` |

The canonical six-figure CLI inventory also contains
`figures/kinematical-detector-overlay.png`; the three product PNGs above are
additional bundle exports required by this native-scale gate.

## Human review checklist

### Grayscale hierarchy

- Fit-to-window observation: **pending**
- 100 percent observation: **pending**

### Trace density

- `quiet` observation: **pending**
- `balanced` diagnostic comparison: **pending**

### Node saturation

- Bright zone-axis and crossing behavior: **pending**

### Rim

- Circular rim continuity, weight, and distraction: **pending**

### Quiet regions

- Preservation of low-density and low-intensity regions: **pending**

### Quiet-parameter adjustment

- Whether the fixed `quiet` parameters need a recorded adjustment: **pending**

## Required next-slice decision

- [ ] `pure-kinematical-refinement`
- [ ] `plan-evidence-guided-hybrid`

Human visual decision: **pending**. No hybrid implementation plan is authorized
by this draft record.

## Additive interactive direction

The fixed spherical PNG is present in this gate. Freely rotatable sphere,
GLB, and VTP work remains linked to the
[interactive spherical-view incubator](../incubator/interactive-spherical-view.md)
as an additive viewing and exchange surface; it does not replace the
stereographic, Lambert, detector, or etched-master projected products.

## Machine gate results

The gates were run sequentially after the production bundle was retained:

| Gate | Result |
| --- | --- |
| `uv run pytest -m "not slow and not gpu" -q` | PASS: `443 passed, 1 deselected, 798 warnings in 83.71 s` |
| `uv run ruff check src tests` | PASS: `All checks passed!` |
| `uv run python scripts/validate_work_items.py` | PASS: `Validated 28 work items in docs/work` |
| `uv run python scripts/work_status.py --root .` | PASS: tracker summary completed; `15 done`, `9 ready`, `4 active` |
| `git diff --check` | PASS: no output |

The warnings are upstream `diffpy`/`orix`/`diffsims` deprecations already
exercised by the kinematical tests; no test failed. These machine results do
not constitute human visual acceptance.

## Machine-verifiable final checklist

- [x] Scientific arrays and reflector records are exercised through the pinned public diffsims/kikuchipy pipeline.
- [x] The retained recipe records a dense master threshold separately from the stronger style overlay thresholds.
- [x] `quiet` is the promoted style and `balanced` remains a retained density diagnostic.
- [x] The retained implementation and recipe use no blur-like operation, generated-image layer, or raster edge detector.
- [x] The bundle contains projection and frame ledgers plus circular, spherical, Lambert, and detector products.
- [x] The existing dynamical final bundle and `scientific-clean` test coverage remain passing in the full machine gate.
- [ ] The human visual decision is recorded before any hybrid implementation plan is created.
- [x] The fixed spherical figure is present while interactive sphere, GLB, and VTP work remains linked to its incubator record.
