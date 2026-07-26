# Atlas Phase Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the current Atlas baseline, then promote grossular, almandine, and the exact COD 2108838 tremolite-family composition through the complete nine-product parity contract.

**Architecture:** First commit the already-verified calcite/enstatite files required by the tracked Atlas state, then create one isolated batch worktree with copy-on-write artifact clones. Implement and review one phase at a time through source verification, direct/simulator parity, kinematical and retained-depth products, animations, printable globes, Atlas publication, and durable acceptance; later-source triage may be read-only and parallel, but tracked writes remain sequential.

**Tech Stack:** Python 3.12, uv, PyCifRW, diffpy.structure, diffsims, kikuchipy, orix, NumPy, trimesh, ffmpeg/ffprobe, pytest, YAML, Git worktrees, APFS clonefile copies.

## Global Constraints

- Do not remove, rename, replace, or mutate an existing phase or product record to make inventory tests pass.
- A phase is done only after all nine product roles are locally available, hash/provenance bound, registered, accepted, and independently reviewed.
- Keep unrelated quartz, artifact-catalog, work-item, and retained-rotation changes out of every batch commit.
- The known unrelated full-suite failures are:
  - `tests/adapters/test_kikuchipy_kinematical.py::test_adapter_context_keeps_upstream_products_private_and_complete`
  - `tests/unit/test_product_status.py::test_product_catalog_has_unique_static_entries_and_tracked_inputs`
- Preserve exact original source bytes and source-specific copying notices.
- Publish no product before its media, preview, bundle, provenance, and recipe paths exist.
- Use 20.0 keV, 0.7 angstrom minimum d-spacing, `xtables`, and the approved Atlas detector/master/tone/style contract for all three phases.
- Start tied-cohort selection at normalized weight `0.10`. If it does not yield four nonempty tied cohorts, test `0.08`, `0.06`, `0.05`, then `0.04` in that order and select the highest passing threshold; change no other reflector calculation input.
- Bind content-derived recipe, run, product, catalog, build, array, and file identities from loader or manifest output. Never invent or precompute an identifier by hand.
- Original source SHA-256 values are:
  - Grossular COD 9000439: `8871e6b800ee64ea1ec4c1c04ea746ac463b6a367283357981a6539f6ecf94c8`.
  - Almandine COD 9006109: `ee62528f110e783b54d93b1d0fc8c43b5dae232c4d9d930ff14bbbff1768a58e`.
  - Tremolite COD 2108838: `91ebb6aad65f380714c3963d83ed7be297ed76d8509d3e18699c3e2d3f50b596`.
- Grossular is one 298.15 K Ca garnet endmember reference, not all grossular-bearing garnets or a pressure series.
- Almandine is one 293 K synthetic Fe garnet endmember reference, not all natural almandine solid solutions or a temperature series.
- Tremolite publication must use the exact measured formula and an exact-composition display name; it is not an ideal `Ca2Mg5Si8O22(OH)2` endmember or a generic amphibole reference.
- Direct-reflector images are crystallographically sourced science art, retained-depth rotations are presentation products, and mesh validation is not indexing, detector, orientation-accuracy, or physical-print validation.

---

### Task 1: Stabilize the calcite and enstatite baseline

**Files:**
- Add existing: `phases/calcite/COD-1547350.cif`
- Add existing: `phases/calcite/source.yml`
- Add existing: `phases/enstatite/COD-9001593.cif`
- Add existing: `phases/enstatite/source.yml`
- Add existing: `recipes/reflectors/calcite-art-bands.yml`
- Add existing: `recipes/reflectors/calcite-catalog.yml`
- Add existing: `recipes/reflectors/enstatite-art-bands.yml`
- Add existing: `recipes/reflectors/enstatite-catalog.yml`
- Add existing: `recipes/kinematical/calcite-001-atlas-parity-master.yml`
- Add existing: `recipes/kinematical/enstatite-001-atlas-parity-master.yml`
- Add existing: `recipes/presentation/calcite-near-depth-atlas-parity.yml`
- Add existing: `recipes/presentation/enstatite-near-depth-atlas-parity.yml`
- Add existing: `recipes/globes/calcite-reflector-ridges.yml`
- Add existing: `recipes/globes/enstatite-reflector-ridges.yml`
- Add existing: `recipes/relief/calcite-atlas-parity-kinematical-intensity.yml`
- Add existing: `recipes/relief/enstatite-atlas-parity-kinematical-intensity.yml`
- Add existing: `tests/adapters/test_calcite_source.py`
- Add existing: `tests/adapters/test_enstatite_source.py`
- Add existing: `docs/acceptance/calcite-atlas-parity.md`
- Add existing: `docs/acceptance/enstatite-atlas-parity.md`
- Add existing: `docs/work/KIKU-T082.md`
- Add existing: `docs/work/KIKU-T083.md`
- Add existing: `docs/superpowers/plans/2026-07-24-enstatite-atlas-parity.md`

**Interfaces:**
- Consumes: the already-tracked 12-phase Atlas registries and release metadata.
- Produces: a self-contained tracked baseline from which a new worktree can verify calcite and enstatite sources and recipes.

- [ ] **Step 1: Prove the files belong to the accepted Atlas state**

Run:

```bash
git status --short -- \
  phases/calcite phases/enstatite \
  recipes/reflectors/calcite-art-bands.yml \
  recipes/reflectors/calcite-catalog.yml \
  recipes/reflectors/enstatite-art-bands.yml \
  recipes/reflectors/enstatite-catalog.yml \
  recipes/kinematical/calcite-001-atlas-parity-master.yml \
  recipes/kinematical/enstatite-001-atlas-parity-master.yml \
  recipes/presentation/calcite-near-depth-atlas-parity.yml \
  recipes/presentation/enstatite-near-depth-atlas-parity.yml \
  recipes/globes/calcite-reflector-ridges.yml \
  recipes/globes/enstatite-reflector-ridges.yml \
  recipes/relief/calcite-atlas-parity-kinematical-intensity.yml \
  recipes/relief/enstatite-atlas-parity-kinematical-intensity.yml \
  tests/adapters/test_calcite_source.py \
  tests/adapters/test_enstatite_source.py \
  docs/acceptance/calcite-atlas-parity.md \
  docs/acceptance/enstatite-atlas-parity.md \
  docs/work/KIKU-T082.md docs/work/KIKU-T083.md \
  docs/superpowers/plans/2026-07-24-enstatite-atlas-parity.md
```

Expected: only the listed files appear. Confirm that the tracked phase/product
registries already name calcite and enstatite and that both acceptance records
point to the same source and recipe paths.

- [ ] **Step 2: Verify the focused prerequisite gate**

Run:

```bash
uv run pytest -q \
  tests/adapters/test_calcite_source.py \
  tests/adapters/test_enstatite_source.py \
  tests/unit/test_atlas_extension_parity_recipes.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_release_metadata.py
uv run python scripts/validate_work_items.py
uv run python scripts/build_atlas.py --output local/atlas-expansion/site
git diff --check
```

Expected: all focused tests pass, work items validate, and the Atlas reports
12 phases and 122 available products.

- [ ] **Step 3: Review the exact staged scope**

Stage only the Task 1 files, then run:

```bash
git diff --cached --name-only
git diff --cached --check
```

Expected: the staged list is exactly the 23 paths named above. Unrelated
quartz, artifact-catalog, work-item, and retained-rotation files remain
unstaged.

- [ ] **Step 4: Commit the stabilized baseline**

```bash
git commit -m "chore: stabilize calcite and enstatite parity baseline"
```

Require a fresh reviewer to compare the commit with the tracked registries,
acceptance records, and focused test evidence before Task 2.

---

### Task 2: Create the isolated batch worktree and artifact cache

**Files:**
- Create workspace: `.worktrees/atlas-phase-batch`
- Create gitignored artifacts: `.worktrees/atlas-phase-batch/local/atlas-expansion/{calcite,enstatite,pyrope}`

**Interfaces:**
- Consumes: stabilized `master` and immutable published artifact roots.
- Produces: branch `codex/atlas-phase-batch` with an isolated, writable artifact cache.

- [ ] **Step 1: Re-run the worktree safety checks**

Use `superpowers:using-git-worktrees`. Confirm:

```bash
git_dir=$(cd "$(git rev-parse --git-dir)" && pwd -P)
git_common=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
test "$git_dir" = "$git_common"
git check-ignore -q .worktrees
```

Expected: the main checkout is a normal repository and `.worktrees/` is
ignored.

- [ ] **Step 2: Create the branch and worktree**

```bash
git worktree add .worktrees/atlas-phase-batch -b codex/atlas-phase-batch
```

Expected: the worktree is created from stabilized `master`.

- [ ] **Step 3: Seed isolated artifact roots**

From the main checkout:

```bash
mkdir -p .worktrees/atlas-phase-batch/local/atlas-expansion
cp -cR local/atlas-expansion/calcite .worktrees/atlas-phase-batch/local/atlas-expansion/
cp -cR local/atlas-expansion/enstatite .worktrees/atlas-phase-batch/local/atlas-expansion/
cp -cR local/atlas-expansion/pyrope .worktrees/atlas-phase-batch/local/atlas-expansion/
```

If `cp -cR` reports that cloning is unsupported, remove only the incomplete
destination phase directory and repeat that phase with `cp -R`. Do not use
symlinks.

- [ ] **Step 4: Verify the cloned artifact inventories**

For every manifest under the three source phase roots, verify each declared
file exists and matches its recorded byte count and SHA-256. Require both
source and destination trees to contain the same relative file set and hashes.

Expected: no missing or mismatched file. Record the verified manifest and file
counts in `.superpowers/sdd/atlas-phase-batch-progress.md`.

- [ ] **Step 5: Set up and verify the worktree**

In `.worktrees/atlas-phase-batch`:

```bash
uv sync --frozen
uv run pytest -q \
  tests/adapters/test_calcite_source.py \
  tests/adapters/test_enstatite_source.py \
  tests/adapters/test_pyrope_source.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_release_metadata.py \
  tests/unit/test_atlas_extension_parity_recipes.py
uv run python scripts/build_atlas.py --output local/atlas-expansion/site
```

Expected: the focused gate passes and the Atlas reports 12/122. Run the full
suite once with an attached session. If the two declared baseline failures
remain, record exact totals and continue; stop for any new failure.

---

### Task 3: Promote the grossular source test-first

**Files:**
- Create: `tests/adapters/test_grossular_source.py`
- Create: `phases/grossular/COD-9000439-original.cif`
- Create: `phases/grossular/COD-9000439-isotropic-u.cif`
- Create: `phases/grossular/source.yml`

**Interfaces:**
- Consumes: `load_structure_record()`, `verify_structure()`, and `_phase_from_record()`.
- Produces: verified identifier `COD-9000439-isotropic-U` with a 160-atom expanded conventional cell.

- [ ] **Step 1: Write the failing source contract**

```python
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kikuchi_lab.kinematical.kikuchipy_adapter import _phase_from_record
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/grossular/source.yml"
ORIGINAL = ROOT / "phases/grossular/COD-9000439-original.cif"
ORIGINAL_SHA256 = "8871e6b800ee64ea1ec4c1c04ea746ac463b6a367283357981a6539f6ecf94c8"


def test_grossular_derivative_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-9000439-isotropic-U"
    assert record.formula == "Ca3Al2Si3O12"
    assert record.space_group_number == 230
    assert record.setting == "I a -3 d"
    assert record.simulation_setting["temperature_k"] == 298.15
    assert record.simulation_setting["target_site_multiplicities"] == [24, 16, 24, 96]
    assert record.simulation_setting["derived_from_sha256"] == ORIGINAL_SHA256
    assert record.simulation_setting["u_iso_derivation"] == (
        "U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal cubic axes"
    )
    assert verified.site_u_iso_angstrom_sq == pytest.approx(
        (0.00495, 0.00507, 0.0038666666666666667, 0.00469)
    )
    assert verified.occupancy_source == "implicit CIF default 1.0"
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == ORIGINAL_SHA256
    assert len(_phase_from_record(record).structure) == 160
```

- [ ] **Step 2: Confirm RED**

```bash
uv run pytest -q tests/adapters/test_grossular_source.py
```

Expected: `FileNotFoundError` for `phases/grossular/source.yml`.

- [ ] **Step 3: Preserve the original and create the derivative**

Retrieve `https://www.crystallography.net/cod/9000439.cif` and reject it unless
its SHA-256 equals the pinned value. Preserve its attribution-use notice and
Meagher (1975) citation.

The derivative must retain the original cell, symmetry operations, coordinates,
implicit full occupancies, citation, and related-entry loop; remove the
anisotropic loop and use this atom loop:

```cif
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_U_iso_or_equiv
Ca 0.12500 0.00000 0.25000 0.00495
Al 0.00000 0.00000 0.00000 0.00507
Si 0.00000 0.25000 0.37500 0.0038666666666666667
O  0.03800 0.04470 0.65120 0.00469
```

Bind the derivative to the original digest and calculate its own SHA-256 after
writing the deterministic bytes.

- [ ] **Step 4: Add the exact source record**

Use:

```yaml
schema_version: 1
identifier: COD-9000439-isotropic-U
cif: COD-9000439-isotropic-u.cif
retrieved: 2026-07-25
uri: https://www.crystallography.net/cod/9000439.cif
page_uri: https://www.crystallography.net/cod/9000439.html
license: COD attribution-use notice
phase:
  name: grossular
  formula: Ca3Al2Si3O12
  space_group_number: 230
  setting: "I a -3 d"
  lattice_angstrom: [11.846, 11.846, 11.846, 90.0, 90.0, 90.0]
sites:
  - {label: Ca, element: Ca, fract: [0.125, 0.0, 0.25], occupancy: 1.0, u_iso_angstrom_sq: 0.00495}
  - {label: Al, element: Al, fract: [0.0, 0.0, 0.0], occupancy: 1.0, u_iso_angstrom_sq: 0.00507}
  - {label: Si, element: Si, fract: [0.0, 0.25, 0.375], occupancy: 1.0, u_iso_angstrom_sq: 0.0038666666666666667}
  - {label: O, element: O, fract: [0.038, 0.0447, 0.6512], occupancy: 1.0, u_iso_angstrom_sq: 0.00469}
simulation_setting:
  temperature_k: 298.15
  source_setting: "I a -3 d"
  target_setting: "I a -3 d"
  target_lattice_from_source: [a, b, c]
  target_fractional_from_source: [x, y, z]
  target_site_multiplicities: [24, 16, 24, 96]
  derived_from_identifier: COD-9000439
  derived_from_sha256: 8871e6b800ee64ea1ec4c1c04ea746ac463b6a367283357981a6539f6ecf94c8
  u_iso_derivation: U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal cubic axes
```

Add the derivative SHA, source-specific copying policy, full Meagher citation,
the standard `B_iso = 8 * pi^2 * U_iso` policy with `missing: reject`, the
required ebsdsim fallback disclosure, unchanged-field ledger, and endmember
scope note.

- [ ] **Step 5: Confirm GREEN and commit**

```bash
uv run pytest -q tests/adapters/test_grossular_source.py
git diff --check
git add phases/grossular tests/adapters/test_grossular_source.py
git commit -m "feat: add verified grossular source"
```

Require a source reviewer to verify both CIF hashes, trace arithmetic,
attribution, setting, multiplicities, and scope.

---

### Task 4: Add grossular parity recipes test-first

**Files:**
- Modify: `tests/unit/test_atlas_extension_parity_recipes.py`
- Create: `recipes/reflectors/grossular-art-bands.yml`
- Create: `recipes/reflectors/grossular-catalog.yml`
- Create: `recipes/kinematical/grossular-001-atlas-parity-master.yml`
- Create: `recipes/presentation/grossular-near-depth-atlas-parity.yml`

**Interfaces:**
- Consumes: `phases/grossular/source.yml`.
- Produces: loader-accepted direct, catalog, kinematical, and near-depth recipes.

- [ ] **Step 1: Add the failing recipe tuple**

Add:

```python
(
    ROOT / "recipes/kinematical/grossular-001-atlas-parity-master.yml",
    ROOT / "recipes/presentation/grossular-near-depth-atlas-parity.yml",
),
```

Run the parameterized recipe test and require failure because the files do not
exist.

- [ ] **Step 2: Add the two reflector recipes**

```yaml
# recipes/reflectors/grossular-art-bands.yml
schema_version: 1
name: grossular-direct-art-reflectors
source_record: ../../phases/grossular/source.yml
energy_kev: 20.0
reflections: {min_dspacing_angstrom: 0.7, scattering_params: xtables, candidate_relative_factor: 0.03}
art_weight: {exponent: 2.0, eligibility_min_weight: 0.08}
```

```yaml
# recipes/reflectors/grossular-catalog.yml
schema_version: 1
source_record: phases/grossular/source.yml
energy_kev: 20.0
min_dspacing_angstrom: 0.7
scattering_params: xtables
source_master_relative_factor: 0.03
selection_relative_factor: 0.18
weight_exponent: 2.0
eligibility_min_weight: 0.10
tie_policy: keep_equal_weights_together
cohort_count: 4
```

- [ ] **Step 3: Add the kinematical recipe**

Use the complete approved contract:

```yaml
schema_version: 1
name: grossular-001-atlas-parity-master
source_record: ../../phases/grossular/source.yml
energy_kev: 20.0
orientation: {euler_bunge_deg: [0.0, 0.0, 0.0], frame: crystal_to_sample, zone_axis_uvw: [0, 0, 1]}
detector: {shape: [1536, 2048], pcx: 0.50, pcy: 0.72, pcz: 0.60, pc_convention: tsl, sample_tilt_deg: 70.0, detector_tilt_deg: 0.0, detector_azimuth_deg: 0.0, detector_twist_deg: 0.0, pixel_size_um: 5.859375, binning: 1, supersampling: 1}
reflections: {min_dspacing_angstrom: 0.7, scattering_params: xtables, master_relative_factor: 0.03}
master: {half_size: 512, hemisphere: both, scaling: square}
tone: {percentiles: [0.5, 99.85], asinh_scale: 7.0}
figure_size_px: 2400
promoted_style: quiet
styles:
  - {name: balanced, overlay_relative_factor: 0.14, line_alpha: 0.54, line_width_pt: 0.36}
  - {name: quiet, overlay_relative_factor: 0.22, line_alpha: 0.62, line_width_pt: 0.42}
```

- [ ] **Step 4: Add the near-depth recipe and confirm GREEN**

Load the kinematical recipe, capture its emitted `recipe_id`, and bind it:

```yaml
schema_version: 1
name: grossular-near-depth-atlas-parity
source_kinematical_recipe: ../kinematical/grossular-001-atlas-parity-master.yml
expected_kinematical_recipe_id: recipe-6f91d62293667b08
overlap: {relative_factor: 0.22, weight_exponent: 2.0, normalization_percentile: 99.5}
optical_depth: {gain: 0.38, luminance_ceiling: 0.985}
center: {enabled: false}
boundary: {relative_factor: 0.50, width_pt: 0.38, alpha: 0.50, casing_width_pt: 0.98, casing_alpha: 0.36}
figure_size_px: 2400
background_color: "#101519"
```

The exact expected ID is `recipe-6f91d62293667b08`, independently reproduced
by loading the approved contract with name
`grossular-001-atlas-parity-master`. Assert the loader emits that ID before
saving the near-depth recipe.

Run the recipe tests, commit the five files, and require reviewer approval.

---

### Task 5: Build grossular scientific intermediates

**Files:**
- Create gitignored artifacts under: `local/atlas-expansion/grossular/`

**Interfaces:**
- Consumes: grossular source and Task 4 recipes.
- Produces: direct catalog, parity report, master, near-depth field, four templates, and four-cohort catalog.

- [ ] **Step 1: Build and validate the direct catalog and parity report**

```bash
uv run kikuchi-lab build-direct-art-catalog \
  --recipe recipes/reflectors/grossular-art-bands.yml \
  --output local/atlas-expansion/grossular/direct-catalog
uv run kikuchi-lab validate-reflector-parity \
  --recipe recipes/reflectors/grossular-art-bands.yml \
  --output local/atlas-expansion/grossular/parity \
  --timeout-seconds 90
```

Require parity `passed: true`, retry count zero, exact HKL/provenance match, and
zero d-spacing, normal, strength, Bragg-angle, and weight errors.

- [ ] **Step 2: Build the master and retained-depth field**

```bash
uv run kikuchi-lab render-kinematical \
  --recipe recipes/kinematical/grossular-001-atlas-parity-master.yml \
  --output local/atlas-expansion/grossular/kinematical
uv run kikuchi-lab render-kinematical-depth \
  --recipe recipes/presentation/grossular-near-depth-atlas-parity.yml \
  --output local/atlas-expansion/grossular/near-depth
```

Require one run directory for each command and exact recipe linkage.

- [ ] **Step 3: Build four templates and the tied-cohort catalog**

```bash
direct_runs=(local/atlas-expansion/grossular/direct-catalog/direct-art-catalog-run-*)
(( ${#direct_runs} == 1 ))
uv run python scripts/render_phase_art_templates.py \
  --phase grossular \
  --catalog "${direct_runs[1]}/art-band-catalog.json" \
  --output local/atlas-expansion/grossular/templates
uv run kikuchi-lab reflectors build \
  --recipe recipes/reflectors/grossular-catalog.yml \
  --output local/atlas-expansion/grossular/reflector-catalog
```

Require exactly four standard-treatment template bundles and four nonempty
tied cohorts. Apply the global threshold ladder only if `0.10` fails.

- [ ] **Step 4: Audit and review the immutable artifacts**

Rehash every manifest-declared file, verify the canonical master array/file
hashes, source lineage, template orientations, and cohort ledger. Record every
emitted ID and count in `.superpowers/sdd/grossular-task-5-report.md`. This task
has no tracked commit; require an artifact reviewer before Task 6.

---

### Task 6: Build grossular rotations and globes test-first

**Files:**
- Modify: `tests/unit/test_direct_reflector_rotation.py`
- Modify: `tests/unit/test_reflector_globe_recipe.py`
- Modify: `tests/unit/relief/test_relief_recipes.py`
- Modify: `scripts/render_direct_reflector_rotation.py`
- Create: `recipes/globes/grossular-reflector-ridges.yml`
- Create: `recipes/relief/grossular-atlas-parity-kinematical-intensity.yml`

**Interfaces:**
- Consumes: exact Task 5 bundles and hashes.
- Produces: two MP4/GIF exports and two validated STL products.

- [ ] **Step 1: Add a failing immutable direct-source test**

Add a test that loads `PHASE_SOURCES["grossular"]`, asserts the literal
repository-relative path equals the one standard bundle emitted by Task 5, and
checks manifest phase `grossular` and treatment `standard`.

Run the test and require `KeyError: 'grossular'`, then add the exact literal
mapping and require GREEN.

- [ ] **Step 2: Add failing exact globe-recipe contracts, then the recipes**

Add grossular-specific loader tests that assert every source identity,
geometry, selection, tier, filter, mapping, export, and FDM field. Require
missing-file RED before adding the recipes.

The ridge recipe uses source identifier `COD-9000439-isotropic-U`, the selected
catalog threshold, 20 keV, four tied cohorts, 80 mm diameter, 3 mm outward
relief, subdivision 7, `filament_fdm`, and tiers:

```yaml
tiers:
  1: {height_mm: 1.2, width_multiplier: 1.4, minimum_width_mm: 0.8, edge_fillet_fraction: 0.25}
  2: {height_mm: 1.8, width_multiplier: 1.8, minimum_width_mm: 1.0, edge_fillet_fraction: 0.25}
  3: {height_mm: 2.4, width_multiplier: 2.2, minimum_width_mm: 1.2, edge_fillet_fraction: 0.25}
  4: {height_mm: 3.0, width_multiplier: 2.6, minimum_width_mm: 1.4, edge_fillet_fraction: 0.25}
```

The relief recipe binds the emitted master product ID and its exact array/file
hashes, 80 mm diameter, 1.2 mm maximum relief, subdivision 7, 1/99
percentiles, gamma 1, bright-outward mapping, 0.8 mm spherical-Gaussian FWHM,
3 sigma cutoff, STL export, and filament-FDM context.

- [ ] **Step 3: Render both rotations**

```bash
uv run python scripts/render_direct_reflector_rotation.py \
  --phase grossular --axis x \
  --output local/atlas-expansion/grossular/direct-rotation \
  --workers 4
kinematical_runs=(local/atlas-expansion/grossular/kinematical/kinematical-run-*)
near_depth_runs=(local/atlas-expansion/grossular/near-depth/near-depth-run-*)
(( ${#kinematical_runs} == 1 && ${#near_depth_runs} == 1 ))
uv run python scripts/render_retained_near_depth_rotation.py \
  --phase-slug grossular --phase-label Grossular \
  --kinematical-run "${kinematical_runs[1]}" \
  --near-depth-run "${near_depth_runs[1]}" \
  --output local/atlas-expansion/grossular/depth-rotation \
  --workers 4
```

Require H.264 High, 1024 square, yuv420p, 144 frames, 12 fps, and 12 seconds.

- [ ] **Step 4: Build and validate both globes**

```bash
reflector_catalog_runs=(local/atlas-expansion/grossular/reflector-catalog/reflector-catalog-build-*)
kinematical_runs=(local/atlas-expansion/grossular/kinematical/kinematical-run-*)
(( ${#reflector_catalog_runs} == 1 && ${#kinematical_runs} == 1 ))
uv run kikuchi-lab reflector-globe build \
  --catalog "${reflector_catalog_runs[1]}/reflector-catalog.json" \
  --recipe recipes/globes/grossular-reflector-ridges.yml \
  --output local/atlas-expansion/grossular/reflector-globe
uv run kikuchi-lab relief globe build \
  --master-pattern "${kinematical_runs[1]}/products/canonical-kinematical-master.npz" \
  --recipe recipes/relief/grossular-atlas-parity-kinematical-intensity.yml \
  --output local/atlas-expansion/grossular/relief
```

Resolve each exact run with a one-directory cardinality guard. Require
`passed`, `watertight`, and `winding_consistent`; preserve all FDM warnings.

- [ ] **Step 5: Verify, commit, and review**

Run the direct/rotation/globe recipe tests, independently rehash both movies
and STLs, run ffprobe and both mesh validators, then commit only the six
tracked files. Require reviewer approval.

---

### Task 7: Publish grossular in the Atlas test-first

**Files:**
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Modify: `docs/atlas/PHASE_REGISTRY.yml`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_ATTRIBUTION.md`

**Interfaces:**
- Consumes: complete existing grossular paths.
- Produces: 13 phases, 131 products, 13 structural sources, and 9 CC0 records.

- [ ] **Step 1: Update exact expected sets/counts and confirm RED**

Add `grossular` to the exact phase set and tracked-source loop, assert family
`garnet`, add `grossular-direct-standard` to the hero set, and change expected
phase/product/source counts from 12/122/12 to 13/131/13 while retaining CC0
count 9. Add an exact set assertion for the nine grossular product IDs.

Run Atlas/release tests and require RED because registries do not contain the
phase.

- [ ] **Step 2: Register the phase and exactly nine products**

Use display name `Grossular (298.15 K Ca endmember)`, formula
`Ca3Al2Si3O12`, cubic system, family `garnet`, and the source/scope from Task
3. Register:

```text
grossular-direct-standard
grossular-direct-azimuthal-60
grossular-direct-tilt-plus-20
grossular-direct-oblique-high
grossular-x-axis-rotation
grossular-reflector-ridge-globe
grossular-atlas-kinematical-master
grossular-atlas-retained-depth-x-axis
grossular-atlas-kinematical-intensity-relief
```

Use only actual existing Task 5/6 media, preview, bundle, provenance, and
recipe paths.

- [ ] **Step 3: Regenerate metadata, confirm GREEN, commit, and review**

```bash
uv run python scripts/build_release_metadata.py
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_release_metadata.py
uv run python scripts/build_atlas.py --output local/atlas-expansion/site
git diff --check
```

Require 13/131 and 13 sources/9 CC0. Commit the six tracked files and require
reviewer approval.

---

### Task 8: Accept grossular and close its work item

**Files:**
- Create: `docs/acceptance/grossular-atlas-parity.md`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`
- Modify: `docs/work/KIKU-F031.md`
- Modify: `docs/work/KIKU-T081.md`
- Create: `docs/work/KIKU-T085.md`

**Interfaces:**
- Consumes: complete grossular evidence.
- Produces: durable acceptance and one done child task while the umbrella remains active.

- [ ] **Step 1: Reverify all manifest, movie, and mesh evidence**

Read every manifest under `local/atlas-expansion/grossular`; verify every
declared path, byte count where recorded, and SHA-256. Recheck both movies with
ffprobe and both STLs with the mesh validators.

- [ ] **Step 2: Write exact acceptance and tracking records**

Record source/derivative hashes, trace derivation, citation, all emitted IDs
and counts, parity, animation profiles, mesh results, FDM advisories, 13/131,
13/9 source audit counts, and nonclaims. Add `KIKU-T085` symmetrically to
`KIKU-F031`, add source evidence to `KIKU-T081`, move grossular to existing
coverage, and leave both umbrella items active.

- [ ] **Step 3: Run the completion gate**

Run source, recipe, rotation, globe, Atlas, release, and work-item tests; build
the Atlas; run diff checks; then run the full suite once with an attached
session. Report the two known baseline failures separately and stop for any new
failure.

- [ ] **Step 4: Commit and broad-review the complete grossular slice**

Commit only the five documentation files. Create a review package from the
grossular starting commit to HEAD and require a fresh broad reviewer to approve
source science, all nine paths, artifact lineage, preservation of prior
records, and acceptance claims.

---

### Task 9: Promote the stronger almandine source test-first

**Files:**
- Create: `tests/adapters/test_almandine_source.py`
- Create: `phases/almandine/COD-9006109.cif`
- Create: `phases/almandine/source.yml`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`

**Interfaces:**
- Consumes: grossular-complete 13/131 Atlas.
- Produces: verified `COD-9006109` almandine with 160 expanded atoms and a documented replacement of zero-Uiso COD 1531283.

- [ ] **Step 1: Record the source decision**

Change the almandine candidate from COD 1531283 to COD 9006109. State that COD
1531283 reports all site Uiso values as `0.0`, whereas the 293 K synthetic
single-crystal record 9006109 reports nonzero refined Uiso values and is the
selected simulation reference.

- [ ] **Step 2: Write and run the failing source test**

The test must assert:

```python
assert record.identifier == "COD-9006109"
assert record.formula == "Fe3Al2Si3O12"
assert record.space_group_number == 230
assert record.setting == "I a -3 d"
assert record.simulation_setting["temperature_k"] == 293.0
assert record.simulation_setting["target_site_multiplicities"] == [24, 16, 24, 96]
assert verified.site_u_iso_angstrom_sq == pytest.approx(
    (0.00550, 0.00224, 0.00194, 0.00388)
)
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == (
    "ee62528f110e783b54d93b1d0fc8c43b5dae232c4d9d930ff14bbbff1768a58e"
)
assert len(_phase_from_record(record).structure) == 160
```

Require RED because `phases/almandine/source.yml` is absent.

- [ ] **Step 3: Preserve the original and add its source record**

Retrieve COD 9006109, require the pinned SHA, and preserve its attribution-use
notice and Geiger et al. (1992) citation. Use:

```yaml
phase:
  name: almandine
  formula: Fe3Al2Si3O12
  space_group_number: 230
  setting: "I a -3 d"
  lattice_angstrom: [11.525, 11.525, 11.525, 90.0, 90.0, 90.0]
sites:
  - {label: Fe, element: Fe, fract: [0.0, 0.25, 0.125], occupancy: 1.0, u_iso_angstrom_sq: 0.00550}
  - {label: Al, element: Al, fract: [0.0, 0.0, 0.0], occupancy: 1.0, u_iso_angstrom_sq: 0.00224}
  - {label: Si, element: Si, fract: [0.375, 0.0, 0.25], occupancy: 1.0, u_iso_angstrom_sq: 0.00194}
  - {label: O, element: O, fract: [0.034, 0.04905, 0.65283], occupancy: 1.0, u_iso_angstrom_sq: 0.00388}
simulation_setting:
  temperature_k: 293.0
  source_setting: "I a -3 d"
  target_setting: "I a -3 d"
  target_lattice_from_source: [a, b, c]
  target_fractional_from_source: [x, y, z]
  target_site_multiplicities: [24, 16, 24, 96]
```

Add the standard required thermal-factor policy and a scope note limiting the
reference to the 293 K synthetic endmember sample.

- [ ] **Step 4: Confirm GREEN, commit, and review**

Run the focused source test, commit the four files, and require a reviewer to
verify the source replacement rationale, checksum, nonzero Uiso values,
citation, setting, and multiplicities.

---

### Task 10: Add almandine parity recipes test-first

**Files:**
- Modify: `tests/unit/test_atlas_extension_parity_recipes.py`
- Create: `recipes/reflectors/almandine-art-bands.yml`
- Create: `recipes/reflectors/almandine-catalog.yml`
- Create: `recipes/kinematical/almandine-001-atlas-parity-master.yml`
- Create: `recipes/presentation/almandine-near-depth-atlas-parity.yml`

**Interfaces:**
- Consumes: verified COD 9006109.
- Produces: loader-accepted direct, catalog, kinematical, and near-depth recipes.

- [ ] **Step 1: Add the failing recipe tuple**

Add the exact almandine kinematical and near-depth paths to the parameterized
parity test. Run it and require missing-file RED.

- [ ] **Step 2: Add direct-art and catalog recipes**

Use:

```yaml
schema_version: 1
name: almandine-direct-art-reflectors
source_record: ../../phases/almandine/source.yml
energy_kev: 20.0
reflections: {min_dspacing_angstrom: 0.7, scattering_params: xtables, candidate_relative_factor: 0.03}
art_weight: {exponent: 2.0, eligibility_min_weight: 0.08}
```

The catalog recipe uses repository-root source
`phases/almandine/source.yml`, 20.0 keV, 0.7 angstrom, `xtables`, source
factor 0.03, selection factor 0.18, exponent 2.0, threshold 0.10,
`keep_equal_weights_together`, and four cohorts.

- [ ] **Step 3: Add the complete kinematical and near-depth recipes**

The kinematical recipe uses name `almandine-001-atlas-parity-master`,
identity orientation, detector shape 1536x2048, PC 0.50/0.72/0.60 in TSL,
sample tilt 70 degrees, zero detector tilt/azimuth/twist, pixel size
5.859375 micrometres, binning/supersampling 1, half-size 512, both
hemispheres, square scaling, tone 0.5/99.85 with asinh 7, figure 2400,
promoted quiet style, balanced 0.14/0.54/0.36 and quiet 0.22/0.62/0.42.

The near-depth recipe binds exact ID `recipe-3a8eb68255ee7b36` and uses
overlap 0.22/2.0/99.5, optical gain 0.38, ceiling 0.985, center disabled,
boundary 0.50/0.38/0.50 with casing 0.98/0.36, figure 2400, and background
`#101519`. Independently load the kinematical recipe and assert that ID.

- [ ] **Step 4: Confirm GREEN, commit, and review**

Run the recipe tests, commit the five tracked files, and require an independent
recipe-contract review.

---

### Task 11: Build almandine scientific intermediates

**Files:**
- Create gitignored artifacts: `local/atlas-expansion/almandine/`

**Interfaces:**
- Consumes: Task 10 recipes.
- Produces: parity, master, retained depth, four templates, and tied cohorts.

- [ ] **Step 1: Build direct catalog and parity**

```bash
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/almandine-art-bands.yml --output local/atlas-expansion/almandine/direct-catalog
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/almandine-art-bands.yml --output local/atlas-expansion/almandine/parity --timeout-seconds 90
```

Require exact parity, zero retries, and zero numeric errors.

- [ ] **Step 2: Build master and retained depth**

```bash
uv run kikuchi-lab render-kinematical --recipe recipes/kinematical/almandine-001-atlas-parity-master.yml --output local/atlas-expansion/almandine/kinematical
uv run kikuchi-lab render-kinematical-depth --recipe recipes/presentation/almandine-near-depth-atlas-parity.yml --output local/atlas-expansion/almandine/near-depth
```

- [ ] **Step 3: Build templates and tied cohorts**

Resolve exactly one direct catalog run, render templates with `--phase
almandine`, then build the reflector catalog from
`recipes/reflectors/almandine-catalog.yml`. Require four standard templates
and four nonempty cohorts; apply the global threshold ladder only if needed.

- [ ] **Step 4: Audit and artifact-review**

Rehash all manifest-ledger files, verify source and recipe lineage, canonical
master identities, template orientations, parity, and cohorts. Record emitted
IDs/counts in `.superpowers/sdd/almandine-task-11-report.md` and require an
artifact reviewer.

---

### Task 12: Build almandine rotations and globes test-first

**Files:**
- Modify: `tests/unit/test_direct_reflector_rotation.py`
- Modify: `tests/unit/test_reflector_globe_recipe.py`
- Modify: `tests/unit/relief/test_relief_recipes.py`
- Modify: `scripts/render_direct_reflector_rotation.py`
- Create: `recipes/globes/almandine-reflector-ridges.yml`
- Create: `recipes/relief/almandine-atlas-parity-kinematical-intensity.yml`

**Interfaces:**
- Consumes: Task 11 exact bundles and hashes.
- Produces: two verified animations and two validated globes.

- [ ] **Step 1: Add RED mapping test and exact mapping**

Assert the literal `PHASE_SOURCES["almandine"]` path equals Task 11's single
standard bundle and its manifest reports phase `almandine`, treatment
`standard`. Require `KeyError` RED before adding the mapping and GREEN after.

- [ ] **Step 2: Add failing exact globe-recipe contracts, then the recipes**

Add almandine-specific loader tests covering every ridge and relief field;
require missing-file RED. The ridge recipe uses identifier `COD-9006109`,
20 keV, the selected threshold,
four tied cohorts, 80 mm diameter, 3 mm outward relief, subdivision 7, and:

```yaml
tiers:
  1: {height_mm: 1.2, width_multiplier: 1.4, minimum_width_mm: 0.8, edge_fillet_fraction: 0.25}
  2: {height_mm: 1.8, width_multiplier: 1.8, minimum_width_mm: 1.0, edge_fillet_fraction: 0.25}
  3: {height_mm: 2.4, width_multiplier: 2.2, minimum_width_mm: 1.2, edge_fillet_fraction: 0.25}
  4: {height_mm: 3.0, width_multiplier: 2.6, minimum_width_mm: 1.4, edge_fillet_fraction: 0.25}
```

The relief recipe binds the actual canonical product/array/file hashes and
uses 80 mm, 1.2 mm, subdivision 7, percentiles 1/99, gamma 1,
bright-outward, spherical Gaussian 0.8 mm FWHM/3 sigma, STL, filament FDM.

- [ ] **Step 3: Render and verify both animations**

Use cardinality-guarded almandine kinematical/near-depth run arrays, render
direct x-axis and retained-depth x-axis outputs with four workers. Require
H.264 High, 1024 square, yuv420p, 144 frames, 12 fps, 12 seconds, and exact
manifest hashes.

- [ ] **Step 4: Build and verify both globes**

Use cardinality-guarded almandine reflector-catalog and kinematical runs.
Build both globe commands with the two recipes. Require passed, watertight,
winding-consistent meshes and preserved FDM warnings.

- [ ] **Step 5: Commit and review**

Run rotation/globe tests, Ruff on changed Python, rehash movies/STLs, commit
only the six tracked files, and require reviewer approval.

---

### Task 13: Publish almandine in the Atlas test-first

**Files:**
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Modify: `docs/atlas/PHASE_REGISTRY.yml`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_ATTRIBUTION.md`

**Interfaces:**
- Consumes: complete almandine paths.
- Produces: 14 phases, 140 products, 14 sources, and 9 CC0 records.

- [ ] **Step 1: Update exact tests and confirm RED**

Add almandine to phase/source sets, family `garnet`, hero
`almandine-direct-standard`, exact nine IDs, and counts 14/140/14/9. Require
RED before registry changes.

- [ ] **Step 2: Register exact phase and products**

Use display `Almandine (293 K synthetic Fe endmember)`, formula
`Fe3Al2Si3O12`, cubic garnet scope, source record, and these IDs:

```text
almandine-direct-standard
almandine-direct-azimuthal-60
almandine-direct-tilt-plus-20
almandine-direct-oblique-high
almandine-x-axis-rotation
almandine-reflector-ridge-globe
almandine-atlas-kinematical-master
almandine-atlas-retained-depth-x-axis
almandine-atlas-kinematical-intensity-relief
```

Bind only existing media/preview/bundle/provenance/recipe paths.

- [ ] **Step 3: Regenerate, verify, commit, and review**

Regenerate release metadata, run Atlas/release tests, build the Atlas at
14/140, diff-check, commit the six files, and require reviewer approval.

---

### Task 14: Accept almandine and close its work item

**Files:**
- Create: `docs/acceptance/almandine-atlas-parity.md`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`
- Modify: `docs/work/KIKU-F031.md`
- Modify: `docs/work/KIKU-T081.md`
- Create: `docs/work/KIKU-T086.md`

**Interfaces:**
- Consumes: complete almandine evidence.
- Produces: durable acceptance at 14/140 while umbrella items remain active.

- [ ] **Step 1: Audit all artifacts and write acceptance**

Repeat the manifest/file/hash, ffprobe, and mesh validation over
`local/atlas-expansion/almandine`. Record the selected source decision, exact
IDs/counts, parity, animation profiles, meshes/FDM warnings, 14/140, 14
sources/9 CC0, and all nonclaims.

- [ ] **Step 2: Update tracking symmetrically**

Create done child `KIKU-T086`, add it to `KIKU-F031`, add source evidence to
`KIKU-T081`, move almandine to existing coverage, and leave the umbrella
feature/intake active.

- [ ] **Step 3: Run completion and broad-review gates**

Run all almandine-focused and shared Atlas tests, work-item validation, fresh
Atlas build, diff checks, and the attached full suite. Commit only the five
acceptance/tracker files and require a broad slice reviewer.

---

### Task 15: Promote a deterministic exact-composition tremolite derivative

**Files:**
- Create: `tests/adapters/test_tremolite_anfa_source.py`
- Create: `phases/tremolite-anfa/COD-2108838-original.cif`
- Create: `phases/tremolite-anfa/COD-2108838-consolidated-sites.cif`
- Create: `phases/tremolite-anfa/source.yml`

**Interfaces:**
- Consumes: COD 2108838 split-occupancy atom loop.
- Produces: verified `COD-2108838-consolidated-sites` with 17 independent rows and 98 expanded atom positions.

- [ ] **Step 1: Write the failing exact-composition test**

Assert:

```python
assert record.identifier == "COD-2108838-consolidated-sites"
assert record.formula == "Al0.68Ca1.99F0.33H1.61K0.20Mg5.09O23.67Si7.32"
assert record.space_group_number == 12
assert record.setting == "C 1 2/m 1"
assert record.simulation_setting["temperature_k"] == 293.0
assert record.simulation_setting["target_site_multiplicities"] == [
    4, 4, 2, 4, 8, 8, 8, 8, 8, 4, 4, 4, 8, 8, 8, 4, 4
]
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == (
    "91ebb6aad65f380714c3963d83ed7be297ed76d8509d3e18699c3e2d3f50b596"
)
assert len(_phase_from_record(record).structure) == 98
```

Also assert the 17 exact occupancies and Uiso values listed in Step 3.
Require RED because the source record is missing.

- [ ] **Step 2: Preserve the original and document the consolidation rule**

Retrieve COD 2108838 and require the pinned SHA. Preserve the IUCr attribution
notice, DOI `10.1107/S2052520621004844`, Ballirano et al. (2021) citation,
293(2) K condition, exact measured formula, and ANFa sample identity.

The derivative may consolidate only coincident rows with the same element and
identical coordinates/Uiso by summing occupancies:

```text
T1 + T1A -> T1 Si occupancy 0.830
T2 + T2A -> T2 Si occupancy 1.000
O1 + O1A -> O1 occupancy 1.000
O2 + O2A -> O2 occupancy 1.000
O3 + O3A -> O3 occupancy 0.835
O4 + O4A -> O4 occupancy 1.000
O5 + O5A -> O5 occupancy 1.000
O6 + O6A -> O6 occupancy 1.000
O7 + O7A -> O7 occupancy 1.000
```

Do not merge different elements sharing a site: retain T1AL Al and F3 F as
separate rows. Retain Mg occupancies above 1 exactly as refined.

- [ ] **Step 3: Write the exact derivative atom loop**

```cif
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_U_iso_or_equiv
_atom_site_occupancy
M1 Mg 0.00000 0.08833 0.50000 0.00580 1.0104
M2 Mg 0.00000 0.17645 0.00000 0.00470 1.0309
M3 Mg 0.00000 0.00000 0.00000 0.00537 1.0050
M4 Ca 0.00000 0.27880 0.50000 0.00858 0.9939
T1 Si 0.28019 0.08467 0.29965 0.00451 0.8300
T1AL Al 0.28019 0.08467 0.29965 0.00451 0.1700
T2 Si 0.28906 0.17207 0.80829 0.00486 1.0000
O1 O 0.10950 0.08663 0.21737 0.00698 1.0000
O2 O 0.11848 0.17170 0.72769 0.00662 1.0000
O3 O 0.10874 0.00000 0.71547 0.00803 0.8350
H H 0.20880 0.00000 0.77300 0.01000 0.8045
F3 F 0.10874 0.00000 0.71547 0.00803 0.1655
O4 O 0.36560 0.24926 0.79264 0.00875 1.0000
O5 O 0.34758 0.13648 0.10495 0.00936 1.0000
O6 O 0.34375 0.11849 0.59634 0.00867 1.0000
O7 O 0.33729 0.00000 0.29008 0.01064 1.0000
AM K 0.02710 0.50000 0.05710 0.05160 0.1004
```

Retain the original cell `9.8348, 18.0035, 5.2825, 90, 104.9961, 90`,
space-group operations, formula, citation, and provenance. Calculate and bind
the derivative SHA.

- [ ] **Step 4: Add the source record and confirm GREEN**

Use identity axis maps `[a,b,c]` and `[x,y,z]`, target setting
`C 1 2/m 1`, the exact 17 site rows, required thermal-factor policy, and a
scope note naming the 293 K ANFa measured composition. Run the source test and
require 98 expanded positions.

- [ ] **Step 5: Commit and source-review**

Commit only the four source/test files. Require a reviewer to re-sum the
consolidated occupancies to the declared formula, verify the 17-row rule,
original/derivative hashes, setting, multiplicities, citation, and scope.

---

### Task 16: Add tremolite-ANFa parity recipes test-first

**Files:**
- Modify: `tests/unit/test_atlas_extension_parity_recipes.py`
- Create: `recipes/reflectors/tremolite-anfa-art-bands.yml`
- Create: `recipes/reflectors/tremolite-anfa-catalog.yml`
- Create: `recipes/kinematical/tremolite-anfa-001-atlas-parity-master.yml`
- Create: `recipes/presentation/tremolite-anfa-near-depth-atlas-parity.yml`

**Interfaces:**
- Consumes: verified consolidated source.
- Produces: loader-accepted scientific recipes.

- [ ] **Step 1: Add failing parity tuple**

Add exact kinematical and near-depth paths, run the recipe test, and require
missing-file RED.

- [ ] **Step 2: Add direct and catalog recipes**

Use source `phases/tremolite-anfa/source.yml`, 20.0 keV, 0.7 angstrom,
`xtables`, candidate/source-master factor 0.03, art eligibility 0.08,
catalog selection 0.18, exponent 2.0, initial catalog threshold 0.10,
equal-weight tie policy, and four cohorts.

- [ ] **Step 3: Add kinematical and near-depth recipes**

Use name `tremolite-anfa-001-atlas-parity-master`, identity orientation,
detector 1536x2048 with TSL PC 0.50/0.72/0.60, sample tilt 70 degrees,
zero other detector angles, 5.859375 micrometre pixels, binning and
supersampling 1, half-size 512, both hemispheres, square scaling, tone
0.5/99.85 and asinh 7, figure 2400, and the balanced/quiet style values
0.14/0.54/0.36 and 0.22/0.62/0.42.

The near-depth recipe binds exact ID `recipe-6ddd6a040216cbdb`, uses overlap
0.22/2.0/99.5, optical gain 0.38, ceiling 0.985, center disabled, boundary
0.50/0.38/0.50 with casing 0.98/0.36, figure 2400, background `#101519`.
Independently assert the loader-emitted ID.

- [ ] **Step 4: Confirm GREEN, commit, and review**

Run recipe tests, commit the five files, and require a recipe reviewer.

---

### Task 17: Build tremolite-ANFa scientific intermediates

**Files:**
- Create gitignored artifacts: `local/atlas-expansion/tremolite-anfa/`

**Interfaces:**
- Consumes: Task 16 recipes.
- Produces: parity, master, retained depth, four templates, and tied cohorts.

- [ ] **Step 1: Build direct catalog and parity**

```bash
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/tremolite-anfa-art-bands.yml --output local/atlas-expansion/tremolite-anfa/direct-catalog
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/tremolite-anfa-art-bands.yml --output local/atlas-expansion/tremolite-anfa/parity --timeout-seconds 90
```

If the simulator cannot represent the consolidated mixed occupancies or parity
does not pass exactly, stop publication and write the exact blocked evidence.

- [ ] **Step 2: Build master and retained depth**

```bash
uv run kikuchi-lab render-kinematical --recipe recipes/kinematical/tremolite-anfa-001-atlas-parity-master.yml --output local/atlas-expansion/tremolite-anfa/kinematical
uv run kikuchi-lab render-kinematical-depth --recipe recipes/presentation/tremolite-anfa-near-depth-atlas-parity.yml --output local/atlas-expansion/tremolite-anfa/near-depth
```

- [ ] **Step 3: Build templates and tied cohorts**

Resolve one direct catalog run; render four templates with phase
`tremolite-anfa`; build the catalog from
`recipes/reflectors/tremolite-anfa-catalog.yml`. Require four standard
templates and four nonempty tied cohorts, applying only the global threshold
ladder when necessary.

- [ ] **Step 4: Audit and artifact-review**

Verify all manifests/hashes, source and recipe lineage, canonical master,
parity, template orientations, and cohort ledger. Record exact results in
`.superpowers/sdd/tremolite-anfa-task-17-report.md` and require review.

---

### Task 18: Build tremolite-ANFa rotations and globes test-first

**Files:**
- Modify: `tests/unit/test_direct_reflector_rotation.py`
- Modify: `tests/unit/test_reflector_globe_recipe.py`
- Modify: `tests/unit/relief/test_relief_recipes.py`
- Modify: `scripts/render_direct_reflector_rotation.py`
- Create: `recipes/globes/tremolite-anfa-reflector-ridges.yml`
- Create: `recipes/relief/tremolite-anfa-atlas-parity-kinematical-intensity.yml`

**Interfaces:**
- Consumes: Task 17 exact bundles and hashes.
- Produces: two verified animations and two validated meshes.

- [ ] **Step 1: Add RED direct-source test and exact mapping**

Assert the literal path, phase `tremolite-anfa`, and standard treatment.
Require missing-key RED, add the single exact bundle path, then require GREEN.

- [ ] **Step 2: Add failing exact globe-recipe contracts, then the recipes**

Add tremolite-ANFa-specific loader tests covering every ridge and relief field;
require missing-file RED. The ridge recipe uses identifier
`COD-2108838-consolidated-sites`, 20 keV,
selected threshold, four cohorts, 80 mm, 3 mm outward relief, subdivision 7,
and tier values 1.2/1.4/0.8, 1.8/1.8/1.0, 2.4/2.2/1.2,
3.0/2.6/1.4 with fillet fraction 0.25.

The relief recipe binds actual canonical product/array/file hashes and uses
80 mm, 1.2 mm, subdivision 7, percentiles 1/99, gamma 1, bright-outward,
spherical Gaussian 0.8 mm FWHM/3 sigma, STL, and filament FDM.

- [ ] **Step 3: Render and verify both animations**

Use one-run guards for kinematical and near-depth inputs; render the direct
x-axis and retained-depth x-axis outputs with display label `Tremolite ANFa`.
Require H.264 High, 1024 square, yuv420p, 144 frames, 12 fps, 12 seconds,
and exact hashes.

- [ ] **Step 4: Build and verify both globes**

Use one-run guards for reflector catalog and kinematical master. Require
passed, watertight, winding-consistent meshes, exact STL hashes, and preserved
FDM warnings.

- [ ] **Step 5: Commit and review**

Run rotation/globe tests and Ruff, rehash outputs, commit only the six tracked
files, and require reviewer approval.

---

### Task 19: Publish tremolite ANFa in the Atlas test-first

**Files:**
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Modify: `docs/atlas/PHASE_REGISTRY.yml`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_ATTRIBUTION.md`

**Interfaces:**
- Consumes: complete tremolite-ANFa paths.
- Produces: 15 phases, 149 products, 15 sources, and 9 CC0.

- [ ] **Step 1: Update exact tests and confirm RED**

Add slug, family `amphibole`, hero, exact nine IDs, and counts 15/149/15/9.
Require RED before registry edits.

- [ ] **Step 2: Register the exact-composition phase**

```yaml
slug: tremolite-anfa
display_name: Tremolite ANFa (293 K measured composition)
family: amphibole
formula: Al0.68Ca1.99F0.33H1.61K0.20Mg5.09O23.67Si7.32
crystal_system: monoclinic
```

Register IDs:

```text
tremolite-anfa-direct-standard
tremolite-anfa-direct-azimuthal-60
tremolite-anfa-direct-tilt-plus-20
tremolite-anfa-direct-oblique-high
tremolite-anfa-x-axis-rotation
tremolite-anfa-reflector-ridge-globe
tremolite-anfa-atlas-kinematical-master
tremolite-anfa-atlas-retained-depth-x-axis
tremolite-anfa-atlas-kinematical-intensity-relief
```

Bind only existing media/preview/bundle/provenance/recipe paths and retain the
exact-composition scope note.

- [ ] **Step 3: Regenerate, verify, commit, and review**

Regenerate release metadata, run Atlas/release tests, build 15/149, diff-check,
commit the six files, and require reviewer approval.

---

### Task 20: Accept tremolite ANFa and complete the batch audit

**Files:**
- Create: `docs/acceptance/tremolite-anfa-atlas-parity.md`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`
- Modify: `docs/work/KIKU-F031.md`
- Modify: `docs/work/KIKU-T081.md`
- Create: `docs/work/KIKU-T087.md`
- Create: `docs/acceptance/atlas-phase-batch-2026-07-25.md`

**Interfaces:**
- Consumes: all accepted grossular, almandine, and tremolite evidence.
- Produces: tremolite acceptance plus a batch-level preservation/count audit.

- [ ] **Step 1: Reverify tremolite artifacts and write acceptance**

Audit every manifest/file/hash, both movies, both meshes, exact source
composition, consolidated-site derivation, all IDs/counts, FDM advisories, and
nonclaims. Create done child `KIKU-T087` and update feature/intake links
symmetrically while keeping both umbrella items active.

- [ ] **Step 2: Prove batch preservation and final inventory**

Compare parsed phase and product records from the stabilized 12/122 baseline
with current registries. Require every baseline record to be byte-equivalent as
a parsed object. Require exactly 27 new products if all three phases completed:

```text
grossular: 9
almandine: 9
tremolite-anfa: 9
```

Record any blocked phase instead of claiming 15/149.

- [ ] **Step 3: Run the final verification gate**

Run all three source tests, shared recipe/rotation/globe tests, Atlas/release
tests, work-item validation, a fresh Atlas build, Ruff on changed Python, and
diff checks. Run the full suite once in an attached session and report exact
totals and failures.

- [ ] **Step 4: Commit, broad-review, and prepare handoff**

Commit the six documentation files. Generate one full-range review package and
require a fresh broad reviewer to audit source science, 27 product records,
artifact lineage, registry preservation, tracking symmetry, and nonclaims.
Apply `superpowers:verification-before-completion`, then
`superpowers:finishing-a-development-branch`; do not push, merge, or clean up
the worktree without the user's chosen integration action.
