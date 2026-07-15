# Ice Ih Near-Depth Stepped Presentation Proof

Date: 2026-07-14  
Status: implemented and verified; visual promotion pending user review

## Scope

This proof adds a presentation-only derivative of the accepted Ice Ih oxygen-
sublattice quiet kinematical master. It does not modify the source structure,
the base kinematical recipe, the accepted quiet bundle, or any scientific
intensity array. The derivative combines an exact additional-overlap channel
with coincident vector boundary strokes and an optional center-stroke layer.

No blur, glow kernel, morphology, raster edge detection, spatial denoising,
intermediate resize, displaced shadow, bilinear interpolation, or bicubic
interpolation is present. The only raster interpolation is `nearest`; vector
coverage antialiasing occurs once at final output resolution.

## Runs

Bounded smoke candidate:

- run: `near-depth-run-dfaf4b9dc462e186`
- output root: `local/runs/kinematical-depth-ice-smoke/`
- final canvas: `480 x 480 px`
- elapsed wall time: approximately `14.8 s`

Full review candidate:

- run: `near-depth-run-7744aaa7dcdd20b8`
- output root: `local/runs/kinematical-depth-ice/`
- depth figure: `2400 x 2400 px`
- comparison figure: `4800 x 2400 px`
- overlap diagnostic: `2400 x 2400 px`
- elapsed wall time: approximately `17.0 s`
- manifest SHA-256: `19ecfaeffbdb927d74f4ae470f497e3b7d57f8bd7745791a106a214c5be6713d`

The native-scale review crop is outside the immutable bundle at
`local/review/ice-near-depth/near-depth-edge-intersections-1000.png`.

Enhanced emphasis candidate (the quieter candidate above remains unchanged):

- recipe: `recipes/presentation/ice-ih-near-depth-stepped-emphasis.yml`
- run: `near-depth-run-4625b83f045dc1df`
- output root: `local/runs/kinematical-depth-ice-emphasis/`
- depth figure: `2400 x 2400 px`
- comparison figure: `4800 x 2400 px`
- treatment recipe: `recipe-1c769311997af1fb`
- depth ledger: `depth-ledger-0f23c2caa6f4b2a2`
- manifest SHA-256: `34354c5f81eb16a0643c4b67b9cace4dc07e316e5cda4ada9237a832ff7908bf`
- depth figure SHA-256: `535b7e67dce9b105426f83b838603ed048e653a4984da86225d708a2331d4e32`

Its native-scale review crop is outside the immutable bundle at
`local/review/ice-near-depth-emphasis/near-depth-emphasis-edge-intersections-1000.png`
(SHA-256 `dab0cbf39501bd4a21d28c27dbdaca1261715aef1af105870bfbe72bb37d106c`).

Band-led candidate (both earlier candidates remain unchanged):

- recipe: `recipes/presentation/ice-ih-near-depth-stepped-band-led.yml`
- smoke run: `near-depth-run-e51543f9374fbb48` at `480 x 480 px`
- full run: `near-depth-run-90186c9901710abe`
- output root: `local/runs/kinematical-depth-ice-band-led/`
- treatment recipe: `recipe-87b20ffcc1c965d9`
- depth ledger: `depth-ledger-407c6efe0451709c`
- manifest SHA-256: `3000b975d01bd78b033b0b7b8058d88ef08cba0e283656f48200e259f9cf5046`
- depth figure SHA-256: `4f26c50b32fb4abab01462c0eecc673f786e9576d066a7afa344e3d95da3a882`

Its native-scale review crop is outside the immutable bundle at
`local/review/ice-near-depth-band-led/near-depth-band-led-edge-intersections-1000.png`
(SHA-256 `0798cf0cd0fcacc4aa39e81f14a48708d2f70a34266bf9e9fed38e6e58472ae5`).

## Provenance Identities

- source: `source-f306aaa577129b9e`
- source SHA-256: `4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81`
- base recipe: `recipe-8aa79ffa759eb05b`
- treatment recipe: `recipe-2ef49ca267f26821`
- base stereographic product: `kinematical-e3f91fd7633d3632`
- base stereographic array SHA-256: `d1b6e2763ba77485e2bbf0eace3557ee490bd49c6c8a96b67627badb024610d5`
- depth ledger: `depth-ledger-ed861034cdee288e`

The quiet control hash recorded by the depth ledger is
`28d6f340755f6c6a7c4517b76ae78f79684e9810473080daef69af9512123fc5`.
It exactly matches the pre-treatment accepted
`kinematical-run-8e0fa453f0869a21/figures/etched-master-quiet.png` hash.

## Exact Additional Overlap

The workflow selected 70 signed entries at relative `abs(F)` threshold `0.22`.
Hexagonal symmetrization includes ten duplicate signed entries, so those 70
entries resolve to 60 unique signed Miller indices and 30 unique axial bands.
Distinct harmonic orders such as 002 and 006 remain distinct; only duplicate
entries and exact `hkl`/`-h-k-l` partners collapse.

For every valid upper-stereographic direction `d` and unit reciprocal normal
`n`, band membership is:

```text
abs(dot(d, n)) <= sin(theta_B)
```

Each axial band has weight:

```text
(abs(F_hkl) / max(abs(F))) ^ 2
```

Additional overlap is accumulated without a pixel-by-reflector cube:

```text
overlap_raw = max(sum_weight - max_weight, 0)
```

The realized `99.5` percentile normalization value is
`0.43836911023780567`. The raw overlap `.npy` SHA-256 is
`21b86dab694ce9d80fa1385cc4a2f443935cf0644066dec1922f2e7859a5a466`.

## Pointwise Near-Light and Vector Relief

The pointwise optical-depth treatment uses gain `0.28` and ceiling `0.985`:

```text
tau_base = -log(1 - B / L_max)
tau_final = tau_base + gain * overlap_normalized
L_final = L_max * (1 - exp(-tau_final))
```

Pixels with zero additional overlap are assigned the base luminance exactly.

The boundary threshold `0.34` retains 24 signed reflectors and emits 27 exact
kikuchipy boundary paths. The center threshold `0.22` retains 70 signed
reflectors and emits 55 exact center paths. Every layer draws all coincident
dark casings first and all main strokes second. Consequently, later casings do
not cover earlier luminous intersections, and no directional shadow offset is
introduced.

The depth figure SHA-256 is
`245ab0be7811b9d4f2f234bf7c7f9a1809250ed734a7a24f9d7d51e59655590d`.

## Enhanced Stepped Emphasis

The enhanced recipe advances only the presentation treatment. It keeps the
same source, projection, exact overlap field, reflector thresholds, line
widths, final resolution, and no-blur rendering path. Optical-depth gain moves
from `0.28` to `0.34`; center alpha/casing move from `0.62 / 0.82 pt / 0.38`
to `0.65 / 0.96 pt / 0.44`; boundary alpha/casing move from
`0.48 / 0.82 pt / 0.30` to `0.50 / 0.98 pt / 0.36`.

The emphasis ledger independently confirms `spatial_filter: none`,
`interpolation: nearest`, unchanged 30 axial bands, unchanged 27 boundary
paths, and unchanged 55 center paths. This keeps the aesthetic comparison
diagnostic: any visible difference comes from stronger pointwise overlap and
vector relief, not changed crystallography or geometry.

## Band-Led Treatment

The band-led recipe keeps the exact 30-band overlap field and all 27 selected
kikuchipy boundary paths from the emphasis candidate while explicitly
disabling the fine center-stroke layer. The treatment selects zero center
reflectors and draws zero center paths; its ledger records `enabled: false`,
`geometry_owner: none`, and `draw_order: disabled` for that layer.

Optical-depth gain advances from `0.34` to `0.38`, so broad band luminance and
multi-band intersections carry more of the hierarchy formerly supplied by the
bright center strokes. The boundary style and reflector threshold remain
unchanged. The renderer still records `spatial_filter: none` and
`interpolation: nearest`; no center paths are rendered invisibly or at reduced
opacity.

## Verification

- Recipe parsing: strict field inventory and range validation.
- Scientific tests: antipodal collapse, duplicate handling, harmonic-order
  preservation, exact kikuchipy Bragg-boundary parity, bounded field values,
  intersection weighting, and optical-depth identity/monotonicity.
- Rendering tests: deterministic bytes, unchanged inputs, exact stroke
  propagation, quiet-control byte identity, identical quiet/depth disk inset,
  and casing-before-main draw order.
- Bundle tests: stable content identity, complete six-file inventory, SHA-256
  records, base/source/product links, and atomic no-replace publication.
- Workflow/CLI tests: base recipe ID gate, bounded size override, normalized
  errors, and inventory output.
- Full suite: `784 passed, 1 skipped` in `106.96 s`.
- Enhanced-recipe focused verification: `39 passed` in `8.36 s`.
- Band-led focused verification: `42 passed` in `8.52 s`.
- Work tracker validation: all 31 work items valid with symmetric links.

## Review Gate

The candidate is technically complete and remains `presentation_only`. Visual
promotion is intentionally open until the user evaluates the full frame and
native-scale edge/intersection crop.
