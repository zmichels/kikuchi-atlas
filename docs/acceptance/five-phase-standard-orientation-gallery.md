# Five-Phase Standard Orientation Gallery Acceptance

- Work item: [KIKU-T036](../work/KIKU-T036.md)
- Design: [five-phase standard orientation-gallery design](../superpowers/specs/2026-07-17-five-phase-standard-orientation-gallery-design.md)
- Plan: [implementation plan](../superpowers/plans/2026-07-17-five-phase-standard-orientation-gallery.md)
- Product boundary: direct-reflector science-art hemispheres; this is **not** a
  quantitative EBSD master pattern.

## Retained publication

The following command was run once against a previously absent output root:

```text
uv run kikuchi-lab render-phase-art-orientation-gallery \
  --recipe recipes/art/five-phase-standard-orientation-gallery.yml \
  --parity-root local/phase-general-direct-reflector-art/parity \
  --output local/phase-general-direct-reflector-art/orientation-gallery
```

The command declared its finite work before publication:

```text
phase-art-orientation-gallery finite-work phases=5 orientations=3 cells=15 simulation_count=0
```

It atomically promoted the complete gallery root after the preflight, cell
bundles, and sheet bundle completed:

- Gallery root: `local/phase-general-direct-reflector-art/orientation-gallery`
- Comparison sheet: `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-sheet-2e035fcbc2398433/orientation-gallery-comparison.png`
- Comparison sheet: `4500 x 2700 px`, RGB
- Comparison bundle: `orientation-gallery-sheet-2e035fcbc2398433`
- Comparison ledger: `orientation-gallery-comparison-ledger-385585589afb431e`
- Comparison SHA-256: `a202e7eb2555eb86ec7a37d7300564f7812e4fbb737545f3d16819917c921b94`
- Comparison-manifest SHA-256: `a2fef67df8c7cc8ab60a5496fb9bd9f5d267e9fba405d75b938762386a265bef`
- Recipe SHA-256: `d20276387c87a25824717d13bdbcc7faee6d03fea5a9f58cc8817ca2d32bcdd7`
- Renderer: `direct-pillow-rgb-vector-v1`
- Gallery simulation count: `0` for every cell and the sheet.

The separately retained, passed parity reports are the bounded diagnostic
source evidence; they each retain their own one-master parity simulation.
No EBSD master-pattern simulation was calculated for this gallery.

## Approved orientation table

| Variant | Active Bunge Euler angles (degrees) | Frame | Orientation ID |
| --- | --- | --- | --- |
| `azimuthal-60` | `[77.0, 31.0, 43.0]` | `crystal_to_sample` | `orientation-aafeef81ff32f9b3` |
| `tilt-plus-20` | `[17.0, 51.0, 43.0]` | `crystal_to_sample` | `orientation-c0a21796ab58a83a` |
| `oblique-high` | `[97.0, 71.0, 83.0]` | `crystal_to_sample` | `orientation-76e99b6fc9f091e2` |

Each cell has exactly one retained standard-width selection and one retained
geometry. The reader rebuilt and validated each 11-path geometry, its full
stereographic hemisphere boundary, and the matching SVG stroke/clip contract.

## Cell and parity inventory

| Cell | Selection ID | Geometry ID | Direct catalog ID | Passed parity report |
| --- | --- | --- | --- | --- |
| `azimuthal-60:ice-ih` | `tattoo-selection-b2c9961f0dd6398a` | `tattoo-geometry-c4b694280310ab59` | `art-band-catalog-627acdd57e1aa127` | `reflector-parity-report-02ca6310f31b3480` |
| `azimuthal-60:forsterite` | `tattoo-selection-bd626a1d5320799e` | `tattoo-geometry-e6fe64ac080b625d` | `art-band-catalog-94ae354258f66b7e` | `reflector-parity-report-c5512a4eedee1455` |
| `azimuthal-60:quartz` | `tattoo-selection-8bfaa4e9b6dce529` | `tattoo-geometry-3df3aaa735277298` | `art-band-catalog-4f9fc8f1789aea65` | `reflector-parity-report-d98098d829dd6039` |
| `azimuthal-60:zircon` | `tattoo-selection-6fc5fa390b108f52` | `tattoo-geometry-6a3da669e599f846` | `art-band-catalog-52a01924f3a8eee2` | `reflector-parity-report-5dd4e0888cee4596` |
| `azimuthal-60:titanite` | `tattoo-selection-90d7e10109253b45` | `tattoo-geometry-8b4afe360bfe34ea` | `art-band-catalog-2c160b67af3953d5` | `reflector-parity-report-2c870292a35a5d4a` |
| `tilt-plus-20:ice-ih` | `tattoo-selection-43c074b8a15a38f5` | `tattoo-geometry-ffaf8b2f5d319f53` | `art-band-catalog-627acdd57e1aa127` | `reflector-parity-report-02ca6310f31b3480` |
| `tilt-plus-20:forsterite` | `tattoo-selection-9a43adebc6c83fdf` | `tattoo-geometry-5ae490b9555a6c34` | `art-band-catalog-94ae354258f66b7e` | `reflector-parity-report-c5512a4eedee1455` |
| `tilt-plus-20:quartz` | `tattoo-selection-f662b4b89a49e393` | `tattoo-geometry-2986a29e23611fe0` | `art-band-catalog-4f9fc8f1789aea65` | `reflector-parity-report-d98098d829dd6039` |
| `tilt-plus-20:zircon` | `tattoo-selection-37b4aa0a034dca76` | `tattoo-geometry-45e78a0e6a5cfe8b` | `art-band-catalog-52a01924f3a8eee2` | `reflector-parity-report-5dd4e0888cee4596` |
| `tilt-plus-20:titanite` | `tattoo-selection-ba2a04e244c186ff` | `tattoo-geometry-84746c0ff189b3ff` | `art-band-catalog-2c160b67af3953d5` | `reflector-parity-report-2c870292a35a5d4a` |
| `oblique-high:ice-ih` | `tattoo-selection-a05a2bed9f742b9d` | `tattoo-geometry-f8659632dc1e7278` | `art-band-catalog-627acdd57e1aa127` | `reflector-parity-report-02ca6310f31b3480` |
| `oblique-high:forsterite` | `tattoo-selection-5d4c24662634ec31` | `tattoo-geometry-746d69869ebf560a` | `art-band-catalog-94ae354258f66b7e` | `reflector-parity-report-c5512a4eedee1455` |
| `oblique-high:quartz` | `tattoo-selection-b2bf4da5f51cfe93` | `tattoo-geometry-290426214afee7d6` | `art-band-catalog-4f9fc8f1789aea65` | `reflector-parity-report-d98098d829dd6039` |
| `oblique-high:zircon` | `tattoo-selection-eaefa753a000d6f1` | `tattoo-geometry-a19e8f873ed49097` | `art-band-catalog-52a01924f3a8eee2` | `reflector-parity-report-5dd4e0888cee4596` |
| `oblique-high:titanite` | `tattoo-selection-b82fa49ea9bb94fc` | `tattoo-geometry-1c6c0820c9f28563` | `art-band-catalog-2c160b67af3953d5` | `reflector-parity-report-2c870292a35a5d4a` |

The phase-local parity sources are retained at:

| Phase | Parity source |
| --- | --- |
| Ice Ih | `local/phase-general-direct-reflector-art/parity/reflector-parity-run-2fc04ef7acef94c4/reflector-parity-report.json` |
| Forsterite | `local/phase-general-direct-reflector-art/parity/reflector-parity-run-83f8b8e06f963665/reflector-parity-report.json` |
| Quartz | `local/phase-general-direct-reflector-art/parity/reflector-parity-run-e7a0912120a5df91/reflector-parity-report.json` |
| Zircon | `local/phase-general-direct-reflector-art/parity/reflector-parity-run-fb301916800e50e4/reflector-parity-report.json` |
| Titanite | `local/phase-general-direct-reflector-art/parity/reflector-parity-run-fd5c960ece11c250/reflector-parity-report.json` |

For every cell, the direct catalog's retained source-structure ID and SHA-256
match the passed parity report copied into that cell bundle.

## Read-only verification

The committed, read-only verifier rechecks the retained publication without
rendering or changing it. It accepts the published gallery and parity roots
explicitly:

```text
uv run python scripts/verify_orientation_gallery.py \
  --gallery-root local/phase-general-direct-reflector-art/orientation-gallery \
  --parity-root local/phase-general-direct-reflector-art/parity
```

Observed output:

```text
orientation-gallery-probe PASS root=local/phase-general-direct-reflector-art/orientation-gallery cells=15 artifacts_checked=137 parity_reports=5
```

The verifier loads the recipe and source-series policy, sheet ledger, all 15
cell manifests, the 5 passed parity reports, and every retained artifact. It
recomputes content-addressed cell/sheet IDs and manifest-listed SHA-256
entries, rebuilds each geometry from JSON, runs geometry and SVG boundary
validation, and checks catalog/parity source-structure identity. It also
asserts the approved orientation table, 15 unique `(phase_slug, variant_slug)`
pairs, the exact 3-by-5 order, standard treatment and
`arc_width_scale == 1.0`, one 11-path selection and one geometry per cell,
complete circular boundaries, checksum-valid inventories, and
`simulation_count == 0` for each gallery record.

## Native visual inspection

The 4500 x 2700 comparison sheet and one native 1713 x 1713 child stencil for
each phase were opened directly:

- `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-cell-bca1b2621044a96b/ice-ih-azimuthal-60-stencil.png`
- `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-cell-9b08b8d2311d3fd8/forsterite-azimuthal-60-stencil.png`
- `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-cell-750e569205dc696c/quartz-azimuthal-60-stencil.png`
- `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-cell-f475ac06fa7942f5/zircon-azimuthal-60-stencil.png`
- `local/phase-general-direct-reflector-art/orientation-gallery/orientation-gallery-cell-ebd0a69bbd4c7c2f/titanite-azimuthal-60-stencil.png`

Observed: every panel retains a complete circular hemisphere boundary and a
white ground with black, single-stroke vector hierarchy. The comparison labels
are outside each circle. Each phase changes visibly across the three rows, so
the result does not read as a camera-only or flat-raster rotation. No clipping
of the circular boundaries was seen.

## Repository verification

| Gate | Result |
| --- | --- |
| Retained gallery verifier | PASS: 15 cells, 137 checksum-validated artifacts, 5 passed parity reports |
| `uv run pytest -q` | Inconclusive: the one invoked full-suite process exited after emitting progress through `5%`, but its terminal wrapper did not return the final summary or exit status. It was not rerun. |
| `uv run ruff check src tests` | PASS: `All checks passed!` |
| `uv run python scripts/validate_work_items.py` | PASS: `Validated 43 work items in docs/work` |
| `git diff --check` | PASS: exit `0` |

The retained-product criteria are complete. KIKU-T036 remains active only
because the fresh full-suite result was not observable from the one allowed
invocation; do not infer a passing full suite from its partial output.
