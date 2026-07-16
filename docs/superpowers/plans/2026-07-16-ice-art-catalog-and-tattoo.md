# Ice Art Catalog and Tattoo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one provenance-bearing Ice Ih band catalog, then use it to create a deterministic 145 mm open-silhouette tattoo composition with a canonical black/skin vector master and a later gray-wash/dotwork derivative.

**Architecture:** A new `kikuchi_lab.art_products` package owns immutable art-product contracts. The catalog consumes `PresentationSource.axial_bands`, never an image. The tattoo pipeline actively rotates catalog normals into the approved specimen frame, scores and selects 11 projected great-circle center traces, validates physical geometry, and publishes vector/raster derivatives atomically. The primary line network is authoritative; the secondary treatment can decorate only a verified accepted geometry record.

**Tech Stack:** Python 3.12, NumPy, the existing orix orientation adapter, Matplotlib, Pillow, PyYAML, pytest, Ruff, repo-native tracker and atomic bundle helpers.

## Global Constraints

- Work in `/Users/Z/Documents/kikuchi/.worktrees/spherical-intensity` on `codex/spherical-intensity-implementation`.
- Preserve every pre-existing dirty MTEX/T023 file. In particular, do not edit or stage `pyproject.toml`, `pytest.ini`, `src/kikuchi_lab/spherical_intensity/__init__.py`, or the existing untracked MTEX examples/tests.
- Use test-driven development for every task: write a focused failing test, run it and confirm RED, implement only the named behavior, rerun GREEN, then commit.
- Array-owning frozen dataclasses copy to explicit little-endian dtypes, validate finiteness and shape, and expose no writable NumPy storage.
- Derive identities with `stable_id()` from canonical plain data. Exclude paths, timestamps, durations, and output locations.
- Preserve `s = G_cs c` and `I_sample(s) = I_crystal(G_cs^-1 s)`. Use `orientation_matrix()`; never rotate a PNG or camera.
- The primary tattoo has exactly 11 unique paths: 4 dominant, 4 secondary, 3 fine. It has no rim, detector rectangle, node glyph, halo, or doubled edge.
- Default artboard is 145 mm. Rounded dominant widths are `[4.8, 4.2, 3.6, 3.1]` mm; secondary `[2.5, 2.2, 1.9, 1.6]` mm; fine `[1.2, 1.0, 0.8]` mm.
- Noncrossing edge clearance is at least 1.5 mm. Open endpoints are at least 2.0 mm from unrelated noncrossing paths. True crystallographic crossings are exempt.
- The canonical SVG has black strokes and transparent paper representing untouched skin. Preview skin color is explicitly presentation-only.
- Do not start gray-wash/dotwork until the user accepts the primary geometry. Secondary structural path records and bytes must match the primary exactly.
- Reuse the bounded Ice workflow deadlines. Long source/catalog stages log their finite work summary, stage start/finish, and elapsed time to stderr; progress observations never enter content identity.
- Finish all validation before output-root mutation. Publish via a unique partial directory, fsync, manifest last, and atomic no-replace promotion.
- Add no dependency; use the existing stack and standard library.

## File Responsibility Map

| File | Responsibility |
| --- | --- |
| `art_products/contracts.py` | Immutable catalog and tattoo geometry identities |
| `art_products/catalog.py` | Tie-aware ranking, eligibility, four cohorts, snapshot I/O |
| `art_products/tattoo_recipe.py` | Strict version-1 physical/art recipe |
| `art_products/tattoo_selection.py` | Active rotation, center traces, scoring, allocation |
| `art_products/tattoo_vector.py` | Crop, physical polylines, clearances, SVG/PDF/PNG |
| `art_products/tattoo_bundle.py` | Full preflight and atomic publication |
| `workflows/ice_art_catalog.py` | Bounded real-Ice catalog build |
| `workflows/ice_tattoo.py` | Catalog-consuming primary/secondary workflows |
| `cli/main.py` | `build-ice-art-catalog` and `render-ice-tattoo` |

---

## Task 1: Promote the art feature and define immutable contracts

**Files:**

- Modify: `docs/work/KIKU-E001.md`
- Create: `docs/work/KIKU-F005.md`, `KIKU-T028.md`, `KIKU-T029.md`, `KIKU-T030.md`, `KIKU-T031.md`
- Modify: `docs/work/index.md`
- Create: `src/kikuchi_lab/art_products/__init__.py`
- Create: `src/kikuchi_lab/art_products/contracts.py`
- Test: `tests/unit/test_art_product_contracts.py`

- [ ] **Step 1: Write RED tests**

Test frozen `ArtBandMember`, `ArtBandCatalog`, `TattooPath`, and `TattooGeometry` objects. Require a nonzero integer HKL, unit normal within `5e-13`, positive finite half width/strength, weight in `(0,1]`, cohort in `{1,2,3,4,None}`, lowercase SHA-256, path points shaped `(N,2)` with `N >= 2`, supported tier literals, unique member/path IDs, and fixed projection `upper_specimen_stereographic_center_trace`. Verify catalog identity is independent of filesystem location and geometry identity changes for a `0.01 mm` coordinate change.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_art_product_contracts.py -q
```

Expected: import failure for `kikuchi_lab.art_products`.

- [ ] **Step 3: Implement exact contracts**

`ArtBandMember` stores HKL, crystal normal, Bragg half width, structure-factor magnitude, normalized weight, optional globe cohort, globe/tattoo eligibility, acceptance state, and reason. Its `member_id` includes only intrinsic band evidence and source-independent numeric values, not cohort or human policy.

`ArtBandCatalog` stores schema version, structure ID/SHA, source recipe ID, presentation recipe ID, eligibility threshold, and ordered members. Its `catalog_id` hashes its complete canonical content.

`TattooPath` stores path/member IDs, tier, width, immutable `<f8` points, score components, and selection reason. `TattooGeometry` stores schema, catalog/orientation IDs, artboard, ordered paths, and projection. Its identity includes coordinate SHA-256 values and all physical widths.

- [ ] **Step 4: Add tracker hierarchy**

Create `KIKU-F005: Ice Ih science-art products` under `KIKU-E001`, with symmetric ready/P1 children: T028 shared catalog, T029 primary tattoo, T030 relief globe, and T031 gray-wash/dotwork. T031 explicitly depends on accepted T029. Link the approved spec and both implementation plans.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/test_art_product_contracts.py -q
uv run python scripts/validate_work_items.py
uv run ruff check src/kikuchi_lab/art_products tests/unit/test_art_product_contracts.py
git add docs/work/KIKU-E001.md docs/work/KIKU-F005.md docs/work/KIKU-T028.md docs/work/KIKU-T029.md docs/work/KIKU-T030.md docs/work/KIKU-T031.md docs/work/index.md src/kikuchi_lab/art_products/__init__.py src/kikuchi_lab/art_products/contracts.py tests/unit/test_art_product_contracts.py
git commit -m "feat: define Ice art product contracts"
```

---

## Task 2: Build the tie-aware shared band catalog

**Files:**

- Create: `src/kikuchi_lab/art_products/catalog.py`
- Create: `recipes/art/ice-ih-band-catalog.yml`
- Test: `tests/unit/test_art_band_catalog.py`
- Test: `tests/scientific/test_art_band_catalog_scientific.py`

- [ ] **Step 1: Write RED tests**

Use a synthetic `PresentationSource` with 12 axial bands and repeated weights at two cohort boundaries. Assert four nonempty cohorts; equal weights never split; output ordering is normalized weight descending, HKL ascending, member ID ascending; eligibility is inclusive at `0.10`; and forge/missing/additional-key snapshot cases fail. Reject fewer than four unique eligible weight blocks, duplicate HKLs, nonpositive thresholds, and source/weight length mismatch.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_art_band_catalog.py tests/scientific/test_art_band_catalog_scientific.py -q
```

- [ ] **Step 3: Implement catalog builder and strict JSON I/O**

Public interfaces:

- `build_art_band_catalog(source, source_structure_id, source_structure_sha256, source_recipe_id, presentation_recipe_id, eligibility_min_weight) -> ArtBandCatalog`
- `write_art_band_catalog(path, catalog) -> None`
- `load_art_band_catalog(path) -> ArtBandCatalog`

Partition equal-weight blocks, not members. Choose the three block boundaries minimizing squared distance of cumulative member counts to 25%, 50%, and 75%, with all cohorts nonempty. Cohort 4 is strongest and 1 weakest. Canonical JSON uses sorted keys, two-space indent, trailing newline, top-level `catalog_id` and `content`. Loading reconstructs and revalidates all IDs.

The strict tracked YAML has schema 1, the oriented Ice recipe link, threshold `0.10`, cohort count 4, `keep_equal_weights_together`, ranking `normalized_structure_factor_weight`, `presentation_only`, and `science_art`.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_art_band_catalog.py tests/scientific/test_art_band_catalog_scientific.py -q
uv run ruff check src/kikuchi_lab/art_products tests/unit/test_art_band_catalog.py tests/scientific/test_art_band_catalog_scientific.py
git add src/kikuchi_lab/art_products/catalog.py recipes/art/ice-ih-band-catalog.yml tests/unit/test_art_band_catalog.py tests/scientific/test_art_band_catalog_scientific.py docs/superpowers/plans/2026-07-16-ice-art-catalog-and-tattoo.md
git commit -m "feat: rank shared Ice art bands"
```

---

## Task 3: Publish a bounded real-Ice catalog bundle

**Files:**

- Create: `src/kikuchi_lab/art_products/catalog_bundle.py`
- Create: `src/kikuchi_lab/workflows/ice_art_catalog.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Test: `tests/unit/test_art_catalog_bundle.py`
- Test: `tests/integration/test_ice_art_catalog.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write RED tests**

Before output mutation, reject forged source/presentation recipe IDs and catalog IDs. Require `art-band-catalog.json`, `catalog-recipe.json`, `catalog-ledger.json`, then manifest. Test stable run ID across parent directories, completed/partial collision behavior, and CLI parsing for `build-ice-art-catalog --recipe recipes/art/ice-ih-band-catalog.yml --output local/ice-art-catalog`.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_art_catalog_bundle.py tests/integration/test_ice_art_catalog.py tests/unit/test_cli.py -q
```

- [ ] **Step 3: Implement workflow and atomic publisher**

Implement `build_ice_art_catalog(*, recipe_path, output_root) -> IceArtCatalogResult`. Resolve the oriented, spherical, kinematical, source, and presentation records through the same validation chain as `oriented_spherical.py`; build the bounded Ice simulation once; create `PresentationSource`; build the catalog; preflight all identities; publish with existing internal fsync/no-replace helpers. Ledger source structure/SHA, all recipe IDs, catalog ID, member/cohort counts, policies, and claim boundaries.

CLI emits sorted JSON with run ID, path, catalog ID, member count, and manifest SHA.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_art_catalog_bundle.py tests/integration/test_ice_art_catalog.py tests/unit/test_cli.py -q
uv run ruff check src/kikuchi_lab/art_products src/kikuchi_lab/workflows/ice_art_catalog.py src/kikuchi_lab/cli/main.py
git add src/kikuchi_lab/art_products/catalog_bundle.py src/kikuchi_lab/workflows/ice_art_catalog.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_art_catalog_bundle.py tests/integration/test_ice_art_catalog.py tests/unit/test_cli.py
git commit -m "feat: publish Ice art band catalog"
```

---

## Task 4: Select 11 rotated center traces deterministically

**Files:**

- Create: `src/kikuchi_lab/art_products/tattoo_recipe.py`
- Create: `src/kikuchi_lab/art_products/tattoo_selection.py`
- Create: `recipes/art/ice-ih-tattoo.yml`
- Test: `tests/unit/test_tattoo_recipe.py`
- Test: `tests/scientific/test_tattoo_selection.py`

- [ ] **Step 1: Write RED tests**

Require active Bunge `(17,31,43)`, 145 mm, allocation `(4,4,3)`, the exact widths above, 721 great-circle samples, crop radius `0.90`, no rim/nodes/filter, and black/skin palette. Reject every out-of-contract value. With 18 synthetic catalog members, assert 11 unique selected IDs, exact tier counts, sample normals equal `orientation_matrix(recipe.orientation) @ normal_crystal`, a redundant candidate excluded as `angular_redundancy`, and numeric score components for strength, angular width, nonredundancy, coverage, and zone relationship.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_tattoo_recipe.py tests/scientific/test_tattoo_selection.py -q
```

- [ ] **Step 3: Implement projection and scoring**

For each rotated plane normal, construct a deterministic orthonormal basis; sample its great circle; retain the continuous upper-hemisphere arc; map with `x=sx/(1+sz)`, `y=sy/(1+sz)`. Score `0.40 strength + 0.15 angular_width + 0.20 nonredundancy + 0.15 coverage + 0.10 zone_relationship`. Greedy ties are total score descending, weight descending, ID ascending. Reject acute axial-normal separations under 4 degrees. Coverage uses six midpoint azimuth sectors. Zone score rewards crossings at least 6 degrees inside the crop. Ledger every score and rejection.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_tattoo_recipe.py tests/scientific/test_tattoo_selection.py -q
uv run ruff check src/kikuchi_lab/art_products/tattoo_recipe.py src/kikuchi_lab/art_products/tattoo_selection.py
git add src/kikuchi_lab/art_products/tattoo_recipe.py src/kikuchi_lab/art_products/tattoo_selection.py recipes/art/ice-ih-tattoo.yml tests/unit/test_tattoo_recipe.py tests/scientific/test_tattoo_selection.py
git commit -m "feat: select rotated Ice tattoo paths"
```

---

## Task 5: Build, validate, and serialize the primary vector geometry

**Files:**

- Create: `src/kikuchi_lab/art_products/tattoo_vector.py`
- Test: `tests/unit/test_tattoo_vector.py`
- Test: `tests/scientific/test_tattoo_clearance.py`

- [ ] **Step 1: Write RED tests**

Assert exact ordered IDs/widths, open polylines, centered 145 mm transform, no duplicate consecutive points, and deterministic geometry ID. Synthetic cases prove true intersections are exempt, 1.49 mm noncrossing edge gap fails, 1.99 mm endpoint clearance fails, and a closed path fails. SVG must have 11 black `path` elements, `fill="none"`, rounded caps/joins, and no `circle`, `rect`, background, rim, or node element.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py -q
```

- [ ] **Step 3: Implement geometry and canonical SVG**

Clip sampled polylines analytically at the `0.90` crop circle; discard boundary-only fragments; transform to millimeters; compute float64 segment intersections and distances. Edge gap subtracts half both stroke widths. Endpoint clearance subtracts half the unrelated width. Serialize six fixed decimals and manually sorted XML attributes. Expose `build_tattoo_geometry`, `validate_tattoo_geometry`, and `primary_svg_bytes`.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py -q
uv run ruff check src/kikuchi_lab/art_products/tattoo_vector.py
git add src/kikuchi_lab/art_products/tattoo_vector.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py
git commit -m "feat: construct Ice tattoo vector geometry"
```

---

## Task 6: Render deterministic PDF and PNG derivatives

**Files:**

- Modify: `src/kikuchi_lab/art_products/tattoo_vector.py`
- Test: `tests/unit/test_tattoo_render.py`

- [ ] **Step 1: Write RED tests**

Render twice and require byte-identical SVG/PDF/mockup/stencil hashes. Require 145 mm PDF MediaBox within 0.02 mm and 1713 by 1713 PNGs at 300 dpi. Input geometry hashes cannot change.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_tattoo_render.py -q
```

Expected: missing render contract or function failure.

- [ ] **Step 3: Implement renderer**

Use the same physical point arrays for all formats. Matplotlib PDF figure size is `145/25.4` inches, exact bounds/no margins, compression zero, fixed Creator, and null creation/modification dates. Mockup background is labeled `#d8b59a`; stencil is black/white. Re-save PNG through Pillow with fixed compression and no metadata.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_tattoo_render.py -q
uv run ruff check src/kikuchi_lab/art_products/tattoo_vector.py tests/unit/test_tattoo_render.py
git add src/kikuchi_lab/art_products/tattoo_vector.py tests/unit/test_tattoo_render.py
git commit -m "feat: render Ice tattoo art derivatives"
```

---

## Task 7: Publish the primary tattoo proof

**Files:**

- Create: `src/kikuchi_lab/art_products/tattoo_bundle.py`
- Create: `src/kikuchi_lab/workflows/ice_tattoo.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`, `src/kikuchi_lab/cli/main.py`
- Create: `docs/acceptance/ice-ih-tattoo-primary.md`
- Modify: `docs/work/KIKU-T028.md`, `docs/work/KIKU-T029.md`
- Test: `tests/unit/test_tattoo_bundle.py`, `tests/integration/test_ice_tattoo.py`, `tests/unit/test_cli.py`

- [ ] **Step 1: Write RED tests**

Require primary SVG/PDF/mockup/stencil, recipe, catalog, selection ledger, path geometry, gap diagnostic, tattoo-artist disclaimer, and manifest. Before mutation reject forged IDs, wrong orientation, wrong path count, changed width/coordinate hash, gap violation, nonblack SVG, and absent disclaimer. Test collisions and CLI `render-ice-tattoo --catalog /tmp/ice-art-catalog/art-band-catalog.json --recipe recipes/art/ice-ih-tattoo.yml --output /tmp/ice-tattoo --treatment primary`.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_tattoo_bundle.py tests/integration/test_ice_tattoo.py tests/unit/test_cli.py -q
```

Expected: missing publisher, workflow, and command failures.

- [ ] **Step 3: Implement and run real proof**

Implement `render_ice_tattoo` returning run/path/catalog/geometry/treatment/manifest fields. Primary preflight rebuilds selection and geometry from strict inputs, verifies rendered formats, then publishes atomically. Graywash arguments raise `graywash requires accepted primary geometry` until Task 9. Disclaimer says science-art is not medical guidance or a skin-approved stencil and requires qualified tattoo-artist review.

Run the real catalog then primary proof. Record commands, IDs, hashes, dimensions, tests, and local artifact locations in acceptance. Mark T028 done; keep T029 active with visual review open.

- [ ] **Step 4: Full verification and commit**

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/validate_work_items.py
git diff --check
git add src/kikuchi_lab/art_products/tattoo_bundle.py src/kikuchi_lab/workflows/ice_tattoo.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py docs/acceptance/ice-ih-tattoo-primary.md docs/work/KIKU-T028.md docs/work/KIKU-T029.md tests/unit/test_tattoo_bundle.py tests/integration/test_ice_tattoo.py tests/unit/test_cli.py
git commit -m "feat: publish primary Ice tattoo proof"
```

---

## Task 8: Human review gate for the primary geometry

- [ ] **Step 1: Present the primary candidate**

Show the full-scale mockup, stencil, and thumbnail. Ask whether the 11-path hierarchy, dominant ribbon widths, open crop, and natural crossings are accepted.

- [ ] **Step 2: Respond through source controls**

If revised, change recipe/scoring and regenerate; never hand-edit SVG. Rerun Task 7's focused and full verification after any revision.

- [ ] **Step 3: Record explicit acceptance**

After explicit acceptance, record the quote, date, primary run ID, geometry ID, and manifest SHA in `docs/acceptance/ice-ih-tattoo-primary.md`; mark T029 done; commit only those documentation/tracker files with message `docs: accept primary Ice tattoo geometry`.

Do not start Task 9 before this gate.

---

## Task 9: Publish the secondary dotwork treatment

**Files:**

- Create: `src/kikuchi_lab/art_products/tattoo_treatment.py`
- Modify: `src/kikuchi_lab/art_products/tattoo_bundle.py`, `src/kikuchi_lab/workflows/ice_tattoo.py`
- Create: `docs/acceptance/ice-ih-tattoo-graywash.md`
- Modify: `docs/work/KIKU-T031.md`
- Test: `tests/unit/test_tattoo_graywash.py`, `tests/integration/test_ice_tattoo.py`

- [ ] **Step 1: Write RED geometry-lock tests**

Require an approval JSON naming primary run, geometry, manifest, author, date, rationale. Reject absent/mismatched approval. Structural path records and SVG path lines must be byte-identical. Dot centers stay at least 3 mm from crossings and 2 mm from endpoints.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_tattoo_graywash.py tests/integration/test_ice_tattoo.py -q
```

Expected: missing treatment implementation and geometry-lock failures.

- [ ] **Step 3: Implement restrained deterministic dotwork**

Seed PCG64 from the geometry SHA. Generate dots only in 3-7 mm corridors around dominant paths, minimum 1.2 mm center separation, radii `{0.18,0.24,0.30}` mm, opacities `{0.18,0.26,0.34}`. Add only a `dotwork-atmosphere` group; never modify/add structural paths or emphasize nodes. Publish secondary SVG/PDF/mockup plus primary geometry, treatment, approval, disclaimer, manifest.

- [ ] **Step 4: Verify and commit candidate**

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/validate_work_items.py
git diff --check
git add src/kikuchi_lab/art_products/tattoo_treatment.py src/kikuchi_lab/art_products/tattoo_bundle.py src/kikuchi_lab/workflows/ice_tattoo.py docs/acceptance/ice-ih-tattoo-graywash.md docs/work/KIKU-T031.md tests/unit/test_tattoo_graywash.py tests/integration/test_ice_tattoo.py
git commit -m "feat: add accepted-geometry Ice dotwork derivative"
```

Keep T031 active until separate visual approval.

---

## Completion Checklist

- [ ] Catalog identities and four tie-aware cohorts recompute from snapshots.
- [ ] Primary uses active Bunge `(17,31,43)` and exactly 11 catalog center traces.
- [ ] SVG/PDF/PNG share one physical geometry record and reproduce byte-for-byte.
- [ ] No blur, raster tracing, rim, nodes, halo, or doubled edges.
- [ ] Width, gap, endpoint, scale, and palette checks pass before publication.
- [ ] Primary acceptance precedes secondary generation.
- [ ] Secondary structural bytes match accepted primary bytes.
- [ ] Full pytest, Ruff, tracker, and diff checks pass without touching protected dirty files.
