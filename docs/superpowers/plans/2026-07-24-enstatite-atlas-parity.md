# Enstatite Atlas Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the 0 GPa COD 9001593 orthoenstatite structure into the Kikuchi Atlas with the same nine registered product roles as calcite.

**Architecture:** Reuse the established phase source, direct-reflector, kinematical, near-depth, rotation, ridge-globe, relief-globe, and Atlas registry contracts. Keep the exact Pbca MgSiO3 structure and source conditions visible; do not generalize it to all orthopyroxenes or pyroxenes.

**Tech Stack:** Python 3.12, PyCifRW, diffpy.structure, diffsims, kikuchipy, NumPy, trimesh, ffmpeg, pytest, YAML.

## Global Constraints

- Do not remove, rename, or replace any existing phase or product.
- Use COD 9001593 exactly as retrieved on 2026-07-24 and verify its SHA-256 before product generation.
- Preserve the source formula `MgSiO3`, space group 61, Pbca setting, 0 GPa condition, ten independent sites, implicit full occupancies, and explicit Uiso values.
- Preserve the source CIF's scientific-community attribution-use notice rather than rewriting it as a generic CC0 declaration.
- Publish no Atlas product entry until its media, preview, bundle, provenance, and recipe paths exist.
- Describe this as one pure 0 GPa orthoenstatite reference, not the full enstatite-ferrosilite or pyroxene compositional field.

---

### Task 1: Promote the exact enstatite source with a failing source test

**Files:**
- Create: `tests/adapters/test_enstatite_source.py`
- Create: `phases/enstatite/COD-9001593.cif`
- Create: `phases/enstatite/source.yml`

**Interfaces:**
- Consumes: `load_structure_record(path)` and `verify_structure(record)`.
- Produces: a verified `StructureRecord` for downstream reflector and master builders.

- [x] **Step 1: Write the failing test**

```python
def test_enstatite_zero_gpa_source_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(ROOT / "phases/enstatite/source.yml")
    verified = verify_structure(record)
    assert record.identifier == "COD-9001593"
    assert record.formula == "MgSiO3"
    assert record.space_group_number == 61
    assert record.setting == "P b c a"
    assert record.simulation_setting["pressure_gpa"] == 0.0
    assert record.simulation_setting["target_site_multiplicities"] == [8] * 10
    assert verified.sha256_matches
    assert verified.occupancy_source == "implicit CIF default 1.0"
```

- [x] **Step 2: Run the test and confirm RED**

Run: `uv run pytest -q tests/adapters/test_enstatite_source.py`

Expected: FAIL because `phases/enstatite/source.yml` does not exist.

- [x] **Step 3: Acquire and describe the source**

Retrieve `https://www.crystallography.net/cod/9001593.cif`, require SHA-256 `9a7e8ca57e3eb4f804fdeb4954566cfaa7b3a61fe24f4931c9c76c1e8228d51d`, and add a source record with the ten CIF sites, Uiso values, direct Pbca setting, and `[8] * 10` multiplicities.

- [x] **Step 4: Run the source test and confirm GREEN**

Run: `uv run pytest -q tests/adapters/test_enstatite_source.py`

Expected: `1 passed`.

### Task 2: Add parity recipes and build scientific products

**Files:**
- Modify: `tests/unit/test_atlas_extension_parity_recipes.py`
- Create: `recipes/reflectors/enstatite-catalog.yml`
- Create: `recipes/reflectors/enstatite-art-bands.yml`
- Create: `recipes/kinematical/enstatite-001-atlas-parity-master.yml`
- Create: `recipes/presentation/enstatite-near-depth-atlas-parity.yml`

**Interfaces:**
- Consumes: verified enstatite source record.
- Produces: direct catalog, passed parity report, canonical master, and near-depth bundle.

- [x] **Step 1: Add enstatite to `PARITY_RECIPES` and confirm RED**

Run: `uv run pytest -q tests/unit/test_atlas_extension_parity_recipes.py`

Expected: FAIL because the enstatite recipes do not exist.

- [x] **Step 2: Add recipes following calcite's fixed 20 keV, 0.7 Å, 512-half-size parity contract**

Load the new kinematical recipe to derive its exact `recipe_id`, then bind that ID in the near-depth recipe.

- [x] **Step 3: Confirm recipe GREEN**

Run: `uv run pytest -q tests/unit/test_atlas_extension_parity_recipes.py`

Expected: all parameterized phases pass.

- [x] **Step 4: Build the zero-master catalog, one bounded parity smoke, full kinematical master, and near-depth bundle**

Run the `build-direct-art-catalog`, `validate-reflector-parity`, `render-kinematical`, and `render-kinematical-depth` CLI commands under `local/atlas-expansion/enstatite`.

### Task 3: Build the art, motion, and printable products

**Files:**
- Modify: `scripts/render_direct_reflector_rotation.py`
- Create: `recipes/globes/enstatite-reflector-ridges.yml`
- Create: `recipes/relief/enstatite-atlas-parity-kinematical-intensity.yml`

**Interfaces:**
- Consumes: direct catalog, passed parity evidence, canonical master, and near-depth bundle.
- Produces: four templates, two MP4 rotations, reflector-ridge STL, and intensity-relief STL.

- [x] **Step 1: Render the four standard orientation templates**

Run `scripts/render_phase_art_templates.py` from the saved direct catalog.

- [x] **Step 2: Add the generated standard template bundle to `PHASE_SOURCES`**

Use the exact content-addressed template directory, then render the 144-frame 1024 px x-axis direct rotation.

- [x] **Step 3: Render the retained-field rotation**

Run `scripts/render_retained_near_depth_rotation.py` with the exact enstatite kinematical and near-depth run directories.

- [x] **Step 4: Build both printable globes**

Tune only the ridge eligibility cutoff if necessary to preserve four tied cohorts; build and validate the subdivision-7 80 mm reflector-ridge and intensity-relief STLs.

### Task 4: Publish enstatite in the Atlas with failing registry tests

**Files:**
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Modify: `docs/atlas/PHASE_REGISTRY.yml`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_ATTRIBUTION.md`

**Interfaces:**
- Consumes: verified local artifact paths.
- Produces: an eleven-phase Atlas with 113 available products.

- [x] **Step 1: Update expected phase/product/source counts and confirm RED**

Expect 11 phases, 113 products, 11 source records, and nine CC0 sources.

Run: `uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_release_metadata.py`

Expected: FAIL until the registries contain enstatite.

- [x] **Step 2: Add one exact phase record and nine product records**

Register four templates, direct rotation, ridge globe, kinematical master, retained-depth rotation, and relief globe using only existing paths.

- [x] **Step 3: Regenerate release metadata and confirm GREEN**

Run `uv run python scripts/build_release_metadata.py`, then rerun the Atlas and release-metadata tests.

### Task 5: Record acceptance and verify the whole slice

**Files:**
- Create: `docs/acceptance/enstatite-atlas-parity.md`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`
- Modify: `docs/work/KIKU-F031.md`
- Modify: `docs/work/KIKU-T081.md`
- Create: `docs/work/KIKU-T083.md`

**Interfaces:**
- Consumes: manifests, checksums, mesh validations, tests, and Atlas build result.
- Produces: durable acceptance evidence and tracker state.

- [x] **Step 1: Verify every manifest inventory and both mesh validations**

Require all listed bytes and SHA-256 values to match, and both meshes to report watertight and winding-consistent.

- [x] **Step 2: Build the Atlas and run focused regression tests**

Run:

```bash
uv run python scripts/validate_work_items.py
uv run pytest -q tests/adapters/test_enstatite_source.py tests/unit/test_atlas.py tests/unit/test_atlas_release_metadata.py tests/unit/test_atlas_extension_parity_recipes.py
uv run python scripts/build_atlas.py --output local/atlas-expansion/site
git diff --check
```

- [x] **Step 3: Record exact IDs, counts, checksums, commands, and nonclaims**

Mark only the enstatite task done; keep `KIKU-F031` active for the remaining requested minerals.
