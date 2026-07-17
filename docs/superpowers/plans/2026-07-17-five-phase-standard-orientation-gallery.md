# Five-Phase Standard-Width Orientation Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a separate, reproducible 3-by-5 gallery of fifteen zero-master direct-reflector hemisphere figures: three active Bunge crystal-to-sample orientations for each of Ice Ih, forsterite, alpha-quartz, zircon, and titanite.

**Architecture:** Keep the current five-phase standard/wide family immutable. Add a versioned orientation-gallery recipe, a standard-only feasibility selector, generic immutable per-cell publication, and a dedicated comparison-sheet renderer. Reuse catalog/parity evidence through an extracted direct-phase preflight seam; calculate the orientation by rotating crystal normals before the great-circle geometry is built.

**Tech Stack:** Python 3.12, NumPy, Pillow, PyYAML, SVG text emission, `uv`, pytest, Ruff, existing repo-native work tracker.

## Global Constraints

- A gallery orientation is an active Bunge ZXZ `crystal_to_sample` rotation. For every reflector normal, use `normal_sample = orientation_matrix @ normal_crystal`; do not rotate a camera or an already rendered raster.
- Publish exactly five phases times three named variants = fifteen standard-width cells. The base five-phase family, its wide selector, and the frozen Ice reference remain unchanged.
- The gallery must run with `simulation_count = 0`; it reuses only retained direct-catalog and passing parity evidence. It must not invoke a master-pattern workflow.
- Each cell must select exactly eleven reflectors through deterministic bounded search, preserve the existing path hierarchy and circular boundary, and resolve physical clearance before any publication.
- A trace producing zero or multiple interior crop fragments is a branchable geometry conflict. It is not a crash and it is not silently dropped.
- Every artifact is content-addressed, atomic, and no-replace. If any preflight step fails, the requested gallery root remains absent.
- Render the comparison sheet directly from vector geometry at native cell resolution. Do not re-resize raster panels to make the sheet.
- Preserve the current default selector's two-width output and its existing ledger semantics byte-for-byte for current callers.

## Approved Orientation Contract

| Variant ID | Active Bunge ZXZ angles (degrees) | Search-state count by phase: Ice, Fo, Qtz, Zrn, Ttn |
| --- | --- | --- |
| `azimuthal-60` | `(77.0, 31.0, 43.0)` | `2, 6, 1, 2, 2` |
| `tilt-plus-20` | `(17.0, 51.0, 43.0)` | `2, 1, 1, 1, 27` |
| `oblique-high` | `(97.0, 71.0, 83.0)` | `1, 2, 2, 4, 5` |

The counts are retained as feasibility-scanning provenance, not an optimization target. The orientation recipe records the values explicitly and never generates them at render time.

## File Structure

| Path | Responsibility |
| --- | --- |
| `src/kikuchi_lab/art_products/tattoo_vector.py` | Represent crop-fragment infeasibility as an actionable clearance conflict. |
| `src/kikuchi_lab/art_products/clearance_selection.py` | Add the shared bounded selector and a standard-only gallery entry point without changing the legacy default result. |
| `recipes/art/five-phase-standard-orientation-gallery.yml` | Versioned five-phase, three-orientation gallery policy. |
| `src/kikuchi_lab/art_products/orientation_gallery_recipe.py` | Parse and validate the new recipe into immutable typed data. |
| `src/kikuchi_lab/art_products/orientation_gallery_bundle.py` | Validate and atomically publish generic gallery cell artifacts and the comparison ledger. |
| `src/kikuchi_lab/art_products/orientation_gallery_sheet.py` | Render a native 3-by-5 labeled comparison PNG directly from geometry. |
| `src/kikuchi_lab/workflows/direct_phase_preflight.py` | Shared direct catalog/parity gate for both art workflows. |
| `src/kikuchi_lab/workflows/phase_art_orientation_gallery.py` | Preflight all fifteen cells, then publish the immutable gallery root. |
| `src/kikuchi_lab/cli/main.py` | Expose the finite, zero-master gallery command. |
| `tests/` | First-failing tests for each seam and regression tests for the current family. |
| `docs/acceptance/five-phase-standard-orientation-gallery.md` | Retain exact command, output identities, checksum evidence, and review path. |

### Task 1: Make crop infeasibility branchable and add standard-only selection

**Files:**
- Modify: `src/kikuchi_lab/art_products/tattoo_vector.py`
- Modify: `src/kikuchi_lab/art_products/clearance_selection.py`
- Modify: `tests/unit/test_tattoo_vector.py`
- Modify: `tests/unit/test_clearance_selection.py`

- [ ] **Step 1: Write failing geometry and selection tests.**

  Add a test that forces a selected path to produce more than one clipped interior fragment and asserts a `TattooClearanceError` with `clearance_kind == "crop_fragment"` and a one-member tuple. Add selector tests that demonstrate: the new standard-only function branches that singleton exclusion; it records a `standard_clearance_search` ledger; it only builds scale `1.0`; and legacy `select_clearance_valid_tattoo_paths()` returns the same selected IDs, search identity, wide-scale geometry, and ledger shape as before.

- [ ] **Step 2: Run the targeted tests to confirm they fail.**

  Run: `uv run pytest tests/unit/test_tattoo_vector.py tests/unit/test_clearance_selection.py -q`

  Expected: failures identify the raw crop `ValueError`, missing `crop_fragment` literal/member shape, and missing standard-only selector.

- [ ] **Step 3: Extend the geometry conflict contract.**

  In `tattoo_vector.py`, extend `ClearanceKind` with `"crop_fragment"` and let `TattooClearanceError.member_ids` hold one or two member IDs. In `build_tattoo_geometry()`, replace the raw fragment-count `ValueError` with `TattooClearanceError` that names the selected member. Do not change successful clipping or valid geometry data.

- [ ] **Step 4: Refactor bounded search behind a shared internal helper.**

  In `clearance_selection.py`, factor the existing BFS into an internal helper accepting the requested width scale(s), ledger key, and algorithm identity. Keep the old public selector configured identically with `(1.15, 1.0)`, `wide_clearance_search`, and `bounded-bfs-wide-clearance-v1`. Add `select_standard_clearance_valid_tattoo_paths(catalog, recipe)` configured with `(1.0,)`, `standard_clearance_search`, and `bounded-bfs-standard-clearance-v1`. Update `_branch_member_ids()` so singleton crop conflicts exclude that one member while two-member clearance conflicts retain current branching behavior.

- [ ] **Step 5: Run focused regressions.**

  Run: `uv run pytest tests/unit/test_tattoo_vector.py tests/unit/test_clearance_selection.py tests/unit/test_phase_art_series.py -q`

  Expected: all pass; current standard/wide selection identity has not changed.

- [ ] **Step 6: Commit the completed slice.**

  ```bash
  git add src/kikuchi_lab/art_products/tattoo_vector.py src/kikuchi_lab/art_products/clearance_selection.py tests/unit/test_tattoo_vector.py tests/unit/test_clearance_selection.py
  git commit -m "feat: branch crop-infeasible art paths"
  ```

### Task 2: Add and validate the immutable orientation-gallery recipe

**Files:**
- Create: `recipes/art/five-phase-standard-orientation-gallery.yml`
- Create: `src/kikuchi_lab/art_products/orientation_gallery_recipe.py`
- Create: `tests/unit/test_orientation_gallery_recipe.py`
- Modify: `src/kikuchi_lab/art_products/__init__.py`

- [ ] **Step 1: Write failing recipe tests.**

  Test that the shipped recipe parses to exactly the ordered phase IDs from the base series and exactly the three ordered variants. Assert `Orientation.euler_bunge_deg`, `frame == "crystal_to_sample"`, non-identity/distinct orientations, only standard width, and rejection of duplicated slugs, non-five phase inventories, wrong frame, missing source recipe, or non-three variants.

- [ ] **Step 2: Run the new test to confirm it fails.**

  Run: `uv run pytest tests/unit/test_orientation_gallery_recipe.py -q`

  Expected: import/recipe-not-found failures.

- [ ] **Step 3: Create the explicit YAML policy.**

  Add `schema_version: 1`, a stable gallery `name`, `source_series_recipe: five-phase-hemisphere-series.yml`, standard-only treatment identity, and these exact variants:

  ```yaml
  variants:
    - slug: azimuthal-60
      orientation:
        euler_bunge_deg: [77.0, 31.0, 43.0]
        frame: crystal_to_sample
    - slug: tilt-plus-20
      orientation:
        euler_bunge_deg: [17.0, 51.0, 43.0]
        frame: crystal_to_sample
    - slug: oblique-high
      orientation:
        euler_bunge_deg: [97.0, 71.0, 83.0]
        frame: crystal_to_sample
  ```

  Use the base recipe for phase/direct-reflector policy rather than duplicating phase physics in the new file.

- [ ] **Step 4: Implement strict typed parsing.**

  Model a frozen `OrientationGalleryVariant` and `OrientationGalleryRecipe`; load the base `HemisphereSeriesRecipe` through its existing parser. Reject unknown/missing fields and validate every contract in Step 1 before returning typed values. Expose only the narrow public loader/types needed by the workflow.

- [ ] **Step 5: Run focused tests.**

  Run: `uv run pytest tests/unit/test_orientation_gallery_recipe.py tests/unit/test_hemisphere_recipe.py -q`

  Expected: all pass.

- [ ] **Step 6: Commit the completed slice.**

  ```bash
  git add recipes/art/five-phase-standard-orientation-gallery.yml src/kikuchi_lab/art_products/orientation_gallery_recipe.py src/kikuchi_lab/art_products/__init__.py tests/unit/test_orientation_gallery_recipe.py
  git commit -m "feat: define standard orientation gallery recipe"
  ```

### Task 3: Publish generic immutable cell bundles and a native 3-by-5 sheet

**Files:**
- Create: `src/kikuchi_lab/art_products/orientation_gallery_bundle.py`
- Create: `src/kikuchi_lab/art_products/orientation_gallery_sheet.py`
- Create: `tests/unit/test_orientation_gallery_bundle.py`
- Create: `tests/unit/test_orientation_gallery_sheet.py`
- Modify: `src/kikuchi_lab/art_products/__init__.py`

- [ ] **Step 1: Write failing bundle tests.**

  Build a minimal real direct-art fixture and assert one generic cell bundle contains the white-background PNG stencil, black-on-white SVG, `art-band-catalog`, composition recipe, selected-path ledger, path geometry, treatment/orientation snapshot, parity report snapshot, scientific claim, manifest, and checksums. Assert the manifest retains phase ID, variant ID, Bunge angles, `crystal_to_sample`, source catalog/parity identity, selection ID, geometry ID, and `simulation_count: 0`. Add tests for content-addressed idempotence, no-replace conflict, and rejection of an Ice-only frozen-reference substitution.

- [ ] **Step 2: Write failing sheet tests.**

  Construct fifteen in-memory geometry cells in the explicit row-major order below and assert: `4500 x 2700` output, binary RGB/RGBA white background, a circular boundary in every panel, labels outside the circle, no resize of imported raster content, and a ledger with all fifteen phase/variant/order records.

  ```text
  azimuthal-60: ice-ih, forsterite, quartz, zircon, titanite
  tilt-plus-20: ice-ih, forsterite, quartz, zircon, titanite
  oblique-high: ice-ih, forsterite, quartz, zircon, titanite
  ```

- [ ] **Step 3: Run the tests to confirm they fail.**

  Run: `uv run pytest tests/unit/test_orientation_gallery_bundle.py tests/unit/test_orientation_gallery_sheet.py -q`

  Expected: module/import failures.

- [ ] **Step 4: Implement a generic cell publication contract.**

  Add an immutable input type for an already-validated gallery cell. Render SVG and its direct white PNG stencil only from `TattooGeometry`; do not pass through a master raster or use the baseline `HemisphereBundle` frozen-Ice path. Snapshot every input evidence record, use content-derived child names, build in a sibling staging directory, validate checksums, then atomically rename. A repeated byte-identical request returns the existing bundle; a divergent request never overwrites it.

- [ ] **Step 5: Implement a direct native sheet renderer.**

  Add a fixed 3-row x 5-column renderer with 900-pixel cells (`4500 x 2700` total). Draw each panel directly from the same path vectors used in the corresponding SVG, include the complete circular boundary, place variant labels on the left/above and phase labels outside panels, and emit both PNG and a normalized comparison ledger. Keep panel layout explicit; do not modify the existing two-treatment `series_sheet.py` contract.

- [ ] **Step 6: Run focused tests and inspect one temporary sheet.**

  Run: `uv run pytest tests/unit/test_orientation_gallery_bundle.py tests/unit/test_orientation_gallery_sheet.py -q`

  Expected: all pass; a representative sheet opens at native dimensions with white background and all fifteen full hemispheres.

- [ ] **Step 7: Commit the completed slice.**

  ```bash
  git add src/kikuchi_lab/art_products/orientation_gallery_bundle.py src/kikuchi_lab/art_products/orientation_gallery_sheet.py src/kikuchi_lab/art_products/__init__.py tests/unit/test_orientation_gallery_bundle.py tests/unit/test_orientation_gallery_sheet.py
  git commit -m "feat: add orientation gallery art bundles"
  ```

### Task 4: Extract direct evidence preflight and build the zero-master gallery workflow

**Files:**
- Create: `src/kikuchi_lab/workflows/direct_phase_preflight.py`
- Create: `src/kikuchi_lab/workflows/phase_art_orientation_gallery.py`
- Modify: `src/kikuchi_lab/workflows/phase_art_series.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Create: `tests/integration/test_phase_art_orientation_gallery.py`
- Modify: `tests/integration/test_phase_art_series.py`

- [ ] **Step 1: Write failing integration tests.**

  Add tests proving the gallery workflow: loads only passed parity reports matching rebuilt direct evidence; produces exactly 15 cells in the prescribed order; records all three active Bunge orientations; uses standard-only selection; reports `simulation_count == 0`; and invokes no master simulation seam. Add a deliberate bad parity/geometry fixture and assert the requested output root does not exist after preflight fails. Also preserve current phase-art-series integration expectations unchanged.

- [ ] **Step 2: Run integration tests to confirm failure.**

  Run: `uv run pytest tests/integration/test_phase_art_orientation_gallery.py tests/integration/test_phase_art_series.py -q`

  Expected: gallery module/workflow failures; current family remains passing.

- [ ] **Step 3: Extract the shared direct-phase preflight seam.**

  Move narrow reusable functions such as `load_passed_parity_reports(parity_root)` and `build_parity_gated_direct_phase(recipe_file, series, phase_slug, reports)` into `direct_phase_preflight.py`. Update `phase_art_series.py` to import those helpers without changing its public API, output values, or parity error behavior. Keep simulation APIs out of this module.

- [ ] **Step 4: Implement all-preflight-before-write gallery orchestration.**

  Load the gallery recipe and parity reports; for each ordered orientation and phase, build direct phase evidence through the shared preflight, compose it with the explicit active orientation, run `select_standard_clearance_valid_tattoo_paths`, build geometry, and retain an in-memory validated cell record. Confirm exact inventory, unique cell IDs, all standard geometry, and zero simulation count. Only after all 15 cells are valid, atomically publish their bundles and the comparison sheet/ledger under a new gallery root. A single failure must publish nothing at that requested root.

- [ ] **Step 5: Run integration and regression tests.**

  Run: `uv run pytest tests/integration/test_phase_art_orientation_gallery.py tests/integration/test_phase_art_series.py tests/unit/test_clearance_selection.py -q`

  Expected: all pass; the existing series continues to retain its frozen Ice bundle and wide companion.

- [ ] **Step 6: Commit the completed slice.**

  ```bash
  git add src/kikuchi_lab/workflows/direct_phase_preflight.py src/kikuchi_lab/workflows/phase_art_orientation_gallery.py src/kikuchi_lab/workflows/phase_art_series.py src/kikuchi_lab/workflows/__init__.py tests/integration/test_phase_art_orientation_gallery.py tests/integration/test_phase_art_series.py
  git commit -m "feat: render phase orientation gallery"
  ```

### Task 5: Expose the finite gallery command

**Files:**
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`
- Modify: `tests/integration/test_phase_art_orientation_gallery.py`

- [ ] **Step 1: Write failing CLI tests.**

  Assert `kikuchi-lab render-phase-art-orientation-gallery --help` describes the gallery recipe, parity root, and output. Assert a fixture command prints exactly `phase-art-orientation-gallery finite-work phases=5 orientations=3 cells=15 simulation_count=0` before it calls the workflow, returns the gallery root/comparison identity, and reports preflight errors without leaving an output root.

- [ ] **Step 2: Run the targeted CLI test to confirm failure.**

  Run: `uv run pytest tests/unit/test_cli.py -q -k orientation_gallery`

  Expected: parser-command failure.

- [ ] **Step 3: Add the command without broadening existing commands.**

  Add `render-phase-art-orientation-gallery` to the existing parser with required `--recipe`, `--parity-root`, and `--output` arguments. Print the exact finite-work declaration before execution, call only the new gallery workflow, serialize the immutable publication result, and preserve exit/error conventions of neighboring art commands.

- [ ] **Step 4: Run focused CLI and workflow tests.**

  Run: `uv run pytest tests/unit/test_cli.py -q -k "orientation_gallery or phase_art" && uv run pytest tests/integration/test_phase_art_orientation_gallery.py -q`

  Expected: all pass.

- [ ] **Step 5: Commit the completed slice.**

  ```bash
  git add src/kikuchi_lab/cli/main.py tests/unit/test_cli.py tests/integration/test_phase_art_orientation_gallery.py
  git commit -m "feat: expose orientation gallery CLI"
  ```

### Task 6: Render retained evidence, verify it, and close the tracked task

**Files:**
- Create: `local/phase-general-direct-reflector-art/orientation-gallery/<content-addressed-gallery>/`
- Create: `docs/acceptance/five-phase-standard-orientation-gallery.md`
- Modify: `docs/work/KIKU-T036.md`

- [ ] **Step 1: Produce the real gallery with retained parity evidence.**

  Run:

  ```bash
  uv run kikuchi-lab render-phase-art-orientation-gallery \
    --recipe recipes/art/five-phase-standard-orientation-gallery.yml \
    --parity-root local/phase-general-direct-reflector-art/parity \
    --output local/phase-general-direct-reflector-art/orientation-gallery
  ```

  Expected: the finite-work line reports `phases=5 orientations=3 cells=15 simulation_count=0`; a newly content-addressed gallery root contains fifteen cell bundles and one `4500 x 2700` comparison sheet.

- [ ] **Step 2: Verify the published inventories and identities with a read-only probe.**

  Run a short `uv run python -c` or existing reader that loads the gallery ledger/manifests and asserts: exactly fifteen unique `(phase_slug, variant_slug)` pairs; the approved orientation table; one standard-width selection and one geometry per cell; complete boundary paths; all `simulation_count == 0`; checksum-valid artifacts; and direct catalog/parity IDs matching the passed reports. Do not regenerate or alter artifacts in this step.

- [ ] **Step 3: Inspect the visual product at native resolution.**

  Open the comparison sheet and at least one Ice, one forsterite, one quartz, one zircon, and one titanite child PNG. Confirm: full hemispherical boundary in all panels; black single-stroke hierarchy on white; orientation labels outside circles; no clipped/camera-only rotation appearance; and visibly distinct orientations per phase.

- [ ] **Step 4: Write concise acceptance evidence.**

  In `docs/acceptance/five-phase-standard-orientation-gallery.md`, record the exact command, recipe checksum, gallery root, comparison path/dimensions, each cell's phase/variant/selection/geometry IDs, parity source, renderer ID, zero-master statement, verification command outputs, and the five representative image paths reviewed. State that the result is a direct-reflector science-art hemisphere gallery, not a quantitative EBSD master pattern.

- [ ] **Step 5: Complete and validate the repo-native work item.**

  Add this plan link to `KIKU-T036`, update its evidence list with the acceptance document and retained gallery ledger, mark every acceptance criterion complete only after Step 2 and 3 succeed, then set task status to `completed`. Retain the design spec; do not change unrelated active tasks.

- [ ] **Step 6: Run the full verification gate.**

  Run:

  ```bash
  uv run pytest -q
  uv run ruff check src tests
  uv run python scripts/validate_work_items.py
  git diff --check
  ```

  Expected: full suite, Ruff, work tracker, and whitespace checks pass. If a failure is unrelated to this plan, report it with the exact failing file and do not edit or stage that unrelated change.

- [ ] **Step 7: Commit retained proof only.**

  ```bash
  git add docs/acceptance/five-phase-standard-orientation-gallery.md docs/work/KIKU-T036.md local/phase-general-direct-reflector-art/orientation-gallery
  git commit -m "docs: retain orientation gallery evidence"
  ```

## Plan Review Checklist

- [ ] The recipe names all three approved active Bunge orientations and no orientation is generated at runtime.
- [ ] Crop infeasibility, normal clearance, and endpoint clearance all enter one deterministic bounded selection process without changing the legacy two-width behavior.
- [ ] The workflow preflights all fifteen cells before it writes any gallery artifact and never depends on an EBSD master-pattern renderer.
- [ ] The baseline standard/wide family and frozen Ice reference remain protected by regression tests.
- [ ] The comparison sheet is 3-by-5, native vector-rendered, labeled outside the boundaries, and preserves complete circular hemispheres.
- [ ] Manifests/ledgers retain the provenance required to reproduce every visual output and distinguish it from a quantitative EBSD simulation.
