# Ice Ih Intensity and Reflector-Ridge Globes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build separate, reproducible Ice-Ih intensity-relief and analytic 15-reflector raised-ridge STL bundles from a shared phase-neutral reflector core.

**Architecture:** Restore the Ice Ih oxygen-sublattice source and the public diffsims/kikuchipy reflection path as project-owned plain-data contracts. A generic `reflectors` package produces an immutable catalog; an independent `reflector_globe` package evaluates analytic great-circle corridors directly on the existing deterministic icosphere. A small generic mesh-export seam is extracted from the existing intensity-relief package so the original Lambert/forsterite workflow remains behaviorally unchanged.

**Tech Stack:** Python 3.12, NumPy, SciPy, diffpy-structure, diffsims, kikuchipy 0.13.0, orix 0.14, trimesh, Matplotlib, PyYAML, pytest, Ruff.

## Global Constraints

- Preserve all existing forsterite intensity-relief recipe IDs, byte artifacts, and canonical `80.0 mm / 1.2 mm / subdivision-7` acceptance behavior.
- Restore the exact Ice source identity `COD-1572233-O-sublattice`, SHA-256 `4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81`, setting `P 63/m m c`, and oxygen-sublattice-only claim boundary.
- Keep `diffsims`, `orix`, and `kikuchipy` objects adapter-local; durable catalog, field, recipe, and mesh contracts are project-owned plain data.
- The ridge product uses the catalog policy `eligibility_min_weight: 0.08`, `keep_equal_weights_together`, normalized structure-factor ranking, and four nonempty strength cohorts; membership must not be hard-coded by position.
- Generate ridge geometry analytically from reflector normals and Bragg-width evidence. Never use pixels, SVG/PDF paths, image thresholding, blur, or a hybrid intensity term.
- All physical dimensions are explicit millimetres. The first ridge recipe has an 80 mm base diameter and a positive maximum relief of about 3 mm; exact review defaults are recipe data.
- Both product bundles are content-addressed, atomically published, deterministic on repeated execution, and independently labeled as intensity-derived versus reflector-defined science-art geometry.
- All STLs must be one watertight, consistently wound, positive-volume body with no validation repair. FDM/FlashForge details remain advisory metadata, not a printer toolpath contract.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `phases/ice-ih/source.yml`, `phases/ice-ih/COD-1572233-oxygen-sublattice.cif` | Restored, checksum-verified Ice Ih oxygen-sublattice source record. |
| `src/kikuchi_lab/reflectors/contracts.py` | Immutable reflection member/catalog and closed recipe data contracts. |
| `src/kikuchi_lab/reflectors/recipe.py` | Strict YAML loaders for reflection and selection recipes. |
| `src/kikuchi_lab/reflectors/diffsims_adapter.py` | Public-API enumeration, factor calculation, axial collapse, normals, and Bragg widths. |
| `src/kikuchi_lab/reflectors/catalog.py` | Tie-preserving normalized-strength selection and canonical catalog snapshots. |
| `src/kikuchi_lab/reflectors/bundle.py` | Atomic catalog publication, ledgers, and manifest. |
| `src/kikuchi_lab/kinematical/*` | Restored public-kikuchipy Ice master simulation adapter, isolated from durable types. |
| `src/kikuchi_lab/ice_globe/intensity.py` | Converts the restored stereographic Ice master to a project-owned directional scalar field and samples it at geodesic vertices. |
| `src/kikuchi_lab/globe_mesh.py` | Shared geometry-spec-aware mesh validation/export façade; old `relief` wrappers remain stable. |
| `src/kikuchi_lab/reflector_globe/field.py` | Analytic raised corridor field and bounded-union evaluation on S2. |
| `src/kikuchi_lab/reflector_globe/recipes.py` | Strict reflector-globe recipe and physical tier validation. |
| `src/kikuchi_lab/reflector_globe/workflow.py` | Build/publish reflector-ridge STL bundle and manifest. |
| `src/kikuchi_lab/ice_globe/workflow.py` | Build/publish the separate Ice intensity-relief STL bundle. |
| `recipes/kinematical/ice-ih-oxygen-quiet-proof.yml` | Bounded Ice simulation recipe. |
| `recipes/reflectors/ice-ih-catalog.yml` | Ice selection policy and source recipe linkage. |
| `recipes/globes/ice-ih-intensity.yml` | Ice intensity-globe physical/mapping recipe. |
| `recipes/globes/ice-ih-reflector-ridges.yml` | 15-family raised-ridge physical recipe. |
| `tests/adapters/test_ice_ih_reflectors.py` | Source setting, public adapter, normals, and factor/angle parity. |
| `tests/unit/test_reflector_*.py` | Contract, recipe, selection, and bundle unit tests. |
| `tests/scientific/test_reflector_ridge_field.py` | Analytic field, antipodes, profile, union, and physical bounds tests. |
| `tests/integration/test_ice_globe_workflows.py` | Both real-Ice smoke bundles, determinism, and product separation. |

### Task 1: Restore and verify the Ice-Ih source record

**Files:**

- Create: `phases/ice-ih/COD-1572233-oxygen-sublattice.cif`
- Create: `phases/ice-ih/source.yml`
- Create: `tests/adapters/test_ice_ih_source.py`

**Interfaces:**

- Consumes: `kikuchi_lab.sources.structure.load_structure_record(path)`.
- Produces: a `StructureRecord` with `identifier == "COD-1572233-O-sublattice"`, source SHA, space group 194, `P 63/m m c`, and the oxygen-only source scope used by later tasks.

- [ ] **Step 1: Write failing source-integrity tests**

```python
def test_ice_ih_oxygen_sublattice_source_is_verified() -> None:
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    assert record.identifier == "COD-1572233-O-sublattice"
    assert record.sha256 == "4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81"
    assert record.space_group_number == 194
    assert record.setting == "P 63/m m c"
    assert record.simulation_setting["model_scope"] == "average oxygen sublattice only"
    assert record.simulation_setting["omitted_source_sites"] == ["H1a", "H1b"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/adapters/test_ice_ih_source.py -q`

Expected: FAIL because the `phases/ice-ih` source files do not exist on `master`.

- [ ] **Step 3: Restore the exact tracked source material**

Recover only the two source files from historical commit `953bfbd` using Git’s file-level restore mechanism, then add no hand-edited changes to their CIF payload:

```bash
git show 953bfbd:phases/ice-ih/source.yml > /tmp/ice-source.yml
git show 953bfbd:phases/ice-ih/COD-1572233-oxygen-sublattice.cif > /tmp/ice.cif
```

Apply their content to the two repository paths with `apply_patch`. Preserve the source YAML’s CC0 provenance, lattice `[4.3815, 4.3815, 7.183, 90.0, 90.0, 120.0]`, thermal-factor policy, and explicit omission of the disordered hydrogen sites.

- [ ] **Step 4: Run the source and existing structure tests**

Run: `uv run pytest tests/adapters/test_ice_ih_source.py tests/adapters/test_forsterite_source.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add phases/ice-ih tests/adapters/test_ice_ih_source.py
git commit -m "feat: restore verified Ice Ih source"
```

### Task 2: Define phase-neutral reflection evidence and strict recipes

**Files:**

- Create: `src/kikuchi_lab/reflectors/__init__.py`
- Create: `src/kikuchi_lab/reflectors/contracts.py`
- Create: `src/kikuchi_lab/reflectors/recipe.py`
- Create: `tests/unit/test_reflector_contracts.py`
- Create: `tests/unit/test_reflector_recipe.py`
- Create: `recipes/reflectors/ice-ih-catalog.yml`

**Interfaces:**

- Produces `ReflectorMember(hkl, normal_crystal, dspacing_angstrom, bragg_half_width_rad, structure_factor_abs, normalized_weight)` with derived `member_id`.
- Produces `ReflectorCatalog(source_structure_id, source_structure_sha256, energy_kev, reflection_recipe_id, selection, members)` with derived `catalog_id`.
- Produces `load_reflector_recipe(path) -> ReflectorRecipe`.

- [ ] **Step 1: Write failing contract and loader tests**

```python
def test_member_requires_unit_normal_and_stable_intrinsic_id() -> None:
    member = ReflectorMember((1, 0, 0), [1.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0)
    assert member.member_id.startswith("reflector-member-")
    with pytest.raises(ValueError, match="unit normal"):
        ReflectorMember((1, 0, 0), [2.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0)

def test_ice_catalog_recipe_is_closed_and_records_selection_policy() -> None:
    recipe = load_reflector_recipe(ROOT / "recipes/reflectors/ice-ih-catalog.yml")
    assert recipe.eligibility_min_weight == 0.08
    assert recipe.tie_policy == "keep_equal_weights_together"
    assert recipe.cohort_count == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py -q`

Expected: FAIL with `ModuleNotFoundError: kikuchi_lab.reflectors`.

- [ ] **Step 3: Implement the immutable contracts and strict loader**

Use owned immutable `<f8` arrays and identity content that excludes local paths. The contract shape is:

```python
@dataclass(frozen=True)
class ReflectorMember:
    hkl: tuple[int, int, int]
    normal_crystal: np.ndarray
    dspacing_angstrom: float
    bragg_half_width_rad: float
    structure_factor_abs: float
    normalized_weight: float
    member_id: str = field(init=False)

@dataclass(frozen=True)
class ReflectorRecipe:
    schema_version: int
    source_record: str
    energy_kev: float
    min_dspacing_angstrom: float
    scattering_params: str
    eligibility_min_weight: float
    tie_policy: Literal["keep_equal_weights_together"]
    cohort_count: int
    recipe_id: str = field(init=False)
```

The YAML loader rejects unknown keys, non-relative source paths, nonpositive energy/spacing, `cohort_count != 4`, and a threshold other than the approved `0.08` in the tracked Ice recipe.

- [ ] **Step 4: Run the focused tests and formatter/linter**

Run: `uv run pytest tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py -q && uv run ruff check src/kikuchi_lab/reflectors tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py`

Expected: PASS and `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/reflectors recipes/reflectors/ice-ih-catalog.yml tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py
git commit -m "feat: define reflector evidence contracts"
```

### Task 3: Implement the public diffsims reflector adapter and tie-preserving catalog

**Files:**

- Create: `src/kikuchi_lab/reflectors/diffsims_adapter.py`
- Create: `src/kikuchi_lab/reflectors/catalog.py`
- Create: `tests/adapters/test_ice_ih_reflectors.py`
- Create: `tests/scientific/test_reflector_catalog.py`

**Interfaces:**

- Consumes: `StructureRecord`, `ReflectorRecipe`.
- Produces: `enumerate_reflector_members(source, recipe) -> tuple[ReflectorMember, ...]` and `build_reflector_catalog(source, recipe) -> ReflectorCatalog`.
- Guarantees: collapsed axial members are canonically sorted by `(-normalized_weight, hkl, member_id)`; all equal normalized weights occupy one cohort; the Ice catalog contains 30 members total and 15 eligible members.

- [ ] **Step 1: Write failing adapter/scientific tests**

```python
def test_ice_catalog_is_real_and_tie_preserving() -> None:
    source = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_reflector_recipe(ROOT / "recipes/reflectors/ice-ih-catalog.yml")
    catalog = build_reflector_catalog(source, recipe)
    eligible = [m for m in catalog.members if m.eligible]
    assert len(catalog.members) == 30
    assert len(eligible) == 15
    assert {m.cohort for m in eligible} == {1, 2, 3, 4}
    for weight in {m.normalized_weight for m in eligible}:
        assert len({m.cohort for m in eligible if m.normalized_weight == weight}) == 1

def test_member_normals_are_crystal_frame_unit_vectors() -> None:
    catalog = build_reflector_catalog(source, recipe)
    assert np.allclose([np.linalg.norm(m.normal_crystal) for m in catalog.members], 1.0, atol=5e-13)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/adapters/test_ice_ih_reflectors.py tests/scientific/test_reflector_catalog.py -q`

Expected: FAIL because adapter/catalog functions do not exist.

- [ ] **Step 3: Implement only public diffsims operations**

Adapt the historical public algorithm, keeping upstream types local:

```python
vectors = ReciprocalLatticeVector.from_min_dspacing(phase, min_dspacing=recipe.min_dspacing_angstrom)
vectors = vectors[_allowed_mask(vectors)].unique(use_symmetry=True).symmetrise()
vectors.sanitise_phase()
vectors.calculate_structure_factor(scattering_params=recipe.scattering_params)
vectors.calculate_theta(recipe.energy_kev * 1_000.0)
```

For primitive hexagonal Ice, `_allowed_mask()` must retain the documented `P`-hexagonal fallback and still calculate structure factors so screw/glide extinction is represented by vanishing factors. Convert each retained axial family to a canonical signed HKL and unit reciprocal-plane normal in the named crystal frame. Normalize weights by the finite maximum absolute structure factor. Build tied blocks before assigning four cohorts; do not use list slicing to assign cohorts.

- [ ] **Step 4: Run focused parity and regression tests**

Run: `uv run pytest tests/adapters/test_ice_ih_reflectors.py tests/scientific/test_reflector_catalog.py tests/adapters/test_kikuchipy_projection.py -q`

Expected: PASS. Record package versions in catalog provenance but exclude them from member intrinsic IDs.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/reflectors tests/adapters/test_ice_ih_reflectors.py tests/scientific/test_reflector_catalog.py
git commit -m "feat: build phase-neutral reflector catalogs"
```

### Task 4: Publish a standalone immutable reflector catalog bundle

**Files:**

- Create: `src/kikuchi_lab/reflectors/bundle.py`
- Create: `src/kikuchi_lab/workflows/ice_reflector_catalog.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_reflector_bundle.py`
- Create: `tests/integration/test_ice_reflector_catalog.py`

**Interfaces:**

- Produces `build_ice_reflector_catalog(recipe_path, output_root) -> ReflectorCatalogBuildResult`.
- CLI: `kikuchi-lab reflectors build --recipe recipes/reflectors/ice-ih-catalog.yml --output local/ice-reflector-catalog`.
- Bundle files: `reflector-catalog.json`, `catalog-recipe.json`, `catalog-ledger.json`, `manifest.json`.

- [ ] **Step 1: Write failing publication tests**

```python
def test_catalog_build_is_path_neutral_and_no_clobber(tmp_path: Path) -> None:
    left = build_ice_reflector_catalog(RECIPE, tmp_path / "left")
    right = build_ice_reflector_catalog(RECIPE, tmp_path / "right")
    assert left.run_id == right.run_id
    assert json.loads(left.catalog.read_text())["catalog_id"].startswith("reflector-catalog-")
    with pytest.raises(FileExistsError, match="completed reflector catalog"):
        build_ice_reflector_catalog(RECIPE, tmp_path / "left")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_reflector_bundle.py tests/integration/test_ice_reflector_catalog.py -q`

Expected: FAIL because no publication workflow exists.

- [ ] **Step 3: Implement atomic publication by reusing the existing proven helpers**

Use the no-replace staging/fsync mechanics from `kikuchi_lab.relief.workflow`; do not copy a second incompatible atomic algorithm. Serialize sorted, newline-terminated JSON. The ledger must include source checksum, recipe/catalog IDs, 30 total/15 eligible counts, exact cohort counts, threshold, tie policy, public package versions, and the oxygen-sublattice claim boundary.

- [ ] **Step 4: Run tests and exercise the CLI smoke build**

Run: `uv run pytest tests/unit/test_reflector_bundle.py tests/integration/test_ice_reflector_catalog.py tests/unit/test_cli.py -q && uv run kikuchi-lab reflectors build --recipe recipes/reflectors/ice-ih-catalog.yml --output /tmp/ice-reflector-catalog-smoke`

Expected: tests PASS; CLI prints JSON containing `run_id`, `catalog`, and `manifest`.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/reflectors/bundle.py src/kikuchi_lab/workflows/ice_reflector_catalog.py src/kikuchi_lab/cli/main.py tests/unit/test_reflector_bundle.py tests/integration/test_ice_reflector_catalog.py tests/unit/test_cli.py
git commit -m "feat: publish Ice reflector catalog bundles"
```

### Task 5: Restore a bounded Ice kinematical master as a separate source product

**Files:**

- Create: `src/kikuchi_lab/kinematical/__init__.py`
- Create: `src/kikuchi_lab/kinematical/contracts.py`
- Create: `src/kikuchi_lab/kinematical/recipe.py`
- Create: `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`
- Create: `src/kikuchi_lab/workflows/ice_kinematical.py`
- Create: `recipes/kinematical/ice-ih-oxygen-quiet-proof.yml`
- Create: `tests/adapters/test_ice_ih_kinematical.py`
- Create: `tests/integration/test_ice_kinematical.py`

**Interfaces:**

- Produces `KinematicalSimulation.master_stereographic` with shape `(2, 2*half_size+1, 2*half_size+1)`, public projection ledger, and source/recipe identity.
- Produces `simulate_ice_kinematical(recipe_path) -> KinematicalSimulation`.

- [ ] **Step 1: Write failing public-source tests**

```python
def test_ice_master_has_two_finite_stereographic_hemispheres() -> None:
    simulation = simulate_ice_kinematical(RECIPE)
    master = simulation.master_stereographic
    assert master.intensity.shape == (2, 65, 65)
    assert master.metadata["projection"] == "stereographic"
    assert master.metadata["hemisphere"] == "both"
    assert np.isfinite(master.intensity).all()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/adapters/test_ice_ih_kinematical.py tests/integration/test_ice_kinematical.py -q`

Expected: FAIL with missing `kikuchi_lab.kinematical`.

- [ ] **Step 3: Restore the bounded public-kikuchipy adapter, not its old art renderers**

Bring forward only the historical project-owned `KinematicalRecipe`, phase conversion, `ReciprocalLatticeVector` enumeration, `KikuchiPatternSimulator.calculate_master_pattern()`, and plain-data projection ledger. Do not restore tattoo, near-depth, SVG, or presentation renderer modules. The adapter must use the same Ice record from Task 1 and consume the catalog recipe evidence from Tasks 2–4 rather than recomputing unrecorded selection policy.

- [ ] **Step 4: Run the Ice kinematical and existing projection tests**

Run: `uv run pytest tests/adapters/test_ice_ih_kinematical.py tests/integration/test_ice_kinematical.py tests/adapters/test_kikuchipy_projection.py -q`

Expected: PASS. The test must verify identity orientation, right-handed crystal frame, both hemispheres, finite values, and the primitive-hexagonal fallback.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/kinematical src/kikuchi_lab/workflows/ice_kinematical.py recipes/kinematical/ice-ih-oxygen-quiet-proof.yml tests/adapters/test_ice_ih_kinematical.py tests/integration/test_ice_kinematical.py
git commit -m "feat: restore bounded Ice kinematical master"
```

### Task 6: Extract a source-agnostic globe mesh/export boundary without changing forsterite

**Files:**

- Create: `src/kikuchi_lab/globe_mesh.py`
- Modify: `src/kikuchi_lab/relief/mapping.py`
- Modify: `src/kikuchi_lab/relief/mesh.py`
- Modify: `src/kikuchi_lab/relief/workflow.py`
- Create: `tests/scientific/test_globe_mesh.py`
- Modify: `tests/scientific/relief/test_relief_mapping.py`
- Modify: `tests/integration/test_relief_workflow.py`

**Interfaces:**

- Produces `GlobeGeometrySpec(base_diameter_mm, maximum_relief_mm, subdivisions)` and `validate_globe_mesh(geometry, topology, spec) -> ReliefMeshValidation`.
- Existing `validate_canonical_relief_mesh()` remains as a strict wrapper with the old fixed constants.
- Produces `build_radial_geometry(topology, normalized_values, spec) -> ReliefGeometry` for any positive finite spec.

- [ ] **Step 1: Write failing generalization and compatibility tests**

```python
def test_generic_globe_geometry_accepts_three_mm_relief() -> None:
    topology = build_icosphere(2)
    geometry = build_radial_geometry(topology, np.ones(len(topology.directions)), GlobeGeometrySpec(80.0, 3.0, 2))
    assert np.allclose(geometry.radii_mm, 43.0)
    assert validate_globe_mesh(geometry, topology, GlobeGeometrySpec(80.0, 3.0, 2)).passed

def test_existing_canonical_relief_rejects_noncanonical_geometry() -> None:
    with pytest.raises(ValueError, match="80.0 mm diameter and 1.2 mm relief"):
        build_relief_geometry(build_icosphere(2), np.zeros(162), 80.0, 3.0)
```

- [ ] **Step 2: Run tests to verify the generic case fails**

Run: `uv run pytest tests/scientific/test_globe_mesh.py tests/scientific/relief/test_relief_mapping.py -q`

Expected: FAIL because existing geometry and validation hard-code `1.2 mm`.

- [ ] **Step 3: Extract without weakening the old public behavior**

Move shared topology/triangle/radial validation to `globe_mesh.py`. Parameterize its physical bounds from `GlobeGeometrySpec`. Keep `relief.mapping.build_relief_geometry()` and `relief.mesh.validate_canonical_relief_mesh()` as compatibility wrappers that explicitly supply the old `80.0/1.2/7` contract. Do not change relief bundle filenames or identity payload keys.

- [ ] **Step 4: Run compatibility and generic tests**

Run: `uv run pytest tests/scientific/test_globe_mesh.py tests/scientific/relief tests/integration/test_relief_workflow.py -q`

Expected: PASS, including existing canonical forsterite fixtures unchanged.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/globe_mesh.py src/kikuchi_lab/relief tests/scientific/test_globe_mesh.py tests/scientific/relief tests/integration/test_relief_workflow.py
git commit -m "refactor: share validated globe mesh boundary"
```

### Task 7: Implement the analytic raised-ridge field and physical recipe

**Files:**

- Create: `src/kikuchi_lab/reflector_globe/__init__.py`
- Create: `src/kikuchi_lab/reflector_globe/recipes.py`
- Create: `src/kikuchi_lab/reflector_globe/field.py`
- Create: `recipes/globes/ice-ih-reflector-ridges.yml`
- Create: `tests/unit/test_reflector_globe_recipe.py`
- Create: `tests/scientific/test_reflector_ridge_field.py`

**Interfaces:**

- Produces `ReflectorRidgeRecipe` with `geometry`, `selection`, and four `RidgeTier(height_mm, width_multiplier, minimum_width_mm, edge_fillet_fraction)` records.
- Produces `evaluate_reflector_ridges(catalog, recipe, directions) -> RidgeField(values, contributor_counts, field_id)` with values in `[0, 1]`.

- [ ] **Step 1: Write failing analytic-field tests**

```python
def test_one_band_has_a_raised_center_and_zero_outside_corridor() -> None:
    member = make_member(normal=(0.0, 0.0, 1.0), theta=0.10, weight=1.0)
    recipe = make_recipe(maximum_relief_mm=3.0)
    field = evaluate_reflector_ridges(catalog_of(member), recipe, [[1, 0, 0], [0, 0, 1]])
    assert field.values[0] == pytest.approx(1.0)
    assert field.values[1] == pytest.approx(0.0)

def test_band_field_is_antipodally_equal_and_union_is_bounded() -> None:
    field = evaluate_reflector_ridges(catalog, recipe, np.vstack([directions, -directions]))
    assert np.allclose(field.values[:len(directions)], field.values[len(directions):], atol=1e-12)
    assert np.all((0.0 <= field.values) & (field.values <= 1.0))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_reflector_globe_recipe.py tests/scientific/test_reflector_ridge_field.py -q`

Expected: FAIL because the recipe and field do not exist.

- [ ] **Step 3: Implement exact corridor and bounded-union math**

Use the named, deterministic functions below. Clamp dot products before `arcsin`; reject invalid normals/tiers before evaluation.

```python
def corridor_profile(distance_rad: np.ndarray, half_width_rad: float, fillet_fraction: float) -> np.ndarray:
    x = np.abs(distance_rad) / half_width_rad
    flat = 1.0 - fillet_fraction
    return np.where(x <= flat, 1.0, np.where(x < 1.0, 0.5 * (1.0 + np.cos(np.pi * (x - flat) / fillet_fraction)), 0.0))

def bounded_union(contributions: np.ndarray) -> np.ndarray:
    return 1.0 - np.prod(1.0 - np.clip(contributions, 0.0, 1.0), axis=0)
```

For each member, calculate `distance = arcsin(clip(directions @ normal, -1, 1))`. Convert angular width to a recipe-recorded effective corridor width using the Bragg half-width, tier multiplier, and physical minimum-width rule at the base radius. Divide tier height by `maximum_relief_mm` before union. Store each selected member’s tier and effective width in the field ledger.

- [ ] **Step 4: Run scientific tests and static checks**

Run: `uv run pytest tests/unit/test_reflector_globe_recipe.py tests/scientific/test_reflector_ridge_field.py -q && uv run ruff check src/kikuchi_lab/reflector_globe tests/unit/test_reflector_globe_recipe.py tests/scientific/test_reflector_ridge_field.py`

Expected: PASS and `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/reflector_globe recipes/globes/ice-ih-reflector-ridges.yml tests/unit/test_reflector_globe_recipe.py tests/scientific/test_reflector_ridge_field.py
git commit -m "feat: model analytic reflector ridge fields"
```

### Task 8: Build and publish the Ice reflector-ridge globe

**Files:**

- Create: `src/kikuchi_lab/reflector_globe/workflow.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_reflector_globe_bundle.py`
- Create: `tests/integration/test_ice_reflector_globe.py`
- Create: `docs/acceptance/ice-ih-reflector-ridge-globe.md`

**Interfaces:**

- Produces `build_reflector_globe(catalog_path, recipe_path, output_root) -> ReflectorGlobeBuildResult`.
- CLI: `kikuchi-lab reflector-globe build --catalog <catalog.json> --recipe recipes/globes/ice-ih-reflector-ridges.yml --output local/ice-reflector-globes`.
- Bundle files: `ice-ih-reflector-ridges.stl`, `ice-ih-reflector-ridges-preview.png`, `ridge-field.npz`, `ridge-ledger.json`, `mesh-validation.json`, `reflector-globe-manifest.json`.

- [ ] **Step 1: Write failing end-to-end bundle tests**

```python
def test_real_ice_ridge_globe_is_a_watertight_three_mm_bounded_single_body(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    result = build_reflector_globe(catalog.catalog, RIDGE_RECIPE, tmp_path / "globes")
    validation = json.loads(result.validation.read_text())
    assert validation["watertight"] is True
    assert validation["winding_consistent"] is True
    assert validation["body_count"] == 1
    assert validation["minimum_radius_mm"] >= 40.0
    assert validation["maximum_radius_mm"] <= 43.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_reflector_globe_bundle.py tests/integration/test_ice_reflector_globe.py -q`

Expected: FAIL because no reflector-globe workflow exists.

- [ ] **Step 3: Implement atomic bundle publication**

Build subdivision-7 topology, evaluate the analytic field at its directions, call `build_radial_geometry()`, then use the generic mesh façade for validation/STL/preview. Derive build identity from recipe, catalog ID, selected member IDs, field ID, topology ID, validation contract, and software versions. Write the manifest last. Reject a catalog whose source/energy/selection policy does not match the recipe before any output mutation.

- [ ] **Step 4: Run smoke/full workflow validation and document review evidence**

Run: `uv run pytest tests/unit/test_reflector_globe_bundle.py tests/integration/test_ice_reflector_globe.py -q && catalog_json=$(find /tmp/ice-reflector-catalog-smoke -name reflector-catalog.json -print -quit) && test -n "$catalog_json" && uv run kikuchi-lab reflector-globe build --catalog "$catalog_json" --recipe recipes/globes/ice-ih-reflector-ridges.yml --output local/ice-reflector-globes`

Expected: tests PASS; CLI prints bundle paths. Record the actual IDs, counts, physical bounds, hashes, and visual-review status in the acceptance note without claiming a physical print.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/reflector_globe/workflow.py src/kikuchi_lab/cli/main.py tests/unit/test_reflector_globe_bundle.py tests/integration/test_ice_reflector_globe.py docs/acceptance/ice-ih-reflector-ridge-globe.md
git commit -m "feat: publish Ice reflector ridge globe"
```

### Task 9: Build and publish the separate Ice intensity-relief globe

**Files:**

- Create: `src/kikuchi_lab/ice_globe/__init__.py`
- Create: `src/kikuchi_lab/ice_globe/intensity.py`
- Create: `src/kikuchi_lab/ice_globe/workflow.py`
- Create: `recipes/globes/ice-ih-intensity.yml`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/scientific/test_ice_intensity_field.py`
- Modify: `tests/integration/test_ice_globe_workflows.py`
- Create: `docs/acceptance/ice-ih-intensity-relief-globe.md`

**Interfaces:**

- Produces `build_ice_intensity_globe(kinematical_recipe, globe_recipe, output_root) -> IceIntensityGlobeBuildResult`.
- CLI: `kikuchi-lab ice-globe intensity --kinematical-recipe ... --recipe recipes/globes/ice-ih-intensity.yml --output local/ice-intensity-globes`.

- [ ] **Step 1: Write failing field/product-separation tests**

```python
def test_ice_intensity_field_comes_from_master_values_not_reflector_ridges() -> None:
    field = build_ice_intensity_field(simulate_ice_kinematical(KINEMATICAL_RECIPE))
    assert field.source_kind == "kinematical_stereographic_master"
    assert field.field_id.startswith("ice-intensity-field-")
    assert field.raw_values.ptp() > 0.0

def test_intensity_and_ridge_bundles_have_distinct_product_kinds(tmp_path: Path) -> None:
    intensity = build_ice_intensity_globe(KINEMATICAL_RECIPE, INTENSITY_RECIPE, tmp_path / "intensity")
    ridge = build_reflector_globe(CATALOG, RIDGE_RECIPE, tmp_path / "ridge")
    assert json.loads(intensity.manifest.read_text())["product_kind"] == "intensity_relief"
    assert json.loads(ridge.manifest.read_text())["product_kind"] == "reflector_defined_ridges"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scientific/test_ice_intensity_field.py tests/integration/test_ice_globe_workflows.py -q`

Expected: FAIL because no Ice intensity field/workflow exists.

- [ ] **Step 3: Implement stereographic master sampling without pretending it is Lambert**

Reuse the restored public-orix stereographic mapping semantics to create a directional field with explicit upper/lower ownership and seam diagnostics. Sample that field at icosphere directions, apply one global percentile/gamma mapping declared by `ice-ih-intensity.yml`, then use the generic radial mesh/export boundary. Do not route this source through `relief.field.build_spherical_scalar_field()`, whose contract is specifically Lambert-square input; do not relabel stereographic data as Lambert.

- [ ] **Step 4: Run both real-Ice workflows and regression tests**

Run: `uv run pytest tests/scientific/test_ice_intensity_field.py tests/integration/test_ice_globe_workflows.py tests/scientific/relief tests/integration/test_relief_workflow.py -q`

Expected: PASS. Assert deterministic rerun identities for both Ice products and unchanged forsterite relief tests.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/ice_globe recipes/globes/ice-ih-intensity.yml src/kikuchi_lab/cli/main.py tests/scientific/test_ice_intensity_field.py tests/integration/test_ice_globe_workflows.py docs/acceptance/ice-ih-intensity-relief-globe.md
git commit -m "feat: publish separate Ice intensity globe"
```

### Task 10: Execute acceptance, update the tracker, and run the full regression gate

**Files:**

- Modify: `docs/work/KIKU-F006.md`
- Modify: `docs/work/KIKU-E001.md` only if parent acceptance evidence needs the new links
- Modify: `docs/acceptance/ice-ih-reflector-ridge-globe.md`
- Modify: `docs/acceptance/ice-ih-intensity-relief-globe.md`

**Interfaces:**

- Consumes: both published bundles from Tasks 8–9.
- Produces: checked acceptance evidence with no physical-print claim and an updated feature status that truthfully reflects any remaining visual/slicer gate.

- [ ] **Step 1: Write a failing acceptance inventory assertion**

```python
def test_ice_globe_acceptance_notes_name_distinct_product_boundaries() -> None:
    ridge = (ROOT / "docs/acceptance/ice-ih-reflector-ridge-globe.md").read_text()
    intensity = (ROOT / "docs/acceptance/ice-ih-intensity-relief-globe.md").read_text()
    assert "not a dynamical EBSD intensity simulation" in ridge
    assert "raw kinematical master" in intensity
    assert "hybrid" not in ridge.lower()
```

- [ ] **Step 2: Run it to verify it fails until evidence is recorded**

Run: `uv run pytest tests/integration/test_ice_globe_workflows.py::test_ice_globe_acceptance_notes_name_distinct_product_boundaries -q`

Expected: FAIL before the acceptance notes contain actual run evidence.

- [ ] **Step 3: Record only generated evidence and user visual review**

Capture source/catalog/build IDs, SHA-256 manifests, selection/cohort counts, physical bounds, and mesh-validation results from the real bundles. Mark visual readability as pending until the user explicitly approves native previews; keep physical FDM printing and slicer ingestion as separate external gates.

- [ ] **Step 4: Run the complete verification gate**

Run: `uv run pytest -q && uv run ruff check . && uv run python scripts/validate_work_items.py && git diff --check`

Expected: all tests PASS, Ruff reports `All checks passed!`, work-item validation succeeds, and `git diff --check` exits 0.

- [ ] **Step 5: Commit**

```bash
git add docs/work/KIKU-F006.md docs/work/KIKU-E001.md docs/acceptance/ice-ih-reflector-ridge-globe.md docs/acceptance/ice-ih-intensity-relief-globe.md tests/integration/test_ice_globe_workflows.py
git commit -m "docs: record Ice globe acceptance evidence"
```

## Self-Review

### Spec coverage

- Separate intensity and reflector products: Tasks 5, 8, and 9.
- Restored Ice oxygen-sublattice provenance: Task 1 and catalog/bundle Tasks 3–4.
- Phase-neutral source methods: Tasks 2–4; no Ice-only evidence types.
- Exact 15-member, tie-preserving, four-cohort policy: Tasks 2–4 and 7.
- Analytic raised ridges with bounded intersections: Task 7.
- ~3 mm Ice ridge geometry without changing the old 1.2 mm product: Task 6.
- Atomic bundles, independent labels, STL checks, no print claim: Tasks 4, 8–10.
- Existing forsterite relief preserved: Task 6 regression and Task 9 full compatibility gate.

### Placeholder scan

No unresolved implementation markers, generic “add validation,” or implicit test steps remain. Every command has a concrete input path or discovers the content-addressed artifact produced by the preceding command.

### Type consistency

`ReflectorMember` and `ReflectorCatalog` are defined before use by the adapter, field, and bundle tasks. `GlobeGeometrySpec` and `build_radial_geometry()` are defined before reflector/intensity workflows consume them. The old `relief` functions remain wrappers, so existing imports and canonical acceptance tests retain their exact contract.
