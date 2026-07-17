# Phase-General Direct-Reflector Art Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build orientation-independent direct reflector catalogs for five phases, verify each catalog through one killable smoke master, and publish four new standard plus five new 15-percent-wider crisp hemisphere-art bundles and a ten-cell comparison sheet.

**Architecture:** A strict direct-reflector recipe drives the existing diffpy/diffsims reflector calculation only through the pre-raster boundary and returns immutable project-owned evidence. Catalog construction consumes that evidence without a `PresentationSource`; a separate subprocess-bounded parity command is the only path allowed to calculate a master. A phase-general hemisphere recipe then selects one 11-band composition per phase and renders standard and wide geometry from the same frozen selection.

**Tech Stack:** Python 3.11+, NumPy, diffpy-structure, diffsims, kikuchipy, orix, PyYAML, Pillow, matplotlib, pytest, Ruff, repository-native artifact and identity helpers.

## Global Constraints

- Routine direct-catalog and series production must report `simulation_count=0` and must never instantiate or calculate a master pattern.
- Parity is an explicit separate command with one `half_size=32`, `hemisphere=both`, `scaling=square` master calculation, a hard 90-second subprocess deadline, no retry, and no automatic resolution increase.
- First-series reflector calculation is fixed at 20.0 keV, 0.7 angstrom minimum d-spacing, `xtables`, candidate floor `abs(F_hkl) >= 0.03 * max(abs(F_hkl))`, weight `(abs(F_hkl) / max(abs(F_hkl)))^2`, and art eligibility `>= 0.08`.
- Every phase uses active crystal-to-sample Bunge ZXZ `(17, 31, 43)` degrees from recipe data; orientation is absent from reflector-catalog identity.
- Each phase selection contains exactly 11 unique axial members with `4/4/3` tier allocation, 4 degree redundancy threshold, six coverage sectors, 721 great-circle samples, 0.90 crop radius, and 6 degree zone-interior margin.
- Standard widths are `[4.8, 4.2, 3.6, 3.1]`, `[2.5, 2.2, 1.9, 1.6]`, and `[1.2, 1.0, 0.8]` mm. Wide geometry multiplies only these arc widths by exactly `1.15`.
- The 145.0 mm artboard, 132.0 mm outer diameter, 2.20 mm boundary, 63.8 mm crystallographic clip radius, centerlines, selected member IDs, projection, palette, and lack of blur remain identical between treatments.
- The reviewed Ice Ih standard-reference bundle is read-only and is never regenerated, overwritten, or silently reselected.
- Corrected Ice products rebind the reviewed 11 canonical HKLs through `recipes/art/ice-ih-reviewed-selection-v2.yml`; they never reuse legacy calculated IDs and always retain the manifest snapshot in the bundle.
- Quartz uses COD 9012600; zircon uses a documented isotropic-U derivative of COD 9000684; titanite uses COD 9000509. All source files and source records are checksum-verified and CC0-attributed.
- Every non-test scientific or visual product is retained under `local/phase-general-direct-reflector-art/` (or an explicitly indexed legacy reference root) in its content-identified directory and is indexed in the acceptance record with the exact reproduction command, recipe/source IDs, manifest ID, and checksums. Pytest temporary outputs are verification scaffolding, not products.
- Existing Ice-specific catalog, recipe, workflow, filenames, IDs, and tests remain backward compatible.
- Legacy Ice artifacts remain load-only compatible. Corrected generation deliberately receives new catalog/member/selection/geometry/run IDs because the repaired non-orthogonal structure-factor boundary changes scientific content.
- Every task follows red-green-refactor TDD, runs the narrow tests first, runs Ruff on touched Python, validates work items when tracker state changes, and commits only its own files.
- Preserve all unrelated dirty files in the worktree.

---

## File and Responsibility Map

### New scientific core

- `src/kikuchi_lab/kinematical/reflector_evidence.py`: strict direct-reflector recipe, owned axial evidence contract, serialization, and identity boundaries.
- `src/kikuchi_lab/kinematical/reflector_parity.py`: numeric direct-versus-simulator reflector comparison contract.
- `src/kikuchi_lab/workflows/direct_art_catalog.py`: zero-master catalog build and atomic publication workflow.
- `src/kikuchi_lab/workflows/reflector_parity.py`: killable subprocess parity orchestration and retained report bundle.

### New phase sources and recipes

- `phases/quartz/COD-9012600.cif`, `phases/quartz/source.yml`.
- `phases/zircon/COD-9000684-original.cif`, `phases/zircon/COD-9000684-isotropic-u.cif`, `phases/zircon/source.yml`.
- `phases/titanite/COD-9000509.cif`, `phases/titanite/source.yml`.
- `recipes/reflectors/{ice-ih,forsterite,quartz,zircon,titanite}-art-bands.yml`: identical first-series calculation policy with phase-specific source paths.

### New phase-general art surface

- `src/kikuchi_lab/art_products/hemisphere_recipe.py`: series, phase-composition, and standard/wide treatment contracts.
- `src/kikuchi_lab/art_products/hemisphere_bundle.py`: generic atomic vector bundle wrapper while preserving the legacy Ice wrapper.
- `src/kikuchi_lab/art_products/series_sheet.py`: direct-at-target-resolution ten-cell review rendering; no post-render blur or resize.
- `src/kikuchi_lab/workflows/phase_art_series.py`: parity-gated catalog, selection, standard/wide rendering, and series publication.
- `recipes/art/five-phase-hemisphere-series.yml`: phase order, source recipes, shared orientation, selection, geometry, and treatment scales.

### Existing files modified deliberately

- `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`: expose pre-master direct evidence while retaining simulation behavior.
- `src/kikuchi_lab/art_products/catalog.py`: add an evidence-first catalog builder and retain the legacy presentation wrapper.
- `src/kikuchi_lab/art_products/tattoo_selection.py`: consume a structural recipe protocol rather than only the Ice concrete class.
- `src/kikuchi_lab/art_products/tattoo_vector.py`: accept a width scale while preserving the default legacy geometry byte-for-byte.
- `src/kikuchi_lab/art_products/tattoo_bundle.py`: extract generic internal publication without changing the public Ice call.
- `src/kikuchi_lab/{kinematical,art_products,workflows}/__init__.py`: export only the new public seams.
- `src/kikuchi_lab/cli/main.py`: add `build-direct-art-catalog`, `validate-reflector-parity`, and `render-phase-art-series`.
- `reference/catalog/crystallography-open-database.yml`: register the three exact new COD sources and the zircon derivative policy.
- `docs/acceptance/phase-general-direct-reflector-art-series.md`: record real run IDs, parity evidence, bundle matrix, and visual-review status.
- `docs/work/KIKU-{F006,T032,T033,T034}.md`: link the plan and update status only as acceptance criteria are actually met.

---

### Task 1: Define strict direct-reflector recipes and owned evidence

**Tracker:** KIKU-T032

**Files:**
- Create: `src/kikuchi_lab/kinematical/reflector_evidence.py`
- Create: `tests/unit/test_reflector_evidence.py`
- Create: `recipes/reflectors/ice-ih-art-bands.yml`
- Create: `recipes/reflectors/forsterite-art-bands.yml`
- Modify: `src/kikuchi_lab/kinematical/__init__.py`

**Interfaces:**
- Produces: `DirectReflectorRecipe`, `DirectReflectorEvidence`,
  `load_direct_reflector_recipe(path)`, and
  `own_direct_reflector_evidence(reflectors, source_structure_id,
  source_structure_sha256, calculation_id, weighting_id, weight_exponent,
  eligibility_min_weight, counts)`.
- `DirectReflectorEvidence` owns `hkl`, `normal_crystal`, `dspacing_angstrom`, `bragg_half_width_rad`, `structure_factor_magnitude`, `normalized_weight`, `ledger`, and the structure/calculation/weighting IDs.
- Later tasks call `recipe.calculation_id`, `recipe.weighting_id`, and `evidence.evidence_id` without reading YAML directly.

- [ ] **Step 1: Write failing recipe and immutability tests**

```python
def test_tracked_direct_recipe_has_exact_first_series_policy() -> None:
    recipe = load_direct_reflector_recipe(
        Path("recipes/reflectors/ice-ih-art-bands.yml")
    )
    assert recipe.energy_kev == 20.0
    assert recipe.min_dspacing_angstrom == 0.7
    assert recipe.scattering_params == "xtables"
    assert recipe.candidate_relative_factor == 0.03
    assert recipe.weight_exponent == 2.0
    assert recipe.eligibility_min_weight == 0.08
    assert recipe.calculation_id.startswith("reflector-calculation-")
    assert recipe.weighting_id.startswith("reflector-weighting-")


def test_owned_evidence_rejects_inconsistent_or_writeable_channels() -> None:
    evidence = DirectReflectorEvidence(
        source_structure_id="COD-test",
        source_structure_sha256="a" * 64,
        calculation_id="reflector-calculation-test",
        weighting_id="reflector-weighting-test",
        hkl=np.array([[1, 0, 0]], dtype=np.int32),
        normal_crystal=np.array([[1.0, 0.0, 0.0]]),
        dspacing_angstrom=np.array([2.0]),
        bragg_half_width_rad=np.array([0.01]),
        structure_factor_magnitude=np.array([10.0]),
        normalized_weight=np.array([1.0]),
        ledger={"simulation_count": 0},
    )
    assert not evidence.normal_crystal.flags.writeable
    assert evidence.evidence_id.startswith("reflector-evidence-")
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run: `uv run pytest tests/unit/test_reflector_evidence.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: kikuchi_lab.kinematical.reflector_evidence`.

- [ ] **Step 3: Implement the strict contracts and loader**

Use exact YAML keys and path-neutral identities:

```python
@dataclass(frozen=True)
class DirectReflectorRecipe:
    schema_version: int
    name: str
    source_record: str
    energy_kev: float
    min_dspacing_angstrom: float
    scattering_params: str
    candidate_relative_factor: float
    weight_exponent: float
    eligibility_min_weight: float

    @property
    def calculation_id(self) -> str:
        return stable_id("reflector-calculation", {
            "energy_kev": self.energy_kev,
            "min_dspacing_angstrom": self.min_dspacing_angstrom,
            "scattering_params": self.scattering_params,
            "candidate_relative_factor": self.candidate_relative_factor,
        })

    @property
    def weighting_id(self) -> str:
        return stable_id("reflector-weighting", {
            "weight_exponent": self.weight_exponent,
            "eligibility_min_weight": self.eligibility_min_weight,
        })


@dataclass(frozen=True, eq=False)
class DirectReflectorEvidence:
    source_structure_id: str
    source_structure_sha256: str
    calculation_id: str
    weighting_id: str
    hkl: np.ndarray
    normal_crystal: np.ndarray
    dspacing_angstrom: np.ndarray
    bragg_half_width_rad: np.ndarray
    structure_factor_magnitude: np.ndarray
    normalized_weight: np.ndarray
    ledger: Mapping[str, object]

    @property
    def evidence_id(self) -> str:
        return stable_id("reflector-evidence", self.identity_dict())
```

The loader must reject booleans as numbers, non-finite values, path escapes, extra or missing keys, and any first-series value that differs from the Global Constraints. Array construction must copy into immutable little-endian buffers and validate exact `(N, 3)`/`(N,)` shapes, finite values, unit normals, positive d-spacings, positive strengths, weights in `[0, 1]`, unique canonical HKLs, and a 64-hex structure checksum.

- [ ] **Step 4: Add the two initial recipes**

Both files use this exact content except for `name` and `source_record`:

```yaml
schema_version: 1
name: ice-ih-direct-art-reflectors
source_record: ../../phases/ice-ih/source.yml
energy_kev: 20.0
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  candidate_relative_factor: 0.03
art_weight:
  exponent: 2.0
  eligibility_min_weight: 0.08
```

Forsterite uses `name: forsterite-direct-art-reflectors` and `../../phases/forsterite/source.yml`.

- [ ] **Step 5: Run narrow tests and lint**

Run: `uv run pytest tests/unit/test_reflector_evidence.py -q && uv run ruff check src/kikuchi_lab/kinematical/reflector_evidence.py tests/unit/test_reflector_evidence.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/kinematical/reflector_evidence.py src/kikuchi_lab/kinematical/__init__.py tests/unit/test_reflector_evidence.py recipes/reflectors/ice-ih-art-bands.yml recipes/reflectors/forsterite-art-bands.yml
git commit -m "feat: define direct reflector evidence"
```

---

### Task 2: Extract the no-master reflector calculation

**Tracker:** KIKU-T032

**Files:**
- Modify: `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`
- Modify: `src/kikuchi_lab/kinematical/reflector_evidence.py`
- Create: `tests/adapters/test_direct_reflector_evidence.py`

**Interfaces:**
- Consumes: `DirectReflectorRecipe` and verified `StructureRecord`.
- Produces: `build_direct_reflector_evidence(record, recipe) -> DirectReflectorEvidence`.
- Preserves: `_enumerate_reflectors`, `_select_reflectors`, and `simulate_kinematical_arrays` behavior for existing callers.

- [ ] **Step 1: Write failing no-master and physics-channel tests**

```python
def test_direct_evidence_never_constructs_a_master(monkeypatch) -> None:
    import kikuchi_lab.kinematical.kikuchipy_adapter as adapter
    monkeypatch.setattr(
        adapter,
        "KikuchiPatternSimulator",
        lambda *_args, **_kwargs: pytest.fail("master simulator constructed"),
    )
    record = load_structure_record("phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe("recipes/reflectors/ice-ih-art-bands.yml")
    evidence = adapter.build_direct_reflector_evidence(record, recipe)
    assert evidence.ledger["simulation_count"] == 0
    assert evidence.hkl.shape[0] >= 11


def test_direct_evidence_preserves_reflector_physics() -> None:
    record = load_structure_record("phases/forsterite/source.yml")
    recipe = load_direct_reflector_recipe("recipes/reflectors/forsterite-art-bands.yml")
    evidence = build_direct_reflector_evidence(record, recipe)
    assert np.all(evidence.dspacing_angstrom > 0)
    assert np.all(evidence.bragg_half_width_rad > 0)
    assert np.max(evidence.normalized_weight) == pytest.approx(1.0)
    np.testing.assert_allclose(
        np.linalg.norm(evidence.normal_crystal, axis=1), 1.0, atol=1e-12
    )
```

- [ ] **Step 2: Run the tests and verify the missing-function failure**

Run: `uv run pytest tests/adapters/test_direct_reflector_evidence.py -q`

Expected: FAIL because `build_direct_reflector_evidence` is not defined.

- [ ] **Step 3: Implement pre-master calculation and axial collapse**

```python
def build_direct_reflector_evidence(
    record: StructureRecord,
    recipe: DirectReflectorRecipe,
) -> DirectReflectorEvidence:
    verify_structure(record)
    phase = _phase_from_record(record)
    enumerated = _enumerate_reflectors(phase, recipe)
    selected = _select_reflectors(
        enumerated,
        recipe.candidate_relative_factor,
        recipe.energy_kev,
    )
    return own_direct_reflector_evidence(
        selected,
        source_structure_id=record.identifier,
        source_structure_sha256=record.sha256,
        calculation_id=recipe.calculation_id,
        weighting_id=recipe.weighting_id,
        weight_exponent=recipe.weight_exponent,
        eligibility_min_weight=recipe.eligibility_min_weight,
        counts={"enumerated": enumerated.size, "selected_signed": selected.size},
    )
```

`own_direct_reflector_evidence` must canonicalize exact signed pairs with the same first-nonzero-positive HKL rule as `collapse_antipodal_reflectors`, retain one d-spacing/angle/strength after pairwise equality checks, sort by canonical HKL before weighting, and compute weights from the global selected maximum. The ledger must record units, formulas, counts, package versions, `eligibility_min_weight`, `simulation_count: 0`, and `orientation_dependency: none`.

- [ ] **Step 4: Prove parity with the current pre-master private path**

Add a test that builds current selected upstream reflectors using `_enumerate_reflectors` and `_select_reflectors`, canonicalizes them independently, and compares exact HKLs plus normals/d-spacing/theta/strength at `rtol=1e-12`, `atol=1e-12` for Ice and forsterite.

- [ ] **Step 5: Run adapter regression tests**

Run: `uv run pytest tests/adapters/test_direct_reflector_evidence.py tests/adapters/test_kikuchipy_kinematical.py tests/adapters/test_ice_ih_kinematical.py -q`

Expected: PASS with the existing master/detector tests unchanged.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/kinematical/kikuchipy_adapter.py src/kikuchi_lab/kinematical/reflector_evidence.py tests/adapters/test_direct_reflector_evidence.py
git commit -m "feat: calculate reflector evidence without masters"
```

---

### Task 3: Decouple art catalogs from raster presentation state

**Tracker:** KIKU-T032

**Files:**
- Modify: `src/kikuchi_lab/art_products/catalog.py`
- Modify: `src/kikuchi_lab/art_products/__init__.py`
- Modify: `tests/unit/test_art_band_catalog.py`
- Create: `tests/scientific/test_direct_art_band_catalog.py`

**Interfaces:**
- Consumes: `DirectReflectorEvidence`.
- Produces: `build_art_band_catalog_from_evidence(evidence) -> ArtBandCatalog`.
- Preserves: the existing
  `build_art_band_catalog(source, source_structure_id,
  source_structure_sha256, source_recipe_id, presentation_recipe_id,
  eligibility_min_weight)` signature and existing Ice catalog snapshot tests.

- [ ] **Step 1: Write a failing direct-catalog equivalence test**

```python
def test_direct_catalog_uses_owned_evidence_without_presentation_source() -> None:
    record = load_structure_record("phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe("recipes/reflectors/ice-ih-art-bands.yml")
    evidence = build_direct_reflector_evidence(record, recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    assert catalog.source_structure_id == record.identifier
    assert catalog.source_structure_sha256 == record.sha256
    assert catalog.source_recipe_id == recipe.calculation_id
    assert catalog.presentation_recipe_id == recipe.weighting_id
    assert catalog.eligibility_min_weight == 0.08
    assert sum(member.tattoo_eligible for member in catalog.members) >= 11
```

- [ ] **Step 2: Run the test and verify the missing-function failure**

Run: `uv run pytest tests/scientific/test_direct_art_band_catalog.py -q`

Expected: FAIL because `build_art_band_catalog_from_evidence` is absent.

- [ ] **Step 3: Extract one array-led internal builder**

```python
def build_art_band_catalog_from_evidence(
    evidence: DirectReflectorEvidence,
) -> ArtBandCatalog:
    return _build_art_band_catalog_arrays(
        hkls=evidence.hkl,
        normals=evidence.normal_crystal,
        half_widths=evidence.bragg_half_width_rad,
        strengths=evidence.structure_factor_magnitude,
        weights=evidence.normalized_weight,
        source_structure_id=evidence.source_structure_id,
        source_structure_sha256=evidence.source_structure_sha256,
        source_recipe_id=evidence.calculation_id,
        presentation_recipe_id=evidence.weighting_id,
        eligibility_min_weight=float(evidence.ledger["eligibility_min_weight"]),
    )
```

Move the current validation, member construction, sorting, eligibility, and cohort assignment into `_build_art_band_catalog_arrays`. Keep the legacy function as a thin adapter that passes its existing `PresentationSource` arrays and IDs. Do not alter `ArtBandMember.intrinsic_dict`, member IDs, schema version, serialization keys, or legacy ordering.

- [ ] **Step 4: Run direct and legacy snapshot tests**

Run: `uv run pytest tests/scientific/test_direct_art_band_catalog.py tests/unit/test_art_band_catalog.py tests/scientific/test_art_band_catalog_scientific.py -q`

Expected: PASS, including byte-stable legacy snapshots.

- [ ] **Step 5: Commit**

```bash
git add src/kikuchi_lab/art_products/catalog.py src/kikuchi_lab/art_products/__init__.py tests/unit/test_art_band_catalog.py tests/scientific/test_direct_art_band_catalog.py
git commit -m "refactor: build art catalogs from reflector evidence"
```

---

### Task 4: Publish zero-master direct catalog bundles

**Tracker:** KIKU-T032

**Files:**
- Create: `src/kikuchi_lab/art_products/direct_catalog_bundle.py`
- Create: `src/kikuchi_lab/workflows/direct_art_catalog.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_direct_catalog_bundle.py`
- Create: `tests/integration/test_direct_art_catalog.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Produces:
  `write_direct_art_catalog_bundle(output_root, source, recipe, evidence,
  catalog)`, `DirectArtCatalogResult`, and
  `build_direct_art_catalog(recipe_path, output_root)`.
- CLI: `kikuchi-lab build-direct-art-catalog --recipe PATH --output ROOT`.
- Bundle inventory: `art-band-catalog.json`, `direct-reflector-recipe.json`, `reflector-evidence.npz`, `reflector-evidence-ledger.json`, `catalog-ledger.json`, `scientific-claim.txt`, and `manifest.json`.

- [ ] **Step 1: Write failing atomic-bundle and CLI tests**

```python
def test_direct_catalog_workflow_reports_zero_simulations(capsys, tmp_path) -> None:
    result = build_direct_art_catalog(
        recipe_path="recipes/reflectors/ice-ih-art-bands.yml",
        output_root=tmp_path,
    )
    assert (result.path / "art-band-catalog.json").is_file()
    assert (result.path / "reflector-evidence.npz").is_file()
    assert "simulation_count=0" in capsys.readouterr().err


def test_direct_catalog_cli_returns_content_ids(tmp_path, capsys) -> None:
    status = main([
        "build-direct-art-catalog",
        "--recipe", "recipes/reflectors/forsterite-art-bands.yml",
        "--output", str(tmp_path),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["catalog_id"].startswith("art-band-catalog-")
```

- [ ] **Step 2: Run tests and verify missing workflow/CLI failures**

Run: `uv run pytest tests/unit/test_direct_catalog_bundle.py tests/integration/test_direct_art_catalog.py tests/unit/test_cli.py -q`

Expected: FAIL on missing imports and unknown command.

- [ ] **Step 3: Implement strict preflight and atomic publication**

```python
def build_direct_art_catalog(*, recipe_path: str | Path, output_root: str | Path) -> DirectArtCatalogResult:
    started = time.monotonic()
    recipe_file = Path(recipe_path).resolve()
    recipe = load_direct_reflector_recipe(recipe_file)
    source_path = (recipe_file.parent / recipe.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    print(
        "direct-art-catalog finite-work simulation_count=0 "
        f"phase={source.name} min_dspacing_angstrom={recipe.min_dspacing_angstrom}",
        file=sys.stderr,
        flush=True,
    )
    evidence = build_direct_reflector_evidence(source, recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    bundle = write_direct_art_catalog_bundle(
        output_root,
        source=source,
        recipe=recipe,
        evidence=evidence,
        catalog=catalog,
    )
    return DirectArtCatalogResult.from_bundle(bundle, catalog, evidence, started)
```

Preflight must recompute all stable IDs, verify source checksum and evidence/catalog linkage, validate at least 11 tattoo-eligible members, use the existing no-replace partial-directory publication helpers, and exclude local paths/timestamps from run identity. NPZ keys and dtypes must be exact and sorted.

- [ ] **Step 4: Add the CLI branch and error behavior**

The CLI catches `BundleExistsError`, `PartialBundleError`, `OSError`, `ValueError`, and `RuntimeError`, writes failures to stderr, returns 1, and emits sorted JSON containing `run_id`, `path`, `catalog_id`, `evidence_id`, `member_count`, `eligible_member_count`, `simulation_count`, and `manifest_sha256` on success.

- [ ] **Step 5: Run narrow integration and regression tests**

Run: `uv run pytest tests/unit/test_direct_catalog_bundle.py tests/integration/test_direct_art_catalog.py tests/unit/test_cli.py tests/integration/test_ice_art_catalog.py -q`

Expected: PASS with legacy Ice catalog behavior unchanged.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/art_products/direct_catalog_bundle.py src/kikuchi_lab/workflows/direct_art_catalog.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_direct_catalog_bundle.py tests/integration/test_direct_art_catalog.py tests/unit/test_cli.py
git commit -m "feat: publish direct reflector catalogs"
```

---

### Task 5: Add killable one-smoke reflector parity

**Tracker:** KIKU-T032

**Files:**
- Create: `src/kikuchi_lab/kinematical/reflector_parity.py`
- Create: `src/kikuchi_lab/workflows/reflector_parity.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_reflector_parity.py`
- Create: `tests/integration/test_reflector_parity.py`
- Create: `tests/fixtures/reflector_parity_hang.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Produces: `ReflectorParityReport` and `run_reflector_parity(recipe_path, output_root, timeout_seconds=90)`.
- Worker writes one JSON response through a temporary path; parent is the only publisher.
- CLI: `kikuchi-lab validate-reflector-parity --recipe PATH --output ROOT --timeout-seconds 90`.

- [ ] **Step 1: Write failing comparator and timeout tests**

```python
def test_parity_comparator_requires_exact_hkls_and_tight_numeric_match() -> None:
    report = compare_reflector_evidence(direct, simulator_owned)
    assert report.passed
    assert report.max_normal_abs_error <= 1e-12
    assert report.max_dspacing_abs_error <= 1e-12
    assert report.max_theta_abs_error <= 1e-12
    assert report.max_strength_abs_error <= 1e-10


def test_parity_parent_terminates_worker_at_deadline(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        parity_workflow,
        "_WORKER_MODULE",
        "tests.fixtures.reflector_parity_hang",
    )
    with pytest.raises(ReflectorParityTimeoutError, match="0.05 seconds"):
        parity_workflow.run_reflector_parity(
            recipe_path="recipes/reflectors/ice-ih-art-bands.yml",
            output_root=tmp_path,
            timeout_seconds=0.05,
        )
    assert not list(tmp_path.glob("reflector-parity-run-*"))
```

- [ ] **Step 2: Run tests and verify missing-module failures**

Run: `uv run pytest tests/unit/test_reflector_parity.py tests/integration/test_reflector_parity.py -q`

Expected: FAIL on missing parity modules.

Add the deterministic hang fixture used only by the injected timeout test:

```python
from __future__ import annotations

import time


while True:
    time.sleep(0.01)
```

- [ ] **Step 3: Implement the worker's single bounded master**

```python
def _worker(recipe_path: Path, response_path: Path) -> None:
    recipe = load_direct_reflector_recipe(recipe_path)
    source = load_structure_record((recipe_path.parent / recipe.source_record).resolve())
    direct = build_direct_reflector_evidence(source, recipe)
    phase = _phase_from_record(source)
    selected = _select_reflectors(
        _enumerate_reflectors(phase, recipe),
        recipe.candidate_relative_factor,
        recipe.energy_kev,
    )
    simulator = KikuchiPatternSimulator(selected)
    master = _calculate_master_pattern_single_worker(
        simulator,
        half_size=32,
        hemisphere="both",
        scaling="square",
    )
    simulator_owned = own_direct_reflector_evidence(
        simulator.reflectors,
        source_structure_id=source.identifier,
        source_structure_sha256=source.sha256,
        calculation_id=recipe.calculation_id,
        weighting_id=recipe.weighting_id,
        weight_exponent=recipe.weight_exponent,
        eligibility_min_weight=recipe.eligibility_min_weight,
        counts={"selected_signed": simulator.reflectors.size},
    )
    report = compare_reflector_evidence(direct, simulator_owned).with_master(master.data)
    response_path.write_text(report.to_json(), encoding="utf-8")
```

The parent launches
`sys.executable -m kikuchi_lab.workflows.reflector_parity --worker RECIPE_PATH RESPONSE_PATH`
with a new process group, calls `communicate(timeout=timeout_seconds)`,
terminates then kills the process group if needed, retains stdout/stderr on
failure, and publishes only a passed report. The report records
`simulation_count: 1`, `half_size: 32`, shape `[2, 65, 65]`, master-array
SHA-256, reflector counts, maximum residuals, package versions, elapsed time
outside identity, and no retry.

- [ ] **Step 4: Add CLI validation**

Reject booleans, non-integers, values outside `1..90`, and any timeout other than 90 for the version-controlled acceptance invocation. Unit tests may inject shorter timeouts directly into the workflow.

- [ ] **Step 5: Run parity tests and existing adapter smoke tests**

Run: `uv run pytest tests/unit/test_reflector_parity.py tests/integration/test_reflector_parity.py tests/adapters/test_kikuchipy_kinematical.py tests/unit/test_cli.py -q`

Expected: PASS; the timeout test completes in under one second.

- [ ] **Step 6: Mark KIKU-T032 done only after its criteria pass and commit**

Update `docs/work/KIKU-T032.md`, add the plan link, check only satisfied criteria, set `status: done`, and run `uv run python scripts/validate_work_items.py`.

```bash
git add src/kikuchi_lab/kinematical/reflector_parity.py src/kikuchi_lab/workflows/reflector_parity.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_reflector_parity.py tests/integration/test_reflector_parity.py tests/fixtures/reflector_parity_hang.py tests/unit/test_cli.py docs/work/KIKU-T032.md
git commit -m "feat: validate reflector parity in bounded workers"
```

---

### Task 6: Onboard ambient alpha-quartz from COD 9012600

**Tracker:** KIKU-T033

**Files:**
- Create: `phases/quartz/COD-9012600.cif`
- Create: `phases/quartz/source.yml`
- Create: `recipes/reflectors/quartz-art-bands.yml`
- Modify: `reference/catalog/crystallography-open-database.yml`
- Create: `tests/adapters/test_quartz_source.py`

**Interfaces:**
- Produces: verified source identifier `COD-9012600` and a direct recipe using the shared first-series policy.
- Source: `https://www.crystallography.net/cod/9012600.cif`; page: `https://www.crystallography.net/cod/9012600.html`; raw SHA-256 `29176db9b50e42972646a43bd171e4cff1d6bc47cc2f93e265ff809ecadd85ef`.

- [ ] **Step 1: Write the failing source and phase-adapter test**

```python
def test_quartz_source_is_ambient_right_handed_alpha_quartz() -> None:
    record = load_structure_record("phases/quartz/source.yml")
    verified = verify_structure(record)
    assert verified.parsed_formula == "SiO2"
    assert verified.parsed_space_group_number == 152
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (4.914, 4.914, 5.406, 90.0, 90.0, 120.0)
    )
    assert verified.site_labels == ("Si1", "O1")
    assert record.setting == "P 31 2 1"
    assert record.simulation_setting["handedness"] == "right-handed P 31 2 1"


def test_quartz_direct_catalog_has_eleven_eligible_bands() -> None:
    result = build_direct_art_catalog(
        recipe_path="recipes/reflectors/quartz-art-bands.yml",
        output_root=tmp_path,
    )
    assert result.eligible_member_count >= 11
```

- [ ] **Step 2: Run the test and verify missing-file failure**

Run: `uv run pytest tests/adapters/test_quartz_source.py -q`

Expected: FAIL because the quartz source record is absent.

- [ ] **Step 3: Add exact COD payload and source record**

Verify the exact current COD payload before adding the inspected payload with
`apply_patch`:

```bash
curl -fsSL https://www.crystallography.net/cod/9012600.cif | shasum -a 256
shasum -a 256 phases/quartz/COD-9012600.cif
```

Both commands must report
`29176db9b50e42972646a43bd171e4cff1d6bc47cc2f93e265ff809ecadd85ef`.

The YAML record uses formula `SiO2`, SG 152, lattice above, sites `Si1 [0.46990, 0, 1/3], Uiso 0.00646` and `O1 [0.41300, 0.26680, 0.21400], Uiso 0.01089`, full occupancy, identity setting, multiplicities `[3, 6]`, COD CC0, retrieval date `2026-07-16`, and the Hazen/Finger/Hemley/Mao 1989 citation.

- [ ] **Step 4: Add recipe and COD catalog entry**

Add this exact recipe and register the source URL, page URL, digest, CC0
license, publication year 1989, right-handed setting, and ambient pressure
1 bar in the reference catalog:

```yaml
schema_version: 1
name: quartz-direct-art-reflectors
source_record: ../../phases/quartz/source.yml
energy_kev: 20.0
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  candidate_relative_factor: 0.03
art_weight:
  exponent: 2.0
  eligibility_min_weight: 0.08
```

- [ ] **Step 5: Run source, direct-catalog, and reflection tests**

Run: `uv run pytest tests/adapters/test_quartz_source.py tests/integration/test_direct_art_catalog.py -q`

Expected: PASS with at least 11 eligible bands; otherwise stop and report the common-policy failure without lowering thresholds.

- [ ] **Step 6: Commit**

```bash
git add phases/quartz recipes/reflectors/quartz-art-bands.yml reference/catalog/crystallography-open-database.yml tests/adapters/test_quartz_source.py
git commit -m "feat: onboard alpha quartz reflectors"
```

---

### Task 7: Onboard zircon through an explicit isotropic-U derivative

**Tracker:** KIKU-T033

**Files:**
- Create: `phases/zircon/COD-9000684-original.cif`
- Create: `phases/zircon/COD-9000684-isotropic-u.cif`
- Create: `phases/zircon/source.yml`
- Create: `recipes/reflectors/zircon-art-bands.yml`
- Modify: `reference/catalog/crystallography-open-database.yml`
- Create: `tests/adapters/test_zircon_source.py`

**Interfaces:**
- Produces: verified derivative identifier `COD-9000684-isotropic-U` and a shared-policy direct recipe.
- Source: `https://www.crystallography.net/cod/9000684.cif`; raw SHA-256 `e461a480345cbb60af43cff99a8f6783cf8a3c41530fcb686c506de97b79c44f`.

- [ ] **Step 1: Write failing derivative-provenance and structure tests**

```python
def test_zircon_derivative_records_exact_anisotropic_to_isotropic_policy() -> None:
    record = load_structure_record("phases/zircon/source.yml")
    verified = verify_structure(record)
    assert verified.parsed_formula == "ZrSiO4"
    assert verified.parsed_space_group_number == 141
    assert record.setting == "I 41/a m d :2"
    assert record.simulation_setting["derived_from_sha256"] == (
        "e461a480345cbb60af43cff99a8f6783cf8a3c41530fcb686c506de97b79c44f"
    )
    assert record.simulation_setting["u_iso_derivation"] == (
        "U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal tetragonal axes"
    )
    assert verified.site_u_iso_angstrom_sq == pytest.approx(
        (0.003493333333333333, 0.003933333333333333, 0.006363333333333333)
    )
```

- [ ] **Step 2: Run the test and verify missing-file failure**

Run: `uv run pytest tests/adapters/test_zircon_source.py -q`

Expected: FAIL because zircon files are absent.

- [ ] **Step 3: Retain the original and construct the deterministic derivative**

Verify the remote original, add the inspected original with `apply_patch`, and
verify the tracked copy:

```bash
curl -fsSL https://www.crystallography.net/cod/9000684.cif | shasum -a 256
shasum -a 256 phases/zircon/COD-9000684-original.cif
```

Both commands must report
`e461a480345cbb60af43cff99a8f6783cf8a3c41530fcb686c506de97b79c44f`.
The derivative must preserve the COD header, citation, SG 141, lattice
`(6.6042, 6.6042, 5.9796, 90, 90, 90)`, symops, and coordinates. It replaces
the anisotropic loop with this explicit site loop:

```cif
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_U_iso_or_equiv
Zr 0.00000 0.75000 0.12500 1.0 0.003493333333333333
Si 0.00000 0.25000 0.37500 1.0 0.003933333333333333
O  0.00000 0.06600 0.19510 1.0 0.006363333333333333
```

The derivative header records the original COD ID, original SHA-256, formula used for each Uiso, and that no coordinates, occupancies, cell values, or symmetry operations changed. Compute the derivative SHA-256 and place that exact digest in `source.yml`; the test recomputes it rather than accepting a hard-coded unchecked value.

- [ ] **Step 4: Add source record, recipe, and catalog provenance**

The source record uses formula `ZrSiO4`, identity setting, multiplicities
`[4, 4, 16]`, source URL/page, COD CC0, retrieval date `2026-07-16`, and
Hazen & Finger 1979 citation. The catalog entry records both original and
derivative digests and the isotropic-U equation. Add this exact direct recipe:

```yaml
schema_version: 1
name: zircon-direct-art-reflectors
source_record: ../../phases/zircon/source.yml
energy_kev: 20.0
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  candidate_relative_factor: 0.03
art_weight:
  exponent: 2.0
  eligibility_min_weight: 0.08
```

- [ ] **Step 5: Run source and direct-catalog tests**

Run: `uv run pytest tests/adapters/test_zircon_source.py tests/integration/test_direct_art_catalog.py -q`

Expected: PASS with at least 11 eligible bands; otherwise stop without threshold relaxation.

- [ ] **Step 6: Commit**

```bash
git add phases/zircon recipes/reflectors/zircon-art-bands.yml reference/catalog/crystallography-open-database.yml tests/adapters/test_zircon_source.py
git commit -m "feat: onboard zircon reflectors"
```

---

### Task 8: Onboard room-temperature synthetic titanite from COD 9000509

**Tracker:** KIKU-T033

**Files:**
- Create: `phases/titanite/COD-9000509.cif`
- Create: `phases/titanite/source.yml`
- Create: `recipes/reflectors/titanite-art-bands.yml`
- Modify: `reference/catalog/crystallography-open-database.yml`
- Create: `tests/adapters/test_titanite_source.py`

**Interfaces:**
- Produces: verified source identifier `COD-9000509` and a shared-policy direct recipe.
- Source: `https://www.crystallography.net/cod/9000509.cif`; raw SHA-256 `ed45563f6621488f165373f2847c65acef197744322e0937d985518a3437be42`.

- [ ] **Step 1: Write failing room-temperature P21/a structure tests**

```python
def test_titanite_source_is_room_temperature_synthetic_p21a() -> None:
    record = load_structure_record("phases/titanite/source.yml")
    verified = verify_structure(record)
    assert verified.parsed_formula == "CaTiSiO5"
    assert verified.parsed_space_group_number == 14
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (7.068, 8.714, 6.562, 90.0, 113.82, 90.0)
    )
    assert verified.site_labels == ("Ca", "Ti", "Si", "O1", "O2", "O3", "O4", "O5")
    assert record.setting == "P 1 21/a 1"
    assert record.simulation_setting["temperature_kelvin"] == 298.15
```

- [ ] **Step 2: Run the test and verify missing-file failure**

Run: `uv run pytest tests/adapters/test_titanite_source.py -q`

Expected: FAIL because titanite files are absent.

- [ ] **Step 3: Add exact COD source and record**

Verify the remote payload, add the inspected payload with `apply_patch`, and
verify the tracked copy:

```bash
curl -fsSL https://www.crystallography.net/cod/9000509.cif | shasum -a 256
shasum -a 256 phases/titanite/COD-9000509.cif
```

Both commands must report
`ed45563f6621488f165373f2847c65acef197744322e0937d985518a3437be42`.
Record all eight CIF sites and Uiso values exactly, full occupancy, identity
setting, multiplicities `[4, 4, 4, 4, 4, 4, 4, 4]`, COD CC0, retrieval date
`2026-07-16`, and Taylor & Brown 1976 citation. State explicitly that this is
the 25 C synthetic P21/a structure, not the high-temperature A2/a polymorph and
not a compositionally substituted natural titanite.

- [ ] **Step 4: Add direct recipe and catalog entry**

Add this exact recipe and register source/page URLs, digest, temperature,
setting, license, and publication:

```yaml
schema_version: 1
name: titanite-direct-art-reflectors
source_record: ../../phases/titanite/source.yml
energy_kev: 20.0
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  candidate_relative_factor: 0.03
art_weight:
  exponent: 2.0
  eligibility_min_weight: 0.08
```

- [ ] **Step 5: Run source and direct-catalog tests**

Run: `uv run pytest tests/adapters/test_titanite_source.py tests/integration/test_direct_art_catalog.py -q`

Expected: PASS with at least 11 eligible bands; otherwise stop without threshold relaxation.

- [ ] **Step 6: Mark KIKU-T033 done only if all three sources pass, then commit**

Update the tracker with exact source IDs and checked criteria, run `uv run python scripts/validate_work_items.py`, then commit:

```bash
git add phases/titanite recipes/reflectors/titanite-art-bands.yml reference/catalog/crystallography-open-database.yml tests/adapters/test_titanite_source.py docs/work/KIKU-T033.md
git commit -m "feat: onboard titanite reflectors"
```

---

### Task 9: Define a phase-general hemisphere composition and treatment recipe

**Tracker:** KIKU-T034

**Files:**
- Create: `src/kikuchi_lab/art_products/hemisphere_recipe.py`
- Create: `recipes/art/five-phase-hemisphere-series.yml`
- Create: `tests/unit/test_hemisphere_recipe.py`
- Modify: `src/kikuchi_lab/art_products/__init__.py`

**Interfaces:**
- Produces: `HemisphereSeriesRecipe`, `HemisphereCompositionRecipe`, `HemisphereTreatment`, and `load_hemisphere_series_recipe(path)`.
- `composition_for(phase_slug)` exposes the same structural attributes currently consumed by tattoo selection.
- Treatments are exactly `standard: 1.0` and `wide: 1.15`; treatment identity is separate from selection identity.

- [ ] **Step 1: Write failing strict-schema and orientation-identity tests**

```python
def test_series_recipe_is_phase_general_and_orientation_is_data() -> None:
    recipe = load_hemisphere_series_recipe(
        "recipes/art/five-phase-hemisphere-series.yml"
    )
    assert recipe.phase_order == (
        "ice-ih", "forsterite", "quartz", "zircon", "titanite"
    )
    assert recipe.orientation.euler_bunge_deg == (17.0, 31.0, 43.0)
    assert recipe.orientation.frame == "crystal_to_sample"
    assert recipe.treatments["standard"].arc_width_scale == 1.0
    assert recipe.treatments["wide"].arc_width_scale == 1.15


def test_orientation_changes_composition_not_catalog_recipe_identity(tmp_path) -> None:
    recipe = load_hemisphere_series_recipe(TRACKED_RECIPE)
    changed = replace(recipe, orientation=Orientation((1.0, 2.0, 3.0), "crystal_to_sample"))
    assert changed.series_id != recipe.series_id
    assert changed.reflector_recipes == recipe.reflector_recipes
```

- [ ] **Step 2: Run tests and verify missing-module failure**

Run: `uv run pytest tests/unit/test_hemisphere_recipe.py -q`

Expected: FAIL during collection.

- [ ] **Step 3: Implement immutable recipe types and exact validation**

```python
@dataclass(frozen=True)
class HemisphereTreatment:
    name: Literal["standard", "wide"]
    arc_width_scale: float


@dataclass(frozen=True)
class HemisphereCompositionRecipe:
    phase_slug: str
    orientation: Orientation
    artboard_size_mm: float
    path_allocation: Mapping[str, int]
    stroke_widths_mm: Mapping[str, tuple[float, ...]]
    great_circle_samples: int
    crop_radius: float
    redundancy_threshold_deg: float
    score_weights: Mapping[str, float]
    coverage_sectors: int
    zone_interior_margin_deg: float
    projection_boundary: Mapping[str, object]
    include_nodes: bool
    spatial_filter: str
    primary_palette: Mapping[str, str]

    @property
    def recipe_id(self) -> str:
        return stable_id("hemisphere-composition", self.to_dict())
```

Validate every Global Constraint exactly, relative recipe paths, unique phase slugs, phase order, treatment names/scales, and the shared score weights. Reject any phase-specific orientation or width override in schema version 1.

- [ ] **Step 4: Add the tracked series YAML**

Use this exact version-1 payload:

```yaml
schema_version: 1
name: five-phase-hemisphere-series
phase_order: [ice-ih, forsterite, quartz, zircon, titanite]
reflector_recipes:
  ice-ih: ../reflectors/ice-ih-art-bands.yml
  forsterite: ../reflectors/forsterite-art-bands.yml
  quartz: ../reflectors/quartz-art-bands.yml
  zircon: ../reflectors/zircon-art-bands.yml
  titanite: ../reflectors/titanite-art-bands.yml
reviewed_standard_reference: ice-ih
orientation:
  euler_bunge_deg: [17.0, 31.0, 43.0]
  frame: crystal_to_sample
path_allocation:
  dominant: 4
  secondary: 4
  fine: 3
stroke_widths_mm:
  dominant: [4.8, 4.2, 3.6, 3.1]
  secondary: [2.5, 2.2, 1.9, 1.6]
  fine: [1.2, 1.0, 0.8]
great_circle_samples: 721
crop_radius: 0.90
redundancy_threshold_deg: 4.0
score_weights:
  strength: 0.40
  angular_width: 0.15
  nonredundancy: 0.20
  coverage: 0.15
  zone_relationship: 0.10
coverage_sectors: 6
zone_interior_margin_deg: 6.0
projection_boundary:
  enabled: true
  role: stereographic_hemisphere_boundary
  scientific_claim: noncrystallographic_projection_primitive
  outer_diameter_mm: 132.0
  stroke_width_mm: 2.2
  ink: "#000000"
artboard_size_mm: 145.0
include_nodes: false
spatial_filter: none
primary_palette:
  ink: "#000000"
  substrate: skin
treatments:
  standard:
    arc_width_scale: 1.0
  wide:
    arc_width_scale: 1.15
```

- [ ] **Step 5: Run tests and lint**

Run: `uv run pytest tests/unit/test_hemisphere_recipe.py -q && uv run ruff check src/kikuchi_lab/art_products/hemisphere_recipe.py tests/unit/test_hemisphere_recipe.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/art_products/hemisphere_recipe.py src/kikuchi_lab/art_products/__init__.py recipes/art/five-phase-hemisphere-series.yml tests/unit/test_hemisphere_recipe.py
git commit -m "feat: define phase hemisphere art recipes"
```

---

### Task 10: Reuse selection and vector rendering for standard/wide phase pairs

**Tracker:** KIKU-T034

**Files:**
- Modify: `src/kikuchi_lab/art_products/tattoo_selection.py`
- Modify: `src/kikuchi_lab/art_products/tattoo_vector.py`
- Modify: `src/kikuchi_lab/art_products/tattoo_bundle.py`
- Create: `src/kikuchi_lab/art_products/hemisphere_bundle.py`
- Create: `tests/scientific/test_phase_hemisphere_selection.py`
- Create: `tests/unit/test_hemisphere_bundle.py`
- Modify: `tests/integration/test_ice_tattoo.py`

**Interfaces:**
- Consumes: `ArtBandCatalog`, `HemisphereCompositionRecipe`, one frozen `TattooSelection`, and `HemisphereTreatment`.
- Produces: `build_tattoo_geometry(selection, recipe, width_scale=1.0)`,
  `write_phase_hemisphere_bundle(output_root, phase_slug, treatment, catalog,
  recipe, selection, geometry, rendered, disclaimer)`, and
  `PhaseHemisphereBundleResult`.
- Preserves: legacy `TattooRecipe`, `render_ice_tattoo`, Ice filenames, Ice IDs, and default `width_scale=1.0` bytes.

- [ ] **Step 1: Write failing pair-invariance and legacy-byte tests**

```python
def test_standard_and_wide_share_selection_and_centerlines() -> None:
    composition = series.composition_for("forsterite")
    selection = select_tattoo_paths(catalog, composition)
    standard = build_tattoo_geometry(selection, composition, width_scale=1.0)
    wide = build_tattoo_geometry(selection, composition, width_scale=1.15)
    assert [path.member_id for path in standard.paths] == [path.member_id for path in wide.paths]
    for ordinary, widened in zip(standard.paths, wide.paths, strict=True):
        np.testing.assert_array_equal(ordinary.points_mm, widened.points_mm)
        assert widened.width_mm == pytest.approx(ordinary.width_mm * 1.15, abs=1e-12)
    assert standard.boundary == wide.boundary


def test_legacy_ice_geometry_and_render_bytes_are_unchanged() -> None:
    legacy = build_tattoo_geometry(selection, ice_recipe)
    explicit = build_tattoo_geometry(selection, ice_recipe, width_scale=1.0)
    assert legacy.geometry_id == explicit.geometry_id
    assert render_primary_tattoo(legacy) == render_primary_tattoo(explicit)
```

- [ ] **Step 2: Run tests and verify type/argument failures**

Run: `uv run pytest tests/scientific/test_phase_hemisphere_selection.py tests/unit/test_hemisphere_bundle.py tests/integration/test_ice_tattoo.py -q`

Expected: FAIL because the selection type guard rejects the generic composition and geometry lacks `width_scale`.

- [ ] **Step 3: Introduce a structural recipe protocol and width scaling**

```python
@runtime_checkable
class HemisphereSelectionRecipe(Protocol):
    orientation: Orientation
    path_allocation: Mapping[str, int]
    stroke_widths_mm: Mapping[str, tuple[float, ...]]
    great_circle_samples: int
    crop_radius: float
    redundancy_threshold_deg: float
    score_weights: Mapping[str, float]
    coverage_sectors: int
    zone_interior_margin_deg: float
    recipe_id: str


def build_tattoo_geometry(
    selection: TattooSelection,
    recipe: HemisphereSelectionRecipe,
    *,
    width_scale: float = 1.0,
) -> TattooGeometry:
    if width_scale not in (1.0, 1.15):
        raise ValueError("width_scale must be exactly 1.0 or 1.15")
```

Keep selection scoring and base-width assignment unchanged. Apply `width_scale` only when constructing `TattooPath.width_mm`. Validate wide geometry before standard publication so the selected set is never frozen if the wider envelope fails existing clearance/containment rules.

- [ ] **Step 4: Extract generic publication behind the legacy wrapper**

`write_phase_hemisphere_bundle` parameterizes phase slug, treatment name, arc scale, dynamic filenames, and run prefix while reusing the current SVG/PDF/PNG validation, stroke diagnostics, no-replace atomic publication, disclaimer, and manifest checks. `write_tattoo_bundle` remains a wrapper with the exact legacy Ice inventory and run identity. Generic bundles contain SVG, PDF, mockup PNG, stencil PNG, geometry, shared selection ledger, composition recipe, treatment recipe, catalog snapshot/reference, diagnostics, disclaimer, and manifest.

- [ ] **Step 5: Run legacy and generic rendering suites**

Run: `uv run pytest tests/scientific/test_phase_hemisphere_selection.py tests/unit/test_hemisphere_bundle.py tests/unit/test_tattoo_recipe.py tests/scientific/test_tattoo_selection.py tests/unit/test_tattoo_vector.py tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py tests/integration/test_ice_tattoo.py -q`

Expected: PASS, including the current Ice geometry ID `tattoo-geometry-55aa84c7c4d78a1b`.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/art_products/tattoo_selection.py src/kikuchi_lab/art_products/tattoo_vector.py src/kikuchi_lab/art_products/tattoo_bundle.py src/kikuchi_lab/art_products/hemisphere_bundle.py tests/scientific/test_phase_hemisphere_selection.py tests/unit/test_hemisphere_bundle.py tests/integration/test_ice_tattoo.py
git commit -m "feat: render phase hemisphere width treatments"
```

---

### Task 11: Build the parity-gated five-phase series and comparison sheet

**Tracker:** KIKU-T034

**Files:**
- Create: `src/kikuchi_lab/art_products/series_sheet.py`
- Create: `src/kikuchi_lab/workflows/phase_art_series.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_series_sheet.py`
- Create: `tests/integration/test_phase_art_series.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Produces: `render_phase_art_series(recipe_path, parity_root, ice_standard_reference, output_root) -> PhaseArtSeriesResult`.
- CLI requires `--parity-root PATH` and `--ice-standard-reference PATH`.
- Outputs: nine new bundle directories plus one content-identified series
  directory containing `comparison.png`, `comparison-ledger.json`, and
  `manifest.json`.

- [ ] **Step 1: Write failing series inventory and no-master tests**

```python
def test_series_publishes_nine_new_bundles_and_ten_review_cells(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        kikuchipy_adapter,
        "KikuchiPatternSimulator",
        lambda *_args, **_kwargs: pytest.fail("series attempted master simulation"),
    )
    result = render_phase_art_series(
        recipe_path=SERIES_RECIPE,
        parity_root=PARITY_FIXTURE_ROOT,
        ice_standard_reference=ICE_REFERENCE_FIXTURE,
        output_root=tmp_path,
    )
    assert len(result.new_bundles) == 9
    assert result.cell_order == (
        "ice-ih:standard", "ice-ih:wide",
        "forsterite:standard", "forsterite:wide",
        "quartz:standard", "quartz:wide",
        "zircon:standard", "zircon:wide",
        "titanite:standard", "titanite:wide",
    )
    assert result.simulation_count == 0
```

- [ ] **Step 2: Write the Ice reference lock test**

Load the reviewed standard's `band-selection-ledger.json` and `path-geometry.json`. The direct Ice selection must match its ordered member IDs and center-trace hashes before the wide Ice bundle is built. A mismatch raises `IceStandardReferenceMismatch` before any series output.

- [ ] **Step 3: Run tests and verify missing-workflow failures**

Run: `uv run pytest tests/unit/test_series_sheet.py tests/integration/test_phase_art_series.py tests/unit/test_cli.py -q`

Expected: FAIL on missing modules and CLI command.

- [ ] **Step 4: Implement parity gates and one-selection/two-treatment flow**

```python
for phase_slug in recipe.phase_order:
    parity = resolve_unique_passed_parity_report(
        parity_root,
        phase_slug=phase_slug,
        expected_recipe=recipe.reflector_recipe(phase_slug),
    )
    direct = build_direct_art_catalog_in_memory(recipe.reflector_recipe(phase_slug))
    parity.require_matches(direct.evidence)
    composition = recipe.composition_for(phase_slug)
    selection = select_tattoo_paths(direct.catalog, composition)
    wide = build_tattoo_geometry(selection, composition, width_scale=1.15)
    standard = build_tattoo_geometry(selection, composition, width_scale=1.0)
    if phase_slug == "ice-ih":
        assert_reviewed_ice_reference(selection, standard, ice_standard_reference)
        publish(wide)
    else:
        publish(standard)
        publish(wide)
```

Resolve exactly one passed report under `parity_root` for each phase by source
structure ID, source SHA, calculation ID, and weighting ID. Reject missing,
duplicate, failed, or stale reports. Validate all parity inputs and all nine
bundles before publishing the series root. A phase failure leaves its
diagnostics explicitly incomplete and prevents the top-level series manifest
from claiming completion.

- [ ] **Step 5: Render comparison cells directly from geometry**

`series_sheet.py` renders each geometry at a declared 900 px panel size using its vector paths and physical widths directly; it does not resize a prior PNG and uses no Gaussian, antialias post-filter, or blur. Use five columns in phase order and two rows (`standard`, `wide`), labels outside the circular artwork, black ink on white, and a ledger containing every geometry ID, bundle ID, phase, treatment, orientation ID, panel renderer version, and exact cell order.

- [ ] **Step 6: Add CLI finite-work output**

Before work starts, stderr must contain:

```text
phase-art-series finite-work phases=5 new_bundle_count=9 comparison_cells=10 simulation_count=0 orientation_bunge_deg=17,31,43
```

The success JSON contains `series_id`, `path`, `new_bundle_count`, `comparison_sheet`, `simulation_count`, ordered bundle IDs, and `manifest_sha256`.

- [ ] **Step 7: Run the complete synthetic series integration**

Run: `uv run pytest tests/unit/test_series_sheet.py tests/integration/test_phase_art_series.py tests/unit/test_cli.py -q`

Expected: PASS; fixture parity reports are validated, the master-construction sentinel is untouched, and all nine bundle inventories are complete.

- [ ] **Step 8: Commit**

```bash
git add src/kikuchi_lab/art_products/series_sheet.py src/kikuchi_lab/workflows/phase_art_series.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_series_sheet.py tests/integration/test_phase_art_series.py tests/unit/test_cli.py
git commit -m "feat: publish five phase hemisphere art series"
```

---

### Task 12: Run bounded real parity, publish the nine designs, and retain acceptance evidence

**Tracker:** KIKU-T034 and KIKU-F006

**Files:**
- Create: `docs/acceptance/phase-general-direct-reflector-art-series.md`
- Modify: `docs/work/KIKU-T034.md`
- Modify: `docs/work/KIKU-F006.md`
- Modify: `docs/work/KIKU-E001.md` only if a new plan/acceptance link is absent
- Output only: `local/phase-general-direct-reflector-art/`

**Interfaces:**
- Consumes: five tracked direct recipes and reviewed Ice reference `/Users/Z/Documents/kikuchi/.worktrees/spherical-intensity/local/ice-tattoo-primary-proof/ice-tattoo-run-9a5ce6ac83e4bdd9`.
- Produces: five passed parity reports, nine new bundles, one ten-cell sheet, and one retained acceptance record that indexes every real non-test product and its reproduction evidence.

- [ ] **Step 1: Run all non-real tests and static validation first**

Run:

```bash
uv run pytest tests/unit tests/scientific tests/adapters -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
git diff --check
```

Expected: all commands PASS before any real smoke starts.

- [ ] **Step 2: Run five parity smokes sequentially with no retry**

Run exactly once per phase, one command at a time:

```bash
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/ice-ih-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/forsterite-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/quartz-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/zircon-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/titanite-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
```

Expected: each reports `simulation_count=1`, one `[2, 65, 65]` master, passed reflector parity, elapsed time, and a retained run path. If any command times out or fails, stop; do not retry or widen limits.

- [ ] **Step 3: Run the zero-master series command**

```bash
uv run kikuchi-lab render-phase-art-series \
  --recipe recipes/art/five-phase-hemisphere-series.yml \
  --parity-root local/phase-general-direct-reflector-art/parity \
  --ice-standard-reference /Users/Z/Documents/kikuchi/.worktrees/spherical-intensity/local/ice-tattoo-primary-proof/ice-tattoo-run-9a5ce6ac83e4bdd9 \
  --output local/phase-general-direct-reflector-art/series
```

Expected: the workflow resolves exactly one matching passed report per phase,
reports `simulation_count=0`, publishes nine new bundles and ten comparison
cells, and completes the series manifest.

- [ ] **Step 4: Run real integration and full regression**

Run:

```bash
uv run pytest tests/integration/test_direct_art_catalog.py tests/integration/test_reflector_parity.py tests/integration/test_phase_art_series.py -q
uv run pytest -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
git diff --check
```

Expected: all PASS with the existing skipped-test count explained in the acceptance record.

- [ ] **Step 5: Inspect and retain the comparison image**

Open the emitted `comparison.png`. Record, separately from numeric validation, whether phase differences are legible, the 15-percent change is slight but visible, the 4/4/3 hierarchy remains coherent, the boundary is unchanged, and no blur or decorative fine centerlines appear. Do not mark visual acceptance on the user's behalf.

- [ ] **Step 6: Write the acceptance record and update tracker truthfully**

The acceptance document records:

- source IDs, source and derivative checksums, settings, citations, and limitations;
- five parity run IDs, master hashes, reflector counts, residual maxima, elapsed times, and deadlines;
- nine bundle IDs and manifests plus the reviewed Ice standard-reference ID;
- identical selected member IDs and centerline hashes within every pair;
- standard and wide width arrays and unchanged 2.20 mm boundary;
- series ID, comparison-sheet path and hash, test commands/results, and scientific-claim boundaries;
- a retained-product index containing the exact generating command, recipe and source IDs, run/bundle/manifest IDs, paths, and checksums for every real catalog, parity report, preview, comparison sheet, vector/geometry bundle, and later derived model created during this execution;
- the Task 5 Ice smoke's retained report evidence and master SHA-256, noting that its pytest-temporary array predated the retention rule and that the Task 12 Ice parity run is the retained replacement rather than a retry;
- `visual_review: pending` until the user explicitly accepts the comparison.

Mark KIKU-T034 and KIKU-F006 `done` only if all non-visual criteria pass and the user explicitly accepts the visual family; otherwise keep them `active` with checked objective criteria and the remaining review box open.

- [ ] **Step 7: Commit acceptance evidence without local output artifacts**

```bash
git add docs/acceptance/phase-general-direct-reflector-art-series.md docs/work/KIKU-T034.md docs/work/KIKU-F006.md docs/work/KIKU-E001.md
git commit -m "docs: retain phase reflector art evidence"
```

Do not add `local/` outputs to Git.

---

## Final Review Gate

Before declaring implementation complete:

1. Confirm direct production and the series workflow both log `simulation_count=0`.
2. Confirm only the five explicitly invoked parity commands log `simulation_count=1`.
3. Compare legacy Ice IDs and bytes against the pre-change tests.
4. Confirm all five phase pairs share member IDs and centerline hashes while widths alone scale by `1.15`.
5. Confirm catalog IDs do not change when only orientation changes.
6. Confirm all nine new bundles include SVG, PDF, PNG, geometry, recipes, catalog/provenance, diagnostics, disclaimer, validation, and manifest.
7. Confirm the comparison sheet contains ten cells in the declared order and is rendered directly at target resolution.
8. Confirm all source and tracker validation, tests, Ruff, and `git diff --check` pass.
9. Present the comparison image and direct bundle paths to the user before closing visual acceptance.
