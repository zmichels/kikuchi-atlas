# Ni 24 dB calibration-pattern Reference Pack intake

Status: gates 1–5 passed for a **source-bound baseline**; public Reference Pack
scope remains pending user approval, 2026-07-23.

## Decision

The Kikuchipy Ni gain dataset at 24 dB is an unusually strong first candidate
for the Open Kikuchi Reference Pack. It is openly licensed, retains raw
acquisition and calibration files, has a documented 20 keV Ni master source,
and supports a small Hough baseline that can be rerun locally.

It is not yet a public Reference Pack release. The remaining decision is
product scope: whether the first release distributes raw patterns, a legal
source pointer plus checksums, or both.

## Intake gates

| Gate | Result | Evidence |
|---|---|---|
| Rights | Pass | Kikuchipy identifies the Zenodo Ni gain series and calibration patterns as CC BY 4.0. |
| Raw values and provenance | Pass | The local source inventory covers 26 files, including Pattern.dat, NORDIF Setting.txt, static backgrounds, and calibration patterns. |
| Geometry/calibration | Pass with declared boundary | The raw settings retain detector, tilt, acquisition, calibration locations, and scan information. The final PC is not stored there; the recipe explicitly uses the cited upstream Hough PC. |
| Phase and master | Pass | The matching 20 keV Ni master is documented as EMsoft-generated and CC BY 4.0; its convenience representation is uint8 stereographic. |
| Rerunnable baseline | Pass | Seven calibration patterns index as Ni through the pinned CPU Hough route. |
| User-approved release scope | Pending | This intake does not decide public artifact distribution or claim a general benchmark. |

## Fixed source-bound method

- Acquisition: kikuchipy.data.ni_gain(number=10), 24 dB, 149 × 200 patterns
  at 60 × 60 pixels, NORDIF UF-1100, 20 keV.
- Calibration: kikuchipy.data.ni_gain_calibration(number=10), seven
  480 × 480 patterns from the same source series.
- Master: kikuchipy.data.nickel_ebsd_master_pattern_small(), 20 keV,
  EMsoft-origin, 401 × 401 uint8 stereographic convenience product.
- Geometry: Bruker PC [0.41835389, 0.22080713, 0.5048758], copied exactly
  from the Hough PC-optimization result in the cited Kikuchipy workflow.
- Processing: divide static background, then divide dynamic background, for
  calibration patterns only.
- Hough path: pyebsdindex==0.3.9.2, 50 selected Ni reflectors.

## Local result

The local runner indexed all 7 of 7 calibration patterns, with mean Hough fit
0.26731613278388977 and mean confidence 0.7579495310783386.

![Ni calibration-pattern source-bound Hough baseline](../../local/reference-packs/ni-gain24db-calibration-hough-v0.1-r3/calibration-hough-baseline.png)

The image is a diagnostic overlay, not a beauty render: white traces are
geometrical simulations from the Hough solutions, and each panel shows its fit
and confidence metric.

## Reproduction

    uv run --with pyebsdindex==0.3.9.2 \
      python scripts/build_ni_gain24db_reference_baseline.py \
      --output local/reference-packs/ni-gain24db-calibration-hough-v0.1

The runner refuses unexpected counts or Hough aggregate metrics, records input
SHA-256 hashes and runtime versions in baseline.json, renders the diagnostic
sheet, and writes checksums for its output files in manifest.json.

## Claim boundary

- This is a source-bound reproduction baseline, not independent orientation
  ground truth.
- The PC is a declared value from the upstream workflow; this runner does not
  re-run that workflow's nonlinear PC search or dynamical refinement.
- The uint8 master is a documented downconverted convenience master, not the
  original float32 EMsoft simulation.
- It does not establish inter-instrument transfer, vendor-format compatibility,
  or broad phase-identification accuracy.

## Sources

- [Ni gain dataset API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.ni_gain.html)
- [Ni calibration-pattern API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.ni_gain_calibration.html)
- [Ni small master-pattern API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.nickel_ebsd_master_pattern_small.html)
- [Upstream hybrid-indexing workflow](https://kikuchipy.org/en/latest/tutorials/hybrid_indexing.html)
