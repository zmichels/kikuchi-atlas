# Ice Ih Near-Depth Stepped Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, separately ledgered Ice Ih presentation renderer that brightens genuine multi-band overlaps and draws crisp symmetric stepped relief without changing the accepted quiet kinematical product.

**Architecture:** A new `near_depth` package owns strict treatment recipes, exact spherical band-membership accumulation, pointwise optical-depth compositing, vector relief rendering, and immutable bundle publication. The workflow reuses the existing verified Ice kinematical simulation and private kikuchipy context, but all serialized outputs remain project-owned plain data and arrays.

**Tech Stack:** Python 3.11, NumPy, Matplotlib, Pillow, PyYAML, kikuchipy/diffsims, pytest, existing `kikuchi_lab` identity and atomic-bundle conventions.

## Global Constraints

- The accepted `etched-master-quiet.png` and the existing kinematical bundle remain unchanged.
- No blur, glow kernel, morphology, raster edge detection, spatial denoising, intermediate resize, or displaced shadow is permitted.
- Brightness means nearness and is driven only by exact additional overlap after antipodal axial collapse.
- The valid upper stereographic disk uses `abs(dot(direction, normal)) <= sin(theta_B)`.
- Initial Ice parameters are overlap threshold `0.22`, exponent `2.0`, percentile `99.5`, luminance ceiling `0.985`, and optical-depth gain `0.28`.
- Center traces use threshold `0.22`, width `0.42 pt`, alpha `0.62`, casing width `0.82 pt`, and casing alpha `0.38`.
- Boundary seams use threshold `0.34`, width `0.38 pt`, alpha `0.48`, casing width `0.82 pt`, and casing alpha `0.30`.
- Vector geometry is rasterized once at the requested final size with coverage antialiasing only.
- A bounded smoke render must pass before the single `2400 x 2400` review render.

---

### Task 1: Strict treatment recipe and durable work item

**Files:**
- Create: `src/kikuchi_lab/near_depth/__init__.py`
- Create: `src/kikuchi_lab/near_depth/contracts.py`
- Create: `src/kikuchi_lab/near_depth/recipe.py`
- Create: `recipes/presentation/ice-ih-near-depth-stepped.yml`
- Create: `tests/unit/test_near_depth_recipe.py`
- Create: `docs/work/KIKU-T026.md`
- Modify: `docs/work/KIKU-F004.md`

**Interfaces:**
- Produces: `StrokeStyle`, `NearDepthTreatmentRecipe`, `load_near_depth_recipe(path: str | Path) -> NearDepthTreatmentRecipe`.
- `NearDepthTreatmentRecipe.to_dict() -> dict[str, object]` and `.recipe_id -> str` are plain-data, stable identity boundaries.

- [ ] **Step 1: Write the failing recipe tests**

```python
def test_ice_treatment_recipe_loads_exact_approved_parameters() -> None:
    recipe = load_near_depth_recipe(RECIPE)
    assert recipe.overlap_relative_factor == 0.22
    assert recipe.optical_depth_gain == 0.28
    assert recipe.center == StrokeStyle(0.22, 0.42, 0.62, 0.82, 0.38)
    assert recipe.boundary == StrokeStyle(0.34, 0.38, 0.48, 0.82, 0.30)
    assert recipe.figure_size_px == 2400

def test_treatment_recipe_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = yaml.safe_load(RECIPE.read_text())
    payload["blur_radius"] = 1
    path = tmp_path / "invalid.yml"
    path.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValueError, match="fields differ"):
        load_near_depth_recipe(path)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/unit/test_near_depth_recipe.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'kikuchi_lab.near_depth'`.

- [ ] **Step 3: Implement immutable contracts and strict parsing**

```python
@dataclass(frozen=True)
class StrokeStyle:
    relative_factor: float
    width_pt: float
    alpha: float
    casing_width_pt: float
    casing_alpha: float

@dataclass(frozen=True)
class NearDepthTreatmentRecipe:
    schema_version: int
    name: str
    source_kinematical_recipe: str
    expected_kinematical_recipe_id: str
    overlap_relative_factor: float
    weight_exponent: float
    normalization_percentile: float
    optical_depth_gain: float
    luminance_ceiling: float
    center: StrokeStyle
    boundary: StrokeStyle
    figure_size_px: int
    background_color: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_kinematical_recipe": self.source_kinematical_recipe,
            "expected_kinematical_recipe_id": self.expected_kinematical_recipe_id,
            "overlap": {
                "relative_factor": self.overlap_relative_factor,
                "weight_exponent": self.weight_exponent,
                "normalization_percentile": self.normalization_percentile,
            },
            "optical_depth": {
                "gain": self.optical_depth_gain,
                "luminance_ceiling": self.luminance_ceiling,
            },
            "center": self.center.to_dict(),
            "boundary": self.boundary.to_dict(),
            "figure_size_px": self.figure_size_px,
            "background_color": self.background_color,
        }

    @property
    def recipe_id(self) -> str:
        payload = self.to_dict()
        del payload["source_kinematical_recipe"]
        return stable_id("recipe", payload)
```

The YAML uses nested `overlap`, `optical_depth`, `center`, and `boundary` mappings with exact field sets; numeric validators reject booleans, non-finite values, thresholds outside `(0, 1]`, alphas outside `[0, 1]`, percentiles outside `(0, 100]`, non-positive widths, an absolute base path, and a luminance ceiling outside `(0, 1)`.

- [ ] **Step 4: Add the approved Ice recipe and tracker task**

```yaml
schema_version: 1
name: ice-ih-near-depth-stepped
source_kinematical_recipe: ../kinematical/ice-ih-oxygen-quiet-proof.yml
expected_kinematical_recipe_id: recipe-8aa79ffa759eb05b
overlap: {relative_factor: 0.22, weight_exponent: 2.0, normalization_percentile: 99.5}
optical_depth: {gain: 0.28, luminance_ceiling: 0.985}
center: {relative_factor: 0.22, width_pt: 0.42, alpha: 0.62, casing_width_pt: 0.82, casing_alpha: 0.38}
boundary: {relative_factor: 0.34, width_pt: 0.38, alpha: 0.48, casing_width_pt: 0.82, casing_alpha: 0.30}
figure_size_px: 2400
background_color: "#101519"
```

Verify the recorded recipe ID with `uv run python -c 'from kikuchi_lab.kinematical import load_kinematical_recipe; print(load_kinematical_recipe("recipes/kinematical/ice-ih-oxygen-quiet-proof.yml").recipe_id)'`, add `KIKU-T026` as a child of `KIKU-F004`, and record tests, recipe, spec, and eventual run as evidence.

- [ ] **Step 5: Verify GREEN and tracker integrity**

Run: `uv run pytest tests/unit/test_near_depth_recipe.py -q`

Expected: all tests pass.

Run: `uv run python scripts/validate_work_items.py`

Expected: all work items validate.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/near_depth/__init__.py src/kikuchi_lab/near_depth/contracts.py src/kikuchi_lab/near_depth/recipe.py recipes/presentation/ice-ih-near-depth-stepped.yml tests/unit/test_near_depth_recipe.py docs/work/KIKU-T026.md docs/work/KIKU-F004.md
git commit -m "feat: define near-depth treatment recipe"
```

### Task 2: Exact axial overlap field and optical-depth compositor

**Files:**
- Create: `src/kikuchi_lab/near_depth/overlap.py`
- Create: `tests/scientific/test_near_depth_overlap.py`

**Interfaces:**
- Consumes: a diffsims `ReciprocalLatticeVector`, grid size, relative threshold, weighting exponent, and normalization percentile.
- Produces: `OverlapField(raw: np.ndarray, normalized: np.ndarray, valid_disk: np.ndarray, normalization_value: float, axial_band_count: int, metadata: Mapping[str, object])`.
- Produces: `compute_overlap_field(reflectors, *, size: int, relative_factor: float, weight_exponent: float, normalization_percentile: float) -> OverlapField`.
- Produces: `apply_optical_depth(base: np.ndarray, overlap: np.ndarray, *, gain: float, luminance_ceiling: float) -> np.ndarray`.

- [ ] **Step 1: Write failing unit-science tests**

```python
def test_additional_overlap_is_zero_for_one_band() -> None:
    result = accumulate_additional_overlap(
        directions=np.array([[1.0, 0.0, 0.0]]),
        normals=np.array([[0.0, 1.0, 0.0]]),
        half_width_sines=np.array([0.1]),
        weights=np.array([1.0]),
    )
    np.testing.assert_array_equal(result, [0.0])

def test_intersections_are_strength_ordered() -> None:
    result = accumulate_additional_overlap(
        directions=np.array([[0.0, 0.0, 1.0]]),
        normals=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]) / np.array([[1.0], [1.0], [np.sqrt(2.0)]]),
        half_width_sines=np.array([0.1, 0.1, 0.1]),
        weights=np.array([1.0, 0.5, 0.25]),
    )
    assert result[0] == pytest.approx(0.75)

def test_optical_depth_is_identity_at_zero_and_monotonic() -> None:
    base = np.array([0.2, 0.2], dtype=np.float32)
    overlap = np.array([0.0, 1.0], dtype=np.float32)
    result = apply_optical_depth(base, overlap, gain=0.28, luminance_ceiling=0.985)
    assert result[0] == pytest.approx(base[0], abs=1e-7)
    assert base[1] < result[1] < 0.985
```

Add real Ice assertions that axial canonicalization is permutation-independent, every antipodal pair agrees in `abs(F)` and `theta`, and controlled samples immediately inside/on/outside a Bragg boundary agree with `abs(dot(d, n)) <= sin(theta_B)`.

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/scientific/test_near_depth_overlap.py -q`

Expected: import fails because `kikuchi_lab.near_depth.overlap` does not exist.

- [ ] **Step 3: Implement exact membership and streaming accumulation**

```python
def accumulate_additional_overlap(directions, normals, half_width_sines, weights):
    total = np.zeros(len(directions), dtype=np.float64)
    maximum = np.zeros(len(directions), dtype=np.float64)
    for normal, half_width_sine, weight in zip(normals, half_width_sines, weights, strict=True):
        inside = np.abs(directions @ normal) <= half_width_sine
        total[inside] += weight
        maximum[inside] = np.maximum(maximum[inside], weight)
    return np.maximum(total - maximum, 0.0)

def apply_optical_depth(base, overlap, *, gain, luminance_ceiling):
    values = np.asarray(base, dtype=np.float64)
    if np.any(values > luminance_ceiling):
        raise ValueError("base luminance exceeds luminance ceiling")
    tau = -np.log1p(-values / luminance_ceiling)
    result = luminance_ceiling * (1.0 - np.exp(-(tau + gain * overlap)))
    return result.astype(np.float32)
```

Build the upper stereographic grid with `InverseStereographicProjection(pole=-1).xy2vector`, deterministically sign-canonicalize unit normals by the first non-zero component, group rounded axial keys, verify antipodal magnitudes/angles, retain one band, compute `w=(abs(F)/max(abs(F)))**exponent`, and store only running total and maximum arrays.

- [ ] **Step 4: Normalize and enforce failure behavior**

Require a square upper stereographic grid, finite inputs and outputs, at least one positive additional-overlap sample, and a positive valid-disk percentile. Store raw and normalized float32 arrays with zeros outside the disk, plus the equation strings, threshold, exponent, percentile, axial count, and normalization value in metadata.

- [ ] **Step 5: Verify GREEN**

Run: `uv run pytest tests/scientific/test_near_depth_overlap.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/near_depth/overlap.py tests/scientific/test_near_depth_overlap.py
git commit -m "feat: compute exact additional band overlap"
```

### Task 3: Crisp stepped vector renderer

**Files:**
- Create: `src/kikuchi_lab/near_depth/render.py`
- Create: `tests/unit/test_near_depth_render.py`

**Interfaces:**
- Consumes: existing `KinematicalSimulation`, private `_KikuchipyContext`, base `KinematicalRecipe`, `NearDepthTreatmentRecipe`, and `OverlapField`.
- Produces: `NearDepthRender(figures: Mapping[str, bytes], diagnostic_png: bytes, ledger: Mapping[str, object])`.
- Produces: `render_near_depth(context, simulation, base_recipe, treatment, overlap) -> NearDepthRender`.

- [ ] **Step 1: Write failing compositor and vector-parameter tests**

```python
def test_renderer_emits_only_approved_png_inventory(small_ice_inputs) -> None:
    result = render_near_depth(*small_ice_inputs)
    assert set(result.figures) == {
        "etched-master-near-depth-stepped.png",
        "quiet-vs-near-depth-stepped.png",
    }
    for payload in (*result.figures.values(), result.diagnostic_png):
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")

def test_vector_layer_receives_exact_approved_styles(monkeypatch, small_ice_inputs) -> None:
    observed = []
    monkeypatch.setattr("kikuchi_lab.near_depth.render._draw_paths", lambda *a, **k: observed.append(k))
    render_near_depth(*small_ice_inputs)
    assert observed == [
        {"mode": "bands", "width_pt": 0.38, "alpha": 0.48, "casing_width_pt": 0.82, "casing_alpha": 0.30},
        {"mode": "lines", "width_pt": 0.42, "alpha": 0.62, "casing_width_pt": 0.82, "casing_alpha": 0.38},
    ]
```

Also assert that scientific arrays are unchanged and that the quiet PNG payload passed into the comparison remains byte-identical.

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/unit/test_near_depth_render.py -q`

Expected: import fails because the renderer does not exist.

- [ ] **Step 3: Implement no-resample base and vector overlay**

Tone the upper master with existing `asinh_tone_map`, apply optical depth pointwise, mask only outside the disk, and insert it with image extent `(-1, 1, -1, 1)`, origin `lower`, and interpolation `nearest`. Select boundary and center reflectors from the context by relative `abs(F)` threshold, plot public kikuchipy `mode="bands"` and `mode="lines"` geometry, and apply coincident `matplotlib.patheffects.Stroke` casings with no path displacement.

- [ ] **Step 4: Implement deterministic output images and ledger**

Use final-size canvas coordinates once, deterministic PNG metadata, the unchanged circular rim, a nearest-neighbor side-by-side comparison, and a grayscale overlap diagnostic. Record exact equations, thresholds, selected signed and axial counts, stroke parameters, projection/frame conventions, renderer versions, and a categorical `presentation_only` scientific claim.

- [ ] **Step 5: Verify GREEN and no-blur guard**

Run: `uv run pytest tests/unit/test_near_depth_render.py -q`

Expected: all tests pass and `rg -n "blur|Gaussian|bilinear|bicubic|resiz" src/kikuchi_lab/near_depth` finds no prohibited implementation.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/near_depth/render.py tests/unit/test_near_depth_render.py
git commit -m "feat: render crisp stepped near-depth relief"
```

### Task 4: Immutable bundle, workflow, and CLI

**Files:**
- Create: `src/kikuchi_lab/near_depth/bundle.py`
- Create: `src/kikuchi_lab/workflows/near_depth.py`
- Create: `tests/unit/test_near_depth_bundle.py`
- Create: `tests/integration/test_ice_near_depth.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Produces: `write_near_depth_bundle(output_root, execution, treatment, base_recipe, source) -> NearDepthBundleResult`.
- Produces: `render_kinematical_depth(*, recipe_path: str | Path, output_root: str | Path, figure_size_px: int | None = None) -> NearDepthRunResult`.
- Produces CLI: `kikuchi-lab render-kinematical-depth --recipe PATH --output PATH [--figure-size-px N]`.

- [ ] **Step 1: Write failing bundle/workflow/CLI tests**

```python
def test_depth_bundle_has_complete_content_addressed_inventory(tmp_path, execution):
    result = write_near_depth_bundle(tmp_path, execution, treatment, base_recipe, source)
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert manifest["run_id"] == stable_id("near-depth-run", manifest["run_identity"])
    assert set(manifest["files"]) == {
        "figures/etched-master-near-depth-stepped.png",
        "figures/quiet-vs-near-depth-stepped.png",
        "diagnostics/overlap-additional-depth.npy",
        "diagnostics/overlap-additional-depth.png",
        "diagnostics/depth-render-ledger.json",
        "recipes/near-depth.json",
    }

def test_render_kinematical_depth_cli_forwards_paths(monkeypatch, tmp_path, capsys):
    def fake_render(**kwargs):
        assert kwargs == {"recipe_path": "depth.yml", "output_root": str(tmp_path), "figure_size_px": None}
        return SimpleNamespace(
            run_id="near-depth-run-0123456789abcdef",
            path=tmp_path / "near-depth-run-0123456789abcdef",
            treatment_recipe_id="recipe-0123456789abcdef",
            base_recipe_id="recipe-fedcba9876543210",
            figure_names=("etched-master-near-depth-stepped.png", "quiet-vs-near-depth-stepped.png"),
        )
    monkeypatch.setattr("kikuchi_lab.workflows.render_kinematical_depth", fake_render)
    assert main(["render-kinematical-depth", "--recipe", "depth.yml", "--output", str(tmp_path)]) == 0
```

Add tests for base recipe ID mismatch, stable rerun identity, complete SHA/byte inventory, base product/source provenance links, and normalized CLI errors without traceback.

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/unit/test_near_depth_bundle.py tests/integration/test_ice_near_depth.py tests/unit/test_cli.py -q`

Expected: failures report missing near-depth bundle/workflow/CLI symbols.

- [ ] **Step 3: Implement bundle identity and atomic publication**

The run identity contains treatment recipe ID, base recipe ID, source ID/SHA, base stereographic product ID/SHA, overlap raw/normalized SHA, overlap metadata ID, and ledger ID. Write through a unique partial directory, fsync files/directories, and promote with the existing macOS exclusive directory primitive; inventory every non-manifest file before canonical manifest serialization.

- [ ] **Step 4: Implement workflow and CLI**

Resolve the referenced base recipe relative to the treatment file, verify its ID before simulation, load and verify the source, call `simulate_kinematical_arrays`, compute exact overlap, render the depth execution, publish the bundle, and print run ID/path/treatment ID/base recipe ID/figure inventory. `--figure-size-px` supports only the bounded smoke proof and creates an in-memory treatment replacement without changing the tracked recipe ID.

- [ ] **Step 5: Verify GREEN**

Run: `uv run pytest tests/unit/test_near_depth_bundle.py tests/integration/test_ice_near_depth.py tests/unit/test_cli.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/kikuchi_lab/near_depth/bundle.py src/kikuchi_lab/workflows/near_depth.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_near_depth_bundle.py tests/integration/test_ice_near_depth.py tests/unit/test_cli.py
git commit -m "feat: publish near-depth render bundles"
```

### Task 5: Smoke render, 2400 review candidate, acceptance evidence

**Files:**
- Create: `docs/acceptance/ice-ih-near-depth-stepped.md`
- Modify: `docs/work/KIKU-T026.md`

**Interfaces:**
- Consumes the public CLI only.
- Produces one smoke bundle and one content-addressed `2400 x 2400` review bundle under `local/runs/kinematical-depth-ice/`.

- [ ] **Step 1: Run focused regression tests**

Run: `uv run pytest tests/unit/test_near_depth_recipe.py tests/scientific/test_near_depth_overlap.py tests/unit/test_near_depth_render.py tests/unit/test_near_depth_bundle.py tests/integration/test_ice_near_depth.py tests/adapters/test_ice_ih_kinematical.py tests/unit/test_kinematical_render.py tests/unit/test_cli.py -q`

Expected: all focused tests pass.

- [ ] **Step 2: Run bounded smoke render**

Run: `uv run kikuchi-lab render-kinematical-depth --recipe recipes/presentation/ice-ih-near-depth-stepped.yml --output local/runs/kinematical-depth-ice-smoke --figure-size-px 480`

Expected: JSON reports two figures and a completed immutable bundle; inspect the full image and a nearest-neighbor 4x edge crop.

- [ ] **Step 3: Run the single full review render**

Run: `uv run kikuchi-lab render-kinematical-depth --recipe recipes/presentation/ice-ih-near-depth-stepped.yml --output local/runs/kinematical-depth-ice`

Expected: one `2400 x 2400` review bundle containing both approved output figures and both overlap diagnostics.

- [ ] **Step 4: Verify unchanged accepted quiet product**

Run: `shasum -a 256 local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21/figures/etched-master-quiet.png`

Expected: `28d6f340755f6c6a7c4517b76ae78f79684e9810473080daef69af9512123fc5` matches the accepted pre-treatment hash recorded in the Ice acceptance note; the base bundle manifest and directory are not modified.

- [ ] **Step 5: Record evidence and tracker state**

Document the smoke/full run IDs, manifest hashes, output dimensions, no-blur constraints, exact equations, base quiet hash, focused test count, and review status in `docs/acceptance/ice-ih-near-depth-stepped.md`. Mark implementation criteria complete while leaving visual promotion explicitly pending user review.

- [ ] **Step 6: Run full verification**

Run: `uv run pytest -q`

Expected: all project tests pass; if the known process-timing test fails under load, rerun it isolated and record both outputs without concealing the suite result.

Run: `uv run python scripts/validate_work_items.py`

Expected: all work items validate.

Run: `uv run python scripts/work_status.py --root .`

Expected: `KIKU-T026` is active pending visual approval and all parent/child links are symmetric.

- [ ] **Step 7: Commit**

```bash
git add docs/acceptance/ice-ih-near-depth-stepped.md docs/work/KIKU-T026.md
git commit -m "docs: record Ice near-depth review candidate"
```
