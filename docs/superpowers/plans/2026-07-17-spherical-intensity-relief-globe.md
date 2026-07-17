# Spherical Intensity Relief Globe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-native pipeline that turns a validated both-hemisphere raw Kikuchi master pattern into a reproducible, provenance-rich, watertight `80.0 mm` spherical intensity-relief STL.

**Architecture:** A strict relief recipe and canonical master-product loader feed a project-owned Lambert-square spherical-field adapter. Raw intensity is globally mapped, sampled onto a deterministic subdivision-7 icosphere, filtered at an explicit physical scale, displaced outward, validated with a star-shaped radial-projection certificate, and atomically published with its field ledger and provenance.

**Tech Stack:** Python 3.12, NumPy 2.x, SciPy 1.x (`cKDTree`), kikuchipy 0.13.0 as a test/reference oracle only, Trimesh 4.12.x with `process=False`, Matplotlib 3.11.x/Agg, PyYAML 6.x, pytest 8.x.

## Global Constraints

- The canonical source is raw finite intensity from a validated `MasterPatternProduct` with shape `(2, N, N)`, hemisphere order `north`, `south`, projection `Lambert square equal-area`, and a non-empty crystal coordinate-frame label.
- The product is one solid star-shaped relief globe, not a texture, band diagram, spherical-harmonic fit, engraved shell, stand, split assembly, or habit hybrid.
- The base diameter is exactly `80.0 mm`; relief is outward-only and at most `1.2 mm`, so every radius lies in `[40.0, 41.2] mm` within `1e-10 mm`.
- Intensity mapping uses one both-hemisphere `1st` to `99th` percentile range, clamp, and positive gamma; the acceptance gamma is `1.0` and per-hemisphere normalization is prohibited.
- The spherical Gaussian filter has `0.8 mm` FWHM at the `40.0 mm` base radius and a `3.0 sigma` cutoff; its parameters and diagnostics are authoritative provenance.
- The canonical topology is a deterministic subdivision-7 icosphere with exactly `163842` vertices and `327680` outward triangles; geometry may not retriangulate, simplify, weld, or repair it.
- The indexed pre-export mesh and its validation ledger are canonical. Production Trimesh construction is always `process=False, validate=False`; only test-only binary-STL round trips may load with `process=True`.
- Canonical validation requires unchanged topology, one connected watertight consistently wound positive-volume body, Euler characteristic `2`, finite bounds, no duplicate or degenerate triangles, and a positive radial-projection certificate for every face.
- The bundle is content-addressed and atomic. Identity includes semantic recipe, source file/product/array identities, mapping/filter/topology/validation contracts, and captured runtime versions.
- The canonical bundle contains exactly STL, fixed PNG preview, deterministic `relief-field.npz`, `mesh-validation.json`, and `relief-manifest.json`; STL coordinates are millimetres and the manifest is authoritative for units.
- FDM observations are advisory and may not mutate geometry. Physical printing, orientation, supports, infill, material, and layer settings remain operator decisions.
- Forsterite `master-437f865cd0f68384` is the acceptance source only; production code must accept arbitrary conforming master products without phase-specific geometry.
- Existing forsterite pattern products, spherical/MTEX plans, and the accepted crystal-habit generator must remain unchanged.

---

## File Map

| File | Responsibility |
| --- | --- |
| `src/kikuchi_lab/relief/recipes.py` | Immutable strict relief recipe, expected source identity, and content identity. |
| `src/kikuchi_lab/relief/field.py` | Lambert square transforms, seam validation, exact source field, and deterministic bilinear sampling. |
| `src/kikuchi_lab/relief/topology.py` | Project-owned deterministic icosahedron subdivision and immutable topology identity. |
| `src/kikuchi_lab/relief/mapping.py` | Global percentile/gamma mapping, physical spherical Gaussian filter, and outward radial geometry. |
| `src/kikuchi_lab/relief/mesh.py` | Star-shaped mesh validation, advisory FDM metrics, deterministic STL/NPZ, and fixed preview. |
| `src/kikuchi_lab/relief/workflow.py` | Content-addressed atomic bundle, inventory, manifest, and public build result. |
| `recipes/relief/forsterite-intensity-globe.yml` | Canonical 501-grid forsterite acceptance recipe. |
| `tests/relief_fixtures.py` | Small analytic canonical master products and spherical feature fixtures. |
| `docs/acceptance/spherical-intensity-relief-globe.md` | Generated acceptance metrics, visual/slicer inspection, and honest print boundary. |

---

### Task 1: Define relief recipes and source identity (`KIKU-T031`)

**Files:**
- Create: `src/kikuchi_lab/relief/__init__.py`
- Create: `src/kikuchi_lab/relief/recipes.py`
- Create: `recipes/relief/forsterite-intensity-globe.yml`
- Create: `tests/unit/relief/test_relief_recipes.py`

**Interfaces:**
- Consumes: `kikuchi_lab.model.identity.plain_data` and `stable_id`.
- Produces: `ReliefSourceExpectation`, `ReliefGeometrySpec`, `ReliefMappingSpec`, `SphericalFilterSpec`, `ReliefFDMContext`, `ReliefGlobeRecipe`, and `load_relief_globe_recipe(path: str | Path) -> ReliefGlobeRecipe`.
- `ReliefGlobeRecipe.identity_dict()` excludes file paths and includes all semantic geometry, mapping, filtering, export, source expectations, and advisory FDM content.

- [ ] **Step 1: Write failing strict recipe and identity tests**

```python
# tests/unit/relief/test_relief_recipes.py
from pathlib import Path

import pytest

from kikuchi_lab.relief.recipes import load_relief_globe_recipe

ROOT = Path(__file__).parents[3]
RECIPE = ROOT / "recipes/relief/forsterite-intensity-globe.yml"


def test_forsterite_relief_recipe_preserves_approved_contract():
    recipe = load_relief_globe_recipe(RECIPE)
    assert recipe.schema == "kikuchi.relief-globe-recipe/v1"
    assert recipe.source.product_id == "master-437f865cd0f68384"
    assert recipe.source.array_sha256 == (
        "7cefc253da7c1d17babca40cfeab12be1e3b400cf259bd28686df51c78451f2e"
    )
    assert recipe.source.file_sha256 == (
        "cd056ab4af34aa3695e492f2f6a85f47beb5e97658ef6c5cc4120802ae161c03"
    )
    assert recipe.geometry.base_diameter_mm == 80.0
    assert recipe.geometry.maximum_relief_mm == 1.2
    assert recipe.geometry.topology == "icosphere"
    assert recipe.geometry.subdivisions == 7
    assert recipe.mapping.percentiles == (1.0, 99.0)
    assert recipe.mapping.gamma == 1.0
    assert recipe.mapping.direction == "bright_outward"
    assert recipe.filter.kind == "spherical_gaussian"
    assert recipe.filter.fwhm_mm == 0.8
    assert recipe.filter.cutoff_sigma == 3.0
    assert recipe.exports == ("stl",)
    assert recipe.recipe_id == load_relief_globe_recipe(RECIPE).recipe_id
    assert "local/" not in str(recipe.identity_dict())


@pytest.mark.parametrize(
    ("needle", "replacement", "message"),
    [
        ("orientation", "orientation_matrx: identity\n", "unknown keys"),
        ("base_diameter_mm: 80.0", "base_diameter_mm: 0", "base_diameter_mm"),
        ("maximum_relief_mm: 1.2", "maximum_relief_mm: -1", "maximum_relief_mm"),
        ("subdivisions: 7", "subdivisions: 6", "subdivisions must equal 7"),
        ("upper: 99.0", "upper: 1.0", "percentile"),
        ("gamma: 1.0", "gamma: false", "gamma"),
        ("fwhm_mm: 0.8", "fwhm_mm: .nan", "fwhm_mm"),
        ("formats: [stl]", "formats: [obj]", "formats"),
    ],
)
def test_recipe_rejects_unknown_and_invalid_semantics(
    tmp_path: Path, needle: str, replacement: str, message: str
):
    text = RECIPE.read_text(encoding="utf-8")
    text = text.replace(needle, replacement) if needle != "orientation" else text + replacement
    candidate = tmp_path / "candidate.yml"
    candidate.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_relief_globe_recipe(candidate)
```

- [ ] **Step 2: Run the focused test and confirm the missing package failure**

Run: `uv run pytest tests/unit/relief/test_relief_recipes.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'kikuchi_lab.relief'`.

- [ ] **Step 3: Add the exact tracked acceptance recipe**

```yaml
# recipes/relief/forsterite-intensity-globe.yml
schema: kikuchi.relief-globe-recipe/v1
source:
  product_id: master-437f865cd0f68384
  array_sha256: 7cefc253da7c1d17babca40cfeab12be1e3b400cf259bd28686df51c78451f2e
  file_sha256: cd056ab4af34aa3695e492f2f6a85f47beb5e97658ef6c5cc4120802ae161c03
geometry:
  base_diameter_mm: 80.0
  maximum_relief_mm: 1.2
  topology: icosphere
  subdivisions: 7
mapping:
  percentiles:
    lower: 1.0
    upper: 99.0
  gamma: 1.0
  direction: bright_outward
filter:
  kind: spherical_gaussian
  fwhm_mm: 0.8
  cutoff_sigma: 3.0
export:
  formats: [stl]
fdm_context:
  process: filament_fdm
```

- [ ] **Step 4: Implement immutable types and closed mapping schemas**

```python
# src/kikuchi_lab/relief/recipes.py
@dataclass(frozen=True)
class ReliefSourceExpectation:
    product_id: str
    array_sha256: str
    file_sha256: str


@dataclass(frozen=True)
class ReliefGeometrySpec:
    base_diameter_mm: float
    maximum_relief_mm: float
    topology: str
    subdivisions: int


@dataclass(frozen=True)
class ReliefMappingSpec:
    percentiles: tuple[float, float]
    gamma: float
    direction: str


@dataclass(frozen=True)
class SphericalFilterSpec:
    kind: str
    fwhm_mm: float
    cutoff_sigma: float


@dataclass(frozen=True)
class ReliefFDMContext:
    process: str


@dataclass(frozen=True)
class ReliefGlobeRecipe:
    schema: str
    source: ReliefSourceExpectation
    geometry: ReliefGeometrySpec
    mapping: ReliefMappingSpec
    filter: SphericalFilterSpec
    exports: tuple[str, ...]
    fdm_context: ReliefFDMContext | None
    recipe_id: str

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source": asdict(self.source),
            "geometry": asdict(self.geometry),
            "mapping": asdict(self.mapping),
            "filter": asdict(self.filter),
            "export": {"formats": list(self.exports)},
            "fdm_context": (
                asdict(self.fdm_context) if self.fdm_context is not None else None
            ),
        }


def _keys(mapping, *, allowed: set[str], required: set[str], field: str) -> None:
    if not isinstance(mapping, dict):
        raise ValueError(f"{field} must be a mapping")
    unknown = sorted(set(mapping) - allowed)
    missing = sorted(required - set(mapping))
    if unknown:
        raise ValueError(f"{field} has unknown keys: {unknown}")
    if missing:
        raise ValueError(f"{field} is missing keys: {missing}")
```

`load_relief_globe_recipe` must call `_keys` for root, source, geometry, mapping,
percentiles, filter, export, and non-null FDM mappings. Reject booleans as
numbers, non-finite values, malformed SHA-256 strings, source IDs outside
`master-[0-9a-f]{16}`, any topology except `icosphere`, subdivisions other
than `7`, nonpositive diameter/relief/gamma/FWHM/cutoff, percentiles outside
`0 <= lower < upper <= 100`, any direction except `bright_outward`, exports
other than exactly `("stl",)`, and FDM processes other than `filament_fdm`.
Compute `recipe_id = stable_id("relief-globe-recipe", identity)` after all
validation.

- [ ] **Step 5: Run recipe tests and lint**

Run: `uv run pytest tests/unit/relief/test_relief_recipes.py -q`

Expected: all recipe tests pass with no task-specific warnings.

Run: `uv run ruff check src/kikuchi_lab/relief tests/unit/relief`

Expected: no lint violations.

- [ ] **Step 6: Commit the recipe contract**

```bash
git add src/kikuchi_lab/relief recipes/relief tests/unit/relief
git commit -m "feat: define intensity relief globe recipes"
```

---

### Task 2: Map Lambert masters onto spherical fields (`KIKU-T032`)

**Files:**
- Create: `src/kikuchi_lab/relief/field.py`
- Create: `tests/relief_fixtures.py`
- Create: `tests/scientific/relief/test_spherical_field.py`
- Modify: `src/kikuchi_lab/relief/__init__.py`

**Interfaces:**
- Consumes: `MasterPatternProduct` and source expectations from Task 1.
- Produces: `SeamDiagnostics`, `SphericalScalarField`, `DirectionalSamples`, `lambert_square_to_directions(x, y, hemisphere)`, `directions_to_lambert_square(directions)`, `build_spherical_scalar_field(master, expected)`, `sample_spherical_field(field, directions)`, and `interpolate_sample_ledger(north_grid, south_grid, samples) -> np.ndarray`.
- All returned arrays are immutable float64/int arrays owned by project types; no kikuchipy/orix object crosses the module boundary.

- [ ] **Step 1: Add analytic master fixtures**

```python
# tests/relief_fixtures.py
def analytic_master_product(size: int = 9, *, seam_offset: float = 0.0):
    grid = np.linspace(-1.0, 1.0, size)
    x, y = np.meshgrid(grid, grid)
    upper_dirs = lambert_square_to_directions(x.ravel(), y.ravel(), hemisphere=1)
    lower_dirs = lambert_square_to_directions(x.ravel(), y.ravel(), hemisphere=-1)
    field = lambda d: 2.0 + 0.25 * d[:, 0] - 0.4 * d[:, 1] + 0.6 * d[:, 2] ** 2
    upper = field(upper_dirs).reshape(size, size)
    lower = field(lower_dirs).reshape(size, size)
    if seam_offset:
        lower[[0, -1], :] += seam_offset
        lower[:, [0, -1]] += seam_offset
    return MasterPatternProduct.from_array(
        np.stack((upper, lower)).astype(np.float32),
        metadata=canonical_master_metadata(projection="Lambert square equal-area"),
    )
```

Copy `canonical_master_metadata` from the existing test-fixture pattern into
this focused module, retaining valid phase/source/generator/simulation,
hemisphere, frame, energy, and provenance identities rather than mocking the
product constructor.

- [ ] **Step 2: Write failing transform, seam, and interpolation tests**

```python
# tests/scientific/relief/test_spherical_field.py
def test_lambert_landmarks_and_round_trip():
    square = np.array([[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    directions = lambert_square_to_directions(square[:, 0], square[:, 1], hemisphere=1)
    assert np.allclose(directions[0], [0, 0, 1], atol=1e-14, rtol=0)
    assert np.allclose(directions[1:], [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]], atol=1e-14, rtol=0)
    assert np.allclose(directions_to_lambert_square(directions), square, atol=1e-14, rtol=0)


def test_project_mapping_matches_pinned_kikuchipy_reference():
    from kikuchipy.signals.util._master_pattern import _vector2lambert
    rng = np.random.default_rng(7142026)
    directions = rng.normal(size=(128, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    expected = _vector2lambert(directions) / np.sqrt(np.pi / 2.0)
    assert np.allclose(directions_to_lambert_square(directions), expected, atol=2e-14, rtol=0)


def test_field_owns_one_equator_and_exact_source_identity():
    master = analytic_master_product(size=9)
    expected = expectation_for(master)
    field = build_spherical_scalar_field(master, expected)
    boundary_count = 4 * 9 - 4
    assert len(field.raw_values) == 2 * 9 * 9 - boundary_count
    assert field.master_product_id == master.product_id
    assert field.seam.maximum_normalized_residual == 0.0
    assert field.seam.equator_owner == "north"
    assert not field.directions.flags.writeable


def test_bilinear_sampling_recovers_selected_source_nodes():
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    indices = np.array([0, 10, 40, 72, 80])
    sampled = sample_spherical_field(field, field.directions[indices])
    assert np.allclose(sampled.raw_values, field.raw_values[indices], atol=2e-6, rtol=0)
    assert np.allclose(sampled.weights.sum(axis=1), 1.0, atol=1e-15, rtol=0)


def test_field_rejects_equator_mismatch():
    master = analytic_master_product(size=9, seam_offset=0.1)
    with pytest.raises(ValueError, match="equator seam residual"):
        build_spherical_scalar_field(master, expectation_for(master))
```

- [ ] **Step 3: Run tests and confirm the missing field module failure**

Run: `uv run pytest tests/scientific/relief/test_spherical_field.py -q`

Expected: collection fails because `kikuchi_lab.relief.field` does not exist.

- [ ] **Step 4: Implement project-owned Lambert transforms**

```python
# src/kikuchi_lab/relief/field.py
_SQRT_PI_HALF = np.sqrt(np.pi / 2.0)
_SQRT_PI_OVER_2 = np.sqrt(np.pi) / 2.0
_TWO_OVER_SQRT_PI = 2.0 / np.sqrt(np.pi)
_SEAM_TOLERANCE = 1e-6


def directions_to_lambert_square(directions: object) -> np.ndarray:
    vectors = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.any(norms <= 0):
        raise ValueError("directions must be finite nonzero vectors")
    unit = vectors / norms[:, None]
    result = np.zeros((len(unit), 2), dtype=np.float64)
    for index, (x, y, z) in enumerate(unit):
        root = np.sqrt(2.0 * (1.0 - abs(z)))
        if root == 0.0:
            continue
        if abs(y) <= abs(x):
            sign = np.copysign(1.0, x)
            result[index, 0] = sign * root * _SQRT_PI_OVER_2
            result[index, 1] = sign * root * _TWO_OVER_SQRT_PI * np.arctan(y / x)
        else:
            sign = np.copysign(1.0, y)
            result[index, 0] = sign * root * _TWO_OVER_SQRT_PI * np.arctan(x / y)
            result[index, 1] = sign * root * _SQRT_PI_OVER_2
    return result / _SQRT_PI_HALF


def lambert_square_to_directions(x: object, y: object, hemisphere: int) -> np.ndarray:
    if hemisphere not in (-1, 1):
        raise ValueError("hemisphere must be +1 north or -1 south")
    x_array, y_array = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    if not np.isfinite(x_array).all() or not np.isfinite(y_array).all():
        raise ValueError("Lambert coordinates must be finite")
    if np.any(np.abs(x_array) > 1.0) or np.any(np.abs(y_array) > 1.0):
        raise ValueError("Lambert coordinates must lie in [-1, 1]")
    xi = x_array.ravel() * _SQRT_PI_HALF
    yi = y_array.ravel() * _SQRT_PI_HALF
    cart = np.zeros((len(xi), 3), dtype=np.float64)
    for index, (left, up) in enumerate(zip(xi, yi, strict=True)):
        if max(abs(left), abs(up)) == 0.0:
            cart[index] = (0.0, 0.0, float(hemisphere))
        elif abs(left) <= abs(up):
            q = 2.0 * up * np.sqrt(np.pi - up * up) / np.pi
            angle = left * np.pi * 0.25 / up
            cart[index] = (q * np.sin(angle), q * np.cos(angle), hemisphere * (1.0 - 2.0 * up * up / np.pi))
        else:
            q = 2.0 * left * np.sqrt(np.pi - left * left) / np.pi
            angle = up * np.pi * 0.25 / left
            cart[index] = (q * np.cos(angle), q * np.sin(angle), hemisphere * (1.0 - 2.0 * left * left / np.pi))
    cart /= np.linalg.norm(cart, axis=1, keepdims=True)
    return cart
```

This is the reviewed Callahan/EMsoft square Lambert mapping used by pinned
kikuchipy 0.13.0, rewritten as project-owned float64 plain-array code. Preserve
attribution in the module docstring. The production module must not import the
private kikuchipy functions used by the reference test.

- [ ] **Step 5: Implement field construction, identity, and sampling ledgers**

```python
@dataclass(frozen=True)
class SeamDiagnostics:
    equator_owner: str
    boundary_count: int
    maximum_absolute_residual: float
    maximum_normalized_residual: float
    tolerance: float


@dataclass(frozen=True)
class SphericalScalarField:
    field_id: str
    master_product_id: str
    master_array_sha256: str
    projection: str
    coordinate_frame: str
    north_grid: np.ndarray
    south_grid: np.ndarray
    directions: np.ndarray
    raw_values: np.ndarray
    source_hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    seam: SeamDiagnostics


@dataclass(frozen=True)
class DirectionalSamples:
    directions: np.ndarray
    raw_values: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray
```

`build_spherical_scalar_field` must verify source product ID, array SHA, file
expectation supplied separately by the workflow, shape, odd square size,
projection, hemisphere order, and frame. Boundary is the union of first/last
rows and columns. Compare paired boundary values using
`max(abs(north-south)) / max(ptp(canonical_values), eps)` and require `<=1e-6`.
Flatten all north nodes in row-major order, then only non-boundary south nodes
in row-major order. Record stable ID from master identity, transform contract,
owner, tolerance, count, and residual metrics.

`sample_spherical_field` must normalize copied directions, choose north for
`z >= -1e-14` and south otherwise, convert to normalized Lambert coordinates,
map to pixel coordinates `(coord + 1) * (N - 1) / 2`, and record clamped low/high
row/column indices plus bilinear weights in order `(00, 10, 01, 11)`. At
`abs(z) <= 1e-14`, evaluate both grids and reject disagreement above the field's
seam tolerance before retaining north. Freeze every returned array.
`interpolate_sample_ledger` validates two grids against the field shape and
uses each sample's recorded hemisphere, two row indices, two column indices,
and four weights to return values in `(00, 10, 01, 11)` order. Task 4 reuses
this function so raw and mapped sampling cannot drift.

```python
def interpolate_sample_ledger(
    north_grid: np.ndarray,
    south_grid: np.ndarray,
    samples: DirectionalSamples,
) -> np.ndarray:
    north = np.asarray(north_grid, dtype=np.float64)
    south = np.asarray(south_grid, dtype=np.float64)
    if north.shape != south.shape or north.ndim != 2 or north.shape[0] != north.shape[1]:
        raise ValueError("sample grids must be aligned square arrays")
    if samples.source_rows.shape != (len(samples.directions), 2):
        raise ValueError("sample row ledger must have shape (N, 2)")
    if samples.source_columns.shape != (len(samples.directions), 2):
        raise ValueError("sample column ledger must have shape (N, 2)")
    if samples.weights.shape != (len(samples.directions), 4):
        raise ValueError("sample weight ledger must have shape (N, 4)")
    if not np.isin(samples.hemisphere, (-1, 1)).all():
        raise ValueError("sample hemisphere ledger must contain only -1 and +1")
    row0, row1 = samples.source_rows.T
    col0, col1 = samples.source_columns.T
    corners = np.empty((len(samples.directions), 4), dtype=np.float64)
    for owner, grid in ((1, north), (-1, south)):
        owned = np.flatnonzero(samples.hemisphere == owner)
        corners[owned, 0] = grid[row0[owned], col0[owned]]
        corners[owned, 1] = grid[row1[owned], col0[owned]]
        corners[owned, 2] = grid[row0[owned], col1[owned]]
        corners[owned, 3] = grid[row1[owned], col1[owned]]
    return immutable_float_array(np.einsum("ij,ij->i", corners, samples.weights))
```

- [ ] **Step 6: Run field tests, the real 501 seam check, and lint**

Run: `uv run pytest tests/scientific/relief/test_spherical_field.py -q`

Expected: all analytic transform/seam/interpolation tests pass.

Add and run a real-source test guarded by `pytest.skip` when the local file is
absent. It must load `master-437f865cd0f68384`, assert shape `(2,501,501)`,
field node count `500002`, and zero normalized seam residual.

Run: `uv run ruff check src/kikuchi_lab/relief tests/relief_fixtures.py tests/scientific/relief`

Expected: no lint violations.

- [ ] **Step 7: Commit the spherical field boundary**

```bash
git add src/kikuchi_lab/relief tests/relief_fixtures.py tests/scientific/relief
git commit -m "feat: map Lambert masters onto spherical fields"
```

---
### Task 3: Build deterministic geodesic topology (`KIKU-T033`)

**Files:**
- Create: `src/kikuchi_lab/relief/topology.py`
- Create: `tests/unit/relief/test_icosphere_topology.py`
- Modify: `src/kikuchi_lab/relief/__init__.py`

**Interfaces:**
- Consumes: only NumPy and project identity helpers.
- Produces: immutable `IcosphereTopology` and `build_icosphere(subdivisions: int) -> IcosphereTopology`.
- Stable seed order and edge-key midpoint subdivision are part of `topology_id`; Trimesh is not used to construct topology.

- [ ] **Step 1: Write failing topology ladder and canonical hash tests**

```python
# tests/unit/relief/test_icosphere_topology.py
import hashlib

import numpy as np
import pytest

from kikuchi_lab.relief.topology import build_icosphere


@pytest.mark.parametrize("level", range(5))
def test_icosphere_subdivision_ladder_has_exact_counts_and_orientation(level):
    topology = build_icosphere(level)
    assert len(topology.directions) == 10 * 4**level + 2
    assert len(topology.faces) == 20 * 4**level
    assert np.allclose(np.linalg.norm(topology.directions, axis=1), 1.0, atol=2e-15, rtol=0)
    a, b, c = topology.directions[topology.faces].transpose(1, 0, 2)
    assert np.all(np.einsum("ij,ij->i", np.cross(b - a, c - a), a) > 0)
    edges = np.sort(
        np.vstack(
            (
                topology.faces[:, [0, 1]],
                topology.faces[:, [1, 2]],
                topology.faces[:, [2, 0]],
            )
        ),
        axis=1,
    )
    unique_edges = np.unique(edges, axis=0)
    assert len(topology.directions) - len(unique_edges) + len(topology.faces) == 2


def test_canonical_level_seven_topology_is_stable():
    first = build_icosphere(7)
    second = build_icosphere(7)
    assert first.topology_id == second.topology_id
    assert len(first.directions) == 163842
    assert len(first.faces) == 327680
    assert hashlib.sha256(first.directions.tobytes()).digest() == hashlib.sha256(second.directions.tobytes()).digest()
    assert hashlib.sha256(first.faces.tobytes()).digest() == hashlib.sha256(second.faces.tobytes()).digest()
    assert np.array_equal(first.directions, second.directions)
    assert np.array_equal(first.faces, second.faces)


def test_icosphere_rejects_invalid_subdivision():
    for value in (-1, 8, True, 1.5):
        with pytest.raises(ValueError, match="subdivisions"):
            build_icosphere(value)
```

- [ ] **Step 2: Run the focused test and confirm the missing topology module failure**

Run: `uv run pytest tests/unit/relief/test_icosphere_topology.py -q`

Expected: collection fails because `kikuchi_lab.relief.topology` does not exist.

- [ ] **Step 3: Implement the fixed project-owned icosahedron seed**

```python
# src/kikuchi_lab/relief/topology.py
_PHI = (1.0 + np.sqrt(5.0)) / 2.0
_SEED_VERTICES = np.array(
    [
        (-1, _PHI, 0), (1, _PHI, 0), (-1, -_PHI, 0), (1, -_PHI, 0),
        (0, -1, _PHI), (0, 1, _PHI), (0, -1, -_PHI), (0, 1, -_PHI),
        (_PHI, 0, -1), (_PHI, 0, 1), (-_PHI, 0, -1), (-_PHI, 0, 1),
    ],
    dtype=np.float64,
)
_SEED_FACES = np.array(
    [
        (0,11,5), (0,5,1), (0,1,7), (0,7,10), (0,10,11),
        (1,5,9), (5,11,4), (11,10,2), (10,7,6), (7,1,8),
        (3,9,4), (3,4,2), (3,2,6), (3,6,8), (3,8,9),
        (4,9,5), (2,4,11), (6,2,10), (8,6,7), (9,8,1),
    ],
    dtype=np.int64,
)


@dataclass(frozen=True)
class IcosphereTopology:
    topology_id: str
    subdivisions: int
    directions: np.ndarray
    faces: np.ndarray


def _unit(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)
```

Normalize seed rows in their fixed order. Verify seed orientation at module
construction and raise `RuntimeError` if any face is not outward rather than
silently reversing a face.

- [ ] **Step 4: Implement deterministic sorted-edge subdivision**

```python
def build_icosphere(subdivisions: int) -> IcosphereTopology:
    if isinstance(subdivisions, bool) or not isinstance(subdivisions, int) or not 0 <= subdivisions <= 7:
        raise ValueError("subdivisions must be an integer in [0, 7]")
    vertices = [_unit(row) for row in _SEED_VERTICES]
    faces = [tuple(int(value) for value in face) for face in _SEED_FACES]
    for _ in range(subdivisions):
        midpoints: dict[tuple[int, int], int] = {}

        def midpoint(left: int, right: int) -> int:
            key = tuple(sorted((left, right)))
            if key not in midpoints:
                midpoints[key] = len(vertices)
                vertices.append(_unit(vertices[left] + vertices[right]))
            return midpoints[key]

        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
        faces = refined
    direction_array = immutable_float_array(vertices, width=3)
    face_array = immutable_int_array(faces, width=3)
    identity = {
        "contract": "fixed-icosahedron-sorted-edge-midpoint/v1",
        "subdivisions": subdivisions,
        "directions_sha256": sha256_array(direction_array),
        "faces_sha256": sha256_array(face_array),
    }
    return IcosphereTopology(stable_id("icosphere", identity), subdivisions, direction_array, face_array)
```

Implement the immutable-array and SHA helpers locally with explicit float64
and int64 C-order bytes. Do not round vertex coordinates before identity.

- [ ] **Step 5: Run topology tests, record the canonical hashes, and lint**

Run: `uv run pytest tests/unit/relief/test_icosphere_topology.py -q`

Expected: levels 0-7 pass exact counts, orientation, Euler, immutability, and
repeatability. Add the observed subdivision-7 direction and face SHA-256 values
as literal regression expectations only after the algorithm passes the
independent count/orientation checks.

Run: `uv run ruff check src/kikuchi_lab/relief/topology.py tests/unit/relief/test_icosphere_topology.py`

Expected: no lint violations.

- [ ] **Step 6: Commit deterministic topology**

```bash
git add src/kikuchi_lab/relief/topology.py src/kikuchi_lab/relief/__init__.py tests/unit/relief/test_icosphere_topology.py
git commit -m "feat: build deterministic geodesic topology"
```

---

### Task 4: Map, filter, and displace radial relief (`KIKU-T034`)

**Files:**
- Create: `src/kikuchi_lab/relief/mapping.py`
- Create: `tests/scientific/relief/test_relief_mapping.py`
- Modify: `src/kikuchi_lab/relief/__init__.py`

**Interfaces:**
- Consumes: `SphericalScalarField`, `DirectionalSamples`, `IcosphereTopology`, and Task 1 mapping/filter/geometry specs.
- Produces: `MappedSphericalField`, `MappedDirectionalSamples`, `SphericalFilterDiagnostics`, `ReliefGeometry`, `map_source_field(field: SphericalScalarField, spec: ReliefMappingSpec) -> MappedSphericalField`, `sample_mapped_field(mapped: MappedSphericalField, topology: IcosphereTopology) -> MappedDirectionalSamples`, `filter_spherical_values(values: object, directions: object, base_radius_mm: float, spec: SphericalFilterSpec) -> tuple[np.ndarray, SphericalFilterDiagnostics]`, and `build_relief_geometry(topology: IcosphereTopology, filtered_values: object, base_diameter_mm: float, maximum_relief_mm: float) -> ReliefGeometry`.
- Filter uses deterministic `cKDTree` neighborhoods with stable vertex-index accumulation; faces are copied exactly from topology.

- [ ] **Step 1: Write failing mapping, filter, and radial geometry tests**

```python
# tests/scientific/relief/test_relief_mapping.py
def test_global_mapping_uses_one_both_hemisphere_percentile_range():
    field = field_with_north_range_and_brighter_south()
    mapped = map_source_field(field, ReliefMappingSpec((1.0, 99.0), 1.0, "bright_outward"))
    assert mapped.lower_value == pytest.approx(np.percentile(field.raw_values, 1.0))
    assert mapped.upper_value == pytest.approx(np.percentile(field.raw_values, 99.0))
    assert mapped.north_grid.max() < 1.0
    assert mapped.south_grid.max() == 1.0


def test_filter_preserves_constant_and_attenuates_narrow_feature():
    topology = build_icosphere(4)
    constant, diagnostics = filter_spherical_values(
        np.full(len(topology.directions), 0.375), topology.directions, 40.0, filter_spec()
    )
    assert np.allclose(constant, 0.375, atol=1e-12, rtol=0)
    assert diagnostics.fwhm_rad == pytest.approx(0.8 / 40.0)
    narrow = angular_gaussian(topology.directions, center=[0, 0, 1], fwhm_mm=0.3, radius_mm=40)
    broad = angular_gaussian(topology.directions, center=[0, 0, 1], fwhm_mm=4.0, radius_mm=40)
    filtered_narrow, _ = filter_spherical_values(narrow, topology.directions, 40.0, filter_spec())
    filtered_broad, _ = filter_spherical_values(broad, topology.directions, 40.0, filter_spec())
    assert filtered_narrow.max() <= 0.5 * narrow.max()
    assert filtered_broad.max() >= 0.9 * broad.max()


def test_filter_is_invariant_under_rigid_rotation():
    topology = build_icosphere(3)
    values = 0.5 + 0.2 * topology.directions[:, 0] - 0.1 * topology.directions[:, 2]
    rotation = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
    original, _ = filter_spherical_values(values, topology.directions, 40.0, filter_spec())
    rotated, _ = filter_spherical_values(
        values, topology.directions @ rotation.T, 40.0, filter_spec()
    )
    assert np.allclose(rotated, original, atol=2e-14, rtol=0)


def test_relief_geometry_is_outward_only_and_preserves_topology():
    topology = build_icosphere(3)
    values = np.linspace(0.0, 1.0, len(topology.directions))
    geometry = build_relief_geometry(topology, values, base_diameter_mm=80.0, maximum_relief_mm=1.2)
    assert np.array_equal(geometry.faces, topology.faces)
    assert np.linalg.norm(geometry.vertices, axis=1).min() == pytest.approx(40.0, abs=1e-10)
    assert np.linalg.norm(geometry.vertices, axis=1).max() == pytest.approx(41.2, abs=1e-10)
    assert not geometry.vertices.flags.writeable
```

Add tests rejecting constant/collapsed percentile ranges, gamma `<=0`, mapped
values outside `[0,1]`, non-finite filter inputs, direction/value length
mismatch, non-unit directions, invalid base/relief values, and any face array
that differs from the topology.

- [ ] **Step 2: Run focused tests and confirm the missing mapping module failure**

Run: `uv run pytest tests/scientific/relief/test_relief_mapping.py -q`

Expected: collection fails because `kikuchi_lab.relief.mapping` does not exist.

- [ ] **Step 3: Implement source mapping before directional interpolation**

```python
@dataclass(frozen=True)
class MappedSphericalField:
    source: SphericalScalarField
    lower_percentile: float
    upper_percentile: float
    lower_value: float
    upper_value: float
    gamma: float
    north_grid: np.ndarray
    south_grid: np.ndarray


def map_source_field(field: SphericalScalarField, spec: ReliefMappingSpec) -> MappedSphericalField:
    lower, upper = spec.percentiles
    source_values = field.raw_values
    lower_value, upper_value = np.percentile(source_values, (lower, upper))
    if not np.isfinite((lower_value, upper_value)).all() or upper_value <= lower_value:
        raise ValueError("source percentile range must be finite and non-collapsed")

    def mapped(grid: np.ndarray) -> np.ndarray:
        unit = np.clip((grid - lower_value) / (upper_value - lower_value), 0.0, 1.0)
        return immutable_float_array(unit**spec.gamma)

    return MappedSphericalField(
        source=field,
        lower_percentile=lower,
        upper_percentile=upper,
        lower_value=float(lower_value),
        upper_value=float(upper_value),
        gamma=spec.gamma,
        north_grid=mapped(field.north_grid),
        south_grid=mapped(field.south_grid),
    )
```

`sample_mapped_field` must reuse the exact rows, columns, hemisphere decisions,
and weights returned by `sample_spherical_field` and apply those weights to the
mapped grids. Return both sampled raw and sampled mapped values; never compute
percentiles from icosphere samples.

```python
@dataclass(frozen=True)
class MappedDirectionalSamples:
    directions: np.ndarray
    raw_values: np.ndarray
    mapped_values: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray


def sample_mapped_field(mapped, topology):
    raw = sample_spherical_field(mapped.source, topology.directions)
    mapped_values = interpolate_sample_ledger(
        mapped.north_grid, mapped.south_grid, raw
    )
    return MappedDirectionalSamples(
        directions=raw.directions,
        raw_values=raw.raw_values,
        mapped_values=immutable_float_array(mapped_values),
        hemisphere=raw.hemisphere,
        source_rows=raw.source_rows,
        source_columns=raw.source_columns,
        weights=raw.weights,
    )
```

- [ ] **Step 4: Implement deterministic physical-scale Gaussian filtering**

```python
@dataclass(frozen=True)
class SphericalFilterDiagnostics:
    fwhm_mm: float
    fwhm_rad: float
    sigma_rad: float
    cutoff_sigma: float
    cutoff_chord: float
    minimum_neighbor_count: int
    maximum_neighbor_count: int
    constant_residual: float


def filter_spherical_values(values, directions, base_radius_mm, spec):
    value_array = np.asarray(values, dtype=np.float64).reshape(-1)
    unit = normalized_directions(directions)
    if len(value_array) != len(unit) or not np.isfinite(value_array).all():
        raise ValueError("filter values and directions must be finite and aligned")
    fwhm_rad = spec.fwhm_mm / base_radius_mm
    sigma_rad = fwhm_rad / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    cutoff_angle = spec.cutoff_sigma * sigma_rad
    cutoff_chord = 2.0 * np.sin(cutoff_angle / 2.0)
    tree = cKDTree(unit)
    neighborhoods = tree.query_ball_point(unit, cutoff_chord, workers=1)
    filtered = np.empty_like(value_array)
    counts = np.empty(len(unit), dtype=np.int64)
    for index, neighbors in enumerate(neighborhoods):
        ordered = np.asarray(sorted(neighbors), dtype=np.int64)
        cosine = np.clip(unit[ordered] @ unit[index], -1.0, 1.0)
        angles = np.arccos(cosine)
        weights = np.exp(-0.5 * (angles / sigma_rad) ** 2)
        filtered[index] = np.dot(weights, value_array[ordered]) / weights.sum()
        counts[index] = len(ordered)
    constant_probe = np.ones(len(unit), dtype=np.float64)
    constant_residual = _constant_filter_residual(tree, unit, constant_probe, sigma_rad, cutoff_chord)
    if constant_residual > 1e-12 or not np.isfinite(filtered).all():
        raise ValueError("spherical filter failed its constant-field invariant")
    diagnostics = SphericalFilterDiagnostics(
        fwhm_mm=spec.fwhm_mm,
        fwhm_rad=float(fwhm_rad),
        sigma_rad=float(sigma_rad),
        cutoff_sigma=spec.cutoff_sigma,
        cutoff_chord=float(cutoff_chord),
        minimum_neighbor_count=int(counts.min()),
        maximum_neighbor_count=int(counts.max()),
        constant_residual=float(constant_residual),
    )
    return immutable_float_array(filtered), diagnostics
```

Implement `_constant_filter_residual` with the same neighborhood/weight path,
not a shortcut returning zero. Fill every diagnostics field explicitly.
`workers=1`, stable neighbor sorting, float64 angles, and float64 accumulation
are identity-bearing behavior.

- [ ] **Step 5: Implement immutable outward radial geometry**

```python
@dataclass(frozen=True)
class ReliefGeometry:
    topology_id: str
    directions: np.ndarray
    faces: np.ndarray
    filtered_values: np.ndarray
    radii_mm: np.ndarray
    vertices: np.ndarray
    base_radius_mm: float
    maximum_relief_mm: float


def build_relief_geometry(topology, filtered_values, base_diameter_mm, maximum_relief_mm):
    values = np.asarray(filtered_values, dtype=np.float64).reshape(-1)
    if len(values) != len(topology.directions) or not np.isfinite(values).all():
        raise ValueError("filtered values must be finite and align with topology")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("filtered values must lie in [0, 1]")
    base_radius = base_diameter_mm / 2.0
    radii = base_radius + maximum_relief_mm * values
    vertices = topology.directions * radii[:, None]
    return ReliefGeometry(
        topology.topology_id,
        immutable_float_array(topology.directions, width=3),
        immutable_int_array(topology.faces, width=3),
        immutable_float_array(values),
        immutable_float_array(radii),
        immutable_float_array(vertices, width=3),
        base_radius,
        maximum_relief_mm,
    )
```

Reject booleans, non-finite values, nonpositive diameter/relief, and configured
geometry other than `80.0/1.2` in the canonical recipe path. Assert copied
faces exactly equal the topology before returning.

- [ ] **Step 6: Run scientific mapping tests, bounded performance probe, and lint**

Run: `uv run pytest tests/scientific/relief/test_relief_mapping.py -q`

Expected: all mapping, filter response, determinism, and radial geometry tests pass.

Add a marked `slow` test for subdivision 7 that records neighbor counts,
elapsed filter time, and finite bounded output. It must complete under `60 s`
on the current development machine but is excluded from the default fast gate.

Run: `uv run ruff check src/kikuchi_lab/relief/mapping.py tests/scientific/relief/test_relief_mapping.py`

Expected: no lint violations.

- [ ] **Step 7: Commit mapped relief geometry**

```bash
git add src/kikuchi_lab/relief/mapping.py src/kikuchi_lab/relief/__init__.py tests/scientific/relief/test_relief_mapping.py
git commit -m "feat: map spherical intensity into radial relief"
```

---

### Task 5: Validate and export relief globe meshes (`KIKU-T035`)

**Files:**
- Create: `src/kikuchi_lab/relief/mesh.py`
- Create: `tests/unit/relief/test_relief_mesh.py`
- Modify: `src/kikuchi_lab/relief/__init__.py`

**Interfaces:**
- Consumes: `IcosphereTopology`, `ReliefGeometry`, `DirectionalSamples`, mapped/filtered arrays, and optional `ReliefFDMContext`.
- Produces: `ReliefMeshValidation`, `ReliefFieldArtifact`, `validate_relief_mesh(geometry, topology, fdm_context)`, `relief_stl_bytes(geometry, topology)`, `relief_field_npz_bytes(artifact)`, and `write_relief_preview(path, geometry, validation, *, lower_percentile, upper_percentile, gamma, filter_fwhm_mm)`.
- Trimesh is an inspection/export adapter instantiated only from copied arrays with `process=False, validate=False`.

- [ ] **Step 1: Write failing canonical validation and non-mutation tests**

```python
# tests/unit/relief/test_relief_mesh.py
from dataclasses import replace
import io
import zipfile

import numpy as np
import pytest
import trimesh


def test_valid_radial_mesh_passes_without_mutation(relief_fixture):
    topology, geometry = relief_fixture
    before_vertices = geometry.vertices.copy()
    before_faces = geometry.faces.copy()
    report = validate_relief_mesh(geometry, topology, fdm_context=None)
    assert report.passed is True
    assert report.watertight is True
    assert report.winding_consistent is True
    assert report.body_count == 1
    assert report.euler_characteristic == 2
    assert report.radial_certificate_minimum > report.radial_certificate_tolerance
    assert report.maximum_radius_mm <= 41.2 + 1e-10
    assert np.array_equal(geometry.vertices, before_vertices)
    assert np.array_equal(geometry.faces, before_faces)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda g: replace(g, faces=g.faces[:-1]), "canonical topology"),
        (lambda g: replace(g, faces=np.vstack((g.faces, g.faces[0]))), "canonical topology"),
        (lambda g: replace(g, faces=g.faces[:, ::-1]), "canonical topology"),
        (lambda g: replace(g, vertices=g.vertices * np.array([1, 1, -1])), "radial projection"),
    ],
)
def test_validation_rejects_topology_and_radial_failures(relief_fixture, mutation, message):
    topology, geometry = relief_fixture
    broken = mutation(geometry)
    with pytest.raises(ValueError, match=message):
        validate_relief_mesh(broken, topology, fdm_context=None)


def test_binary_stl_round_trip_is_one_slicer_style_volume(relief_fixture):
    topology, geometry = relief_fixture
    validate_relief_mesh(geometry, topology, fdm_context=None)
    payload = relief_stl_bytes(geometry, topology)
    loaded = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    assert loaded.is_volume and loaded.body_count == 1


def test_field_npz_is_byte_deterministic_and_has_fixed_inventory(field_artifact):
    first = relief_field_npz_bytes(field_artifact)
    second = relief_field_npz_bytes(field_artifact)
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == [f"{name}.npy" for name in FIELD_ARRAY_ORDER]
        assert {item.date_time for item in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}
```

Add tests for radii below `40.0` or above `41.2`, NaN vertices, a zero-area
triangle with otherwise equal shape, changed direction order, disconnected
components, and FDM observations not affecting `passed` or input arrays.

- [ ] **Step 2: Run focused tests and confirm the missing mesh module failure**

Run: `uv run pytest tests/unit/relief/test_relief_mesh.py -q`

Expected: collection fails because `kikuchi_lab.relief.mesh` does not exist.

- [ ] **Step 3: Implement the star-shaped canonical validator**

```python
# src/kikuchi_lab/relief/mesh.py
@dataclass(frozen=True)
class ReliefMeshValidation:
    passed: bool
    watertight: bool
    winding_consistent: bool
    body_count: int
    euler_characteristic: int
    positive_volume: bool
    volume_mm3: float
    surface_area_mm2: float
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    minimum_radius_mm: float
    maximum_radius_mm: float
    degenerate_triangle_count: int
    duplicate_triangle_count: int
    radial_certificate_minimum: float
    radial_certificate_tolerance: float
    self_intersection_contract: str
    warnings: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def _trimesh(geometry: ReliefGeometry) -> trimesh.Trimesh:
    return trimesh.Trimesh(
        vertices=np.array(geometry.vertices, dtype=np.float64, copy=True),
        faces=np.array(geometry.faces, dtype=np.int64, copy=True),
        process=False,
        validate=False,
    )


def _radial_certificate(geometry: ReliefGeometry) -> np.ndarray:
    a, b, c = np.moveaxis(geometry.vertices[geometry.faces], 1, 0)
    return np.einsum("ij,ij->i", np.cross(b - a, c - a), a)


def validate_relief_mesh(geometry, topology, fdm_context):
    if geometry.topology_id != topology.topology_id:
        raise ValueError("relief mesh topology identity differs from canonical topology")
    if not np.array_equal(geometry.faces, topology.faces) or not np.array_equal(geometry.directions, topology.directions):
        raise ValueError("relief mesh changed canonical topology")
    inspected = _trimesh(geometry)
    radii = np.linalg.norm(geometry.vertices, axis=1)
    duplicate_count = duplicate_triangle_count(geometry.faces)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= 1e-12))
    certificate = _radial_certificate(geometry)
    certificate_tolerance = 1e-12 * geometry.base_radius_mm**3
    edge_count = unique_edge_count(geometry.faces)
    euler = len(geometry.vertices) - edge_count + len(geometry.faces)
    failures = []
    if not np.isfinite(geometry.vertices).all(): failures.append("finite vertices")
    if np.any(radii < geometry.base_radius_mm - 1e-10) or np.any(radii > geometry.base_radius_mm + geometry.maximum_relief_mm + 1e-10): failures.append("configured radial range")
    if not inspected.is_watertight: failures.append("watertight")
    if not inspected.is_winding_consistent: failures.append("winding")
    if inspected.body_count != 1: failures.append("one connected body")
    if not inspected.is_volume or not np.isfinite(inspected.volume) or inspected.volume <= 0: failures.append("positive volume")
    if euler != 2: failures.append("Euler characteristic 2")
    if duplicate_count: failures.append("duplicate triangles")
    if degenerate_count: failures.append("degenerate triangles")
    if not np.isfinite(certificate).all() or np.any(certificate <= certificate_tolerance): failures.append("radial projection")
    if failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(failures))
    bounds = np.asarray(inspected.bounds, dtype=float)
    return ReliefMeshValidation(
        passed=True,
        watertight=True,
        winding_consistent=True,
        body_count=1,
        euler_characteristic=2,
        positive_volume=True,
        volume_mm3=float(inspected.volume),
        surface_area_mm2=float(inspected.area),
        bounds_mm=(tuple(bounds[0]), tuple(bounds[1])),
        minimum_radius_mm=float(radii.min()),
        maximum_radius_mm=float(radii.max()),
        degenerate_triangle_count=0,
        duplicate_triangle_count=0,
        radial_certificate_minimum=float(certificate.min()),
        radial_certificate_tolerance=float(certificate_tolerance),
        self_intersection_contract="positive-radial-bijection-over-canonical-icosphere",
        warnings=relief_fdm_warnings(geometry, inspected, fdm_context),
    )
```

Expand the compact one-line conditions to normal formatted blocks during
implementation. `unique_edge_count` must sort and deduplicate all three face
edges. `duplicate_triangle_count` sorts each face's vertex IDs. The radial
certificate plus unchanged canonical connectivity, positive radii, and Euler-2
closed topology is the product-specific no-foldover/self-intersection proof.

- [ ] **Step 4: Implement advisory relief FDM observations**

For a non-null `ReliefFDMContext`, return data-only warnings/metrics containing:

```python
(
    {"code": "fdm_minimum_edge", "measured_mm": minimum_edge},
    {"code": "fdm_minimum_triangle_altitude", "measured_mm": minimum_altitude},
    {"code": "fdm_maximum_local_relief_slope", "measured_degrees": maximum_slope},
    {"code": "fdm_radial_dynamic_range", "measured_mm": maximum_radius - minimum_radius},
    {"code": "fdm_downward_face_fraction", "measured_fraction": downward_count / face_count},
    {"code": "fdm_feature_floor", "configured_mm": 0.8},
)
```

Compute edge/altitude/slope from copied arrays. Define local relief slope on
each canonical edge as `degrees(arctan(abs(delta_radius) / arc_length))` where
`arc_length = base_radius * arccos(dot(unit_left, unit_right))`. Downward faces
are those whose outward normal has negative `z` in the inspection orientation.
These observations never enter the failure list.

- [ ] **Step 5: Implement deterministic STL and field NPZ bytes**

```python
FIELD_ARRAY_ORDER = (
    "directions", "hemisphere", "source_rows", "source_columns", "weights",
    "sampled_raw", "mapped", "filtered", "radii_mm", "faces",
)


@dataclass(frozen=True)
class ReliefFieldArtifact:
    directions: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray
    sampled_raw: np.ndarray
    mapped: np.ndarray
    filtered: np.ndarray
    radii_mm: np.ndarray
    faces: np.ndarray


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, np.ascontiguousarray(array), allow_pickle=False)
    return stream.getvalue()


def relief_field_npz_bytes(artifact: ReliefFieldArtifact) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in FIELD_ARRAY_ORDER:
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, _npy_bytes(getattr(artifact, name)))
    return stream.getvalue()


def relief_stl_bytes(geometry, topology) -> bytes:
    validate_relief_mesh(geometry, topology, fdm_context=None)
    payload = _trimesh(geometry).export(file_type="stl")
    if not isinstance(payload, bytes):
        raise TypeError("Trimesh STL export did not return bytes")
    return payload
```

Validate every artifact array's exact name, dtype, shape, finiteness, and
alignment before writing. Use float64 for directions/weights/values/radii,
int8 for hemisphere, int32 for source rows/columns, and int64 for faces.

- [ ] **Step 6: Implement a fixed accepted-mesh preview**

`write_relief_preview` must use Matplotlib Agg, fixed `figsize=(9,9)`,
`dpi=100`, camera `(elev=22, azim=38)`, white background, equal limits, and
fixed directional lighting. Face colors are the mean filtered value of their
three vertices through `gray`, while geometry is the accepted full-resolution
mesh. Include a text inset for base radius, observed relief range, mapping
percentiles/gamma, and filter FWHM. Save RGBA PNG with fixed metadata
`{"Software": "kikuchi-lab"}` and no timestamps.

```python
def write_relief_preview(
    path: Path,
    geometry: ReliefGeometry,
    validation: ReliefMeshValidation,
    *,
    lower_percentile: float,
    upper_percentile: float,
    gamma: float,
    filter_fwhm_mm: float,
) -> None:
    vertices = np.array(geometry.vertices, copy=True)
    triangles = vertices[geometry.faces]
    face_values = geometry.filtered_values[geometry.faces].mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    light = np.array([0.35, -0.45, 0.82], dtype=np.float64)
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0.0, 1.0)
    rgba = plt.get_cmap("gray")(face_values)
    rgba[:, :3] *= shade[:, None]

    figure = plt.figure(figsize=(9, 9), dpi=100, facecolor="white")
    axes = figure.add_subplot(111, projection="3d")
    axes.add_collection3d(Poly3DCollection(triangles, facecolors=rgba, linewidths=0))
    radius = geometry.base_radius_mm + geometry.maximum_relief_mm
    axes.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(-radius, radius))
    axes.set_box_aspect((1, 1, 1))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    inset = (
        f"base radius: {geometry.base_radius_mm:.3f} mm\n"
        f"observed relief: {validation.maximum_radius_mm - validation.minimum_radius_mm:.3f} mm\n"
        f"mapping: p{lower_percentile:g}-p{upper_percentile:g}, gamma {gamma:g}\n"
        f"filter FWHM: {filter_fwhm_mm:.3f} mm"
    )
    figure.text(0.025, 0.025, inset, ha="left", va="bottom", family="monospace")
    figure.savefig(path, dpi=100, facecolor="white", metadata={"Software": "kikuchi-lab"})
    plt.close(figure)
```

The production module must set `matplotlib.use("Agg")` before importing
`pyplot`, import `Poly3DCollection` explicitly, and validate the accepted mesh
before rendering it. The workflow passes the observed mapping and filter
parameters shown in the inset; preview styling never enters mesh identity.

- [ ] **Step 7: Run mesh/export tests and lint**

Run: `uv run pytest tests/unit/relief/test_relief_mesh.py -q`

Expected: valid geometry, every rejection branch, input non-mutation,
deterministic NPZ, deterministic preview, and test-only STL volume pass.

Run: `uv run ruff check src/kikuchi_lab/relief/mesh.py tests/unit/relief/test_relief_mesh.py`

Expected: no lint violations.

- [ ] **Step 8: Commit relief validation and export**

```bash
git add src/kikuchi_lab/relief/mesh.py src/kikuchi_lab/relief/__init__.py tests/unit/relief/test_relief_mesh.py
git commit -m "feat: validate and export relief globe meshes"
```

---

### Task 6: Build and accept atomic relief globe bundles (`KIKU-T036`)

**Files:**
- Create: `src/kikuchi_lab/relief/workflow.py`
- Create: `tests/integration/test_relief_globe_workflow.py`
- Create: `docs/acceptance/spherical-intensity-relief-globe.md`
- Modify: `src/kikuchi_lab/relief/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`
- Modify: `pytest.ini`
- Modify: `README.md`
- Modify: `docs/work/KIKU-T031.md` through `docs/work/KIKU-T036.md`
- Modify: `docs/work/KIKU-F005.md`

**Interfaces:**
- Consumes: all accepted Task 1-5 public contracts and `load_master_product`.
- Produces: `ReliefGlobeBuildResult` and `build_relief_globe(master_pattern_path, recipe_path, output_root) -> ReliefGlobeBuildResult`.
- CLI: `kikuchi-lab relief globe build --master-pattern PATH --recipe PATH --output ROOT` emits one JSON document; domain/I/O/runtime failures return `1` with `kikuchi-lab: relief globe build failed:` and no traceback.

- [ ] **Step 1: Write failing atomic workflow and CLI tests**

```python
# tests/integration/test_relief_globe_workflow.py
@pytest.mark.slow
def test_analytic_globe_build_is_reproducible_atomic_and_complete(tmp_path, analytic_master_file, canonical_recipe_file):
    first = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "first")
    second = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "second")
    assert first.build_id == second.build_id
    assert tree_hashes(first.path) == tree_hashes(second.path)
    assert {path.name for path in first.path.iterdir()} == {
        "analytic-intensity-relief-globe.stl",
        "analytic-intensity-relief-preview.png",
        "relief-field.npz",
        "mesh-validation.json",
        "relief-manifest.json",
    }
    manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
    assert manifest["units"] == "millimetre"
    assert manifest["topology"]["vertex_count"] == 163842
    assert manifest["topology"]["triangle_count"] == 327680
    assert manifest["source"]["master_product_id"] == load_master_product(analytic_master_file).product_id
    assert manifest["validation"]["passed"] is True
    loaded = trimesh.load_mesh(first.stl, process=True)
    assert loaded.is_volume and loaded.body_count == 1


@pytest.mark.slow
def test_runtime_version_change_changes_build_id(monkeypatch, tmp_path, analytic_master_file, canonical_recipe_file):
    original = workflow._software_versions
    monkeypatch.setattr(workflow, "_software_versions", lambda: {**original(), "scipy": "changed"})
    changed = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "changed")
    monkeypatch.setattr(workflow, "_software_versions", original)
    normal = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "normal")
    assert changed.build_id != normal.build_id


@pytest.mark.slow
def test_failure_removes_partial_bundle(monkeypatch, tmp_path, analytic_master_file, canonical_recipe_file):
    monkeypatch.setattr(workflow, "write_relief_preview", Mock(side_effect=RuntimeError("preview failed")))
    with pytest.raises(RuntimeError, match="preview failed"):
        build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path)
    assert list(tmp_path.glob("*.partial")) == []
    assert list(tmp_path.glob("relief-globe-build-*")) == []
```

The analytic test recipe must contain the actual product, array, and file hashes
for `analytic_master_file`; create it through a fixture rather than weakening
source verification. Mark every test that executes subdivision-7 generation
and filtering `slow`. The failure-before-publication test monkeypatches only the
preview after real source, field, topology, mapping, filter, geometry, and
validation so atomic cleanup is exercised at the final pre-publication seam.

Add CLI tests to `tests/unit/test_cli.py` that monkeypatch
`kikuchi_lab.relief.build_relief_globe`, assert exact argument routing and JSON
paths, and assert a `ValueError` produces one concise stderr line without
`Traceback`.

```python
def test_relief_globe_build_cli_routes_paths_and_prints_json(monkeypatch, capsys, tmp_path):
    bundle = tmp_path / "relief-globe-build-abc"
    result = ReliefGlobeBuildResult(
        build_id="relief-globe-build-abc",
        path=bundle,
        manifest=bundle / "relief-manifest.json",
        stl=bundle / "phase-intensity-relief-globe.stl",
        preview=bundle / "phase-intensity-relief-preview.png",
        field=bundle / "relief-field.npz",
        validation=bundle / "mesh-validation.json",
    )
    build = Mock(return_value=result)
    monkeypatch.setattr("kikuchi_lab.relief.build_relief_globe", build)
    exit_code = main(
        [
            "relief", "globe", "build",
            "--master-pattern", "master.npz",
            "--recipe", "recipe.yml",
            "--output", "out",
        ]
    )
    assert exit_code == 0
    build.assert_called_once_with("master.npz", "recipe.yml", "out")
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "build_id": result.build_id,
        "field": str(result.field),
        "manifest": str(result.manifest),
        "path": str(result.path),
        "preview": str(result.preview),
        "stl": str(result.stl),
        "validation": str(result.validation),
    }


def test_relief_globe_build_cli_reports_domain_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        "kikuchi_lab.relief.build_relief_globe",
        Mock(side_effect=ValueError("source mismatch")),
    )
    exit_code = main(
        [
            "relief", "globe", "build",
            "--master-pattern", "master.npz",
            "--recipe", "recipe.yml",
            "--output", "out",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "kikuchi-lab: relief globe build failed: source mismatch\n"
    assert "Traceback" not in captured.err
```

- [ ] **Step 2: Run focused tests and confirm missing workflow/CLI failures**

Run: `uv run pytest tests/integration/test_relief_globe_workflow.py tests/unit/test_cli.py -q -m "not slow"`

Expected: workflow import or nested `relief globe build` parsing fails.

- [ ] **Step 3: Implement content-addressed identity and atomic publication**

```python
# src/kikuchi_lab/relief/workflow.py
@dataclass(frozen=True)
class ReliefGlobeBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    field: Path
    validation: Path


def build_relief_globe(master_pattern_path, recipe_path, output_root):
    recipe = load_relief_globe_recipe(recipe_path)
    source_path = Path(master_pattern_path).resolve()
    source_file_sha256 = sha256_file(source_path)
    if source_file_sha256 != recipe.source.file_sha256:
        raise ValueError("master product file SHA-256 does not match relief recipe")
    master = load_master_product(source_path)
    verify_master_expectation(master, recipe.source)
    field = build_spherical_scalar_field(master, recipe.source)
    topology = build_icosphere(recipe.geometry.subdivisions)
    mapped = map_source_field(field, recipe.mapping)
    samples = sample_mapped_field(mapped, topology)
    filtered, filter_report = filter_spherical_values(
        samples.mapped_values,
        topology.directions,
        recipe.geometry.base_diameter_mm / 2.0,
        recipe.filter,
    )
    geometry = build_relief_geometry(
        topology,
        filtered,
        recipe.geometry.base_diameter_mm,
        recipe.geometry.maximum_relief_mm,
    )
    validation = validate_relief_mesh(geometry, topology, recipe.fdm_context)
    versions = _software_versions()
    identity = relief_build_identity(
        recipe, master, source_file_sha256, field, topology, mapped, filter_report, versions
    )
    build_id = stable_id("relief-globe-build", identity)
    root = Path(output_root).resolve()
    partial, completed = root / f"{build_id}.partial", root / build_id
    require_fresh_destinations(partial, completed)
    partial.mkdir(parents=True)
    try:
        stem = f"{safe_slug(master.metadata_dict()['phase']['name'])}-intensity-relief"
        (partial / f"{stem}-globe.stl").write_bytes(relief_stl_bytes(geometry, topology))
        write_relief_preview(
            partial / f"{stem}-preview.png",
            geometry,
            validation,
            lower_percentile=mapped.lower_percentile,
            upper_percentile=mapped.upper_percentile,
            gamma=mapped.gamma,
            filter_fwhm_mm=filter_report.fwhm_mm,
        )
        artifact = assemble_field_artifact(samples, filtered, geometry)
        (partial / "relief-field.npz").write_bytes(relief_field_npz_bytes(artifact))
        write_json(partial / "mesh-validation.json", validation.to_dict())
        manifest = build_manifest(identity, recipe, master, field, topology, mapped, filter_report, geometry, validation, partial)
        write_json(partial / "relief-manifest.json", manifest)
        fsync_tree(partial)
        os.replace(partial, completed)
        fsync_directory(root)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return build_result(build_id, completed)
```

Reuse the reviewed habit workflow patterns for canonical JSON, SHA/byte
inventory, safe slugs, fresh destination refusal, fsync, and atomic replace by
extracting only truly generic private helpers into
`src/kikuchi_lab/artifacts/atomic.py` if both workflows can import them without
changing habit output bytes. Otherwise keep focused relief-local helpers; do
not refactor accepted habit behavior merely for DRYness.

`_software_versions()` must capture Python, kikuchi-lab, NumPy, SciPy,
kikuchipy, Trimesh, and Matplotlib once; the exact same mapping appears in
identity and manifest. Manifest must record source/grid/frame/seam, recipe,
mapping percentiles and observed values, topology hashes/counts, interpolation
contract, filter diagnostics, radius/geometry metrics, validation link and
content, units, versions, and SHA-256/byte size for the other four files.

- [ ] **Step 4: Add the nested CLI without disturbing existing commands**

```python
relief = subparsers.add_parser("relief", help="Build printable Kikuchi relief geometry.")
relief_commands = relief.add_subparsers(dest="relief_command", required=True)
globe = relief_commands.add_parser("globe", help="Build spherical relief products.")
globe_commands = globe.add_subparsers(dest="globe_command", required=True)
globe_build = globe_commands.add_parser("build", help="Build one validated relief globe bundle.")
globe_build.add_argument("--master-pattern", required=True)
globe_build.add_argument("--recipe", required=True)
globe_build.add_argument("--output", required=True)

if args.command == "relief" and args.relief_command == "globe" and args.globe_command == "build":
    from kikuchi_lab.relief import build_relief_globe
    try:
        result = build_relief_globe(args.master_pattern, args.recipe, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"kikuchi-lab: relief globe build failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(asdict_path_strings(result), indent=2, sort_keys=True))
    return 0
```

`asdict_path_strings` returns exactly `build_id`, `path`, `manifest`, `stl`,
`preview`, `field`, and `validation`, with paths stringified and no extra keys.

- [ ] **Step 5: Run focused workflow, CLI, and slow reproducibility gates**

Run: `uv run pytest tests/integration/test_relief_globe_workflow.py tests/unit/test_cli.py -q -m "not slow"`

Expected: focused non-slow CLI tests pass; full subdivision-7 workflow tests are deselected.

Run: `uv run pytest tests/integration/test_relief_globe_workflow.py -q -m slow`

Expected: two independent full-resolution analytic builds have identical IDs
and file hashes, runtime-version changes alter identity, late failures leave no
partial bundle, and every slow test completes within the recorded bounded runtime.

- [ ] **Step 6: Build and inspect the real forsterite acceptance bundle**

```bash
uv run kikuchi-lab relief globe build \
  --master-pattern local/benchmarks/forsterite-resolution-501/COD-9000319-ebsdsim.bundle/master-437f865cd0f68384.npz \
  --recipe recipes/relief/forsterite-intensity-globe.yml \
  --output local/relief-globes/forsterite-501
```

Expected manifest/validation evidence:

- source product `master-437f865cd0f68384`, file and array hashes match;
- seam residual `0.0` or below `1e-6`;
- `163842` vertices, `327680` triangles, Euler characteristic `2`;
- radii within `[40.0, 41.2] mm` and maximum possible diameter `<=82.4 mm`;
- one watertight, consistently wound, positive-volume body;
- no duplicate/degenerate triangles and every radial certificate positive;
- five inventoried files with deterministic hashes.

Open the fixed preview and the STL in the available FlashForge-oriented slicer.
Record reported dimensions, solid/body count, whether the slicer changes or
repairs the mesh, and warnings. Do not claim a physical print.

- [ ] **Step 7: Record acceptance and close tracker items only after evidence exists**

Write `docs/acceptance/spherical-intensity-relief-globe.md` with the exact
build ID, local relative links, source identity, mapping/filter metrics,
topology hashes/counts, validation metrics, preview observation, slicer
observation, runtime, software versions, and explicit physical-print boundary.

Update `KIKU-T031` through `KIKU-T036` to `done`, check only criteria backed by
tests/generated evidence, add acceptance/test evidence paths, and set
`KIKU-F005` to `done` only when every feature criterion is satisfied.

- [ ] **Step 8: Run complete regression and repository gates**

```bash
uv run pytest -m "not gpu and not slow" -q
uv run pytest tests/integration/test_relief_globe_workflow.py -m slow -q
uv run ruff check .
uv run python scripts/validate_work_items.py
git diff --check
```

Expected: fast suite and explicit slow relief suite pass, Ruff is clean, all
42 work items validate, and whitespace checks report no errors. Existing
orix/diffpy deprecation warnings may remain documented; no new task-specific
warnings are accepted.

- [ ] **Step 9: Commit the accepted workflow**

```bash
git add src/kikuchi_lab/relief src/kikuchi_lab/cli/main.py tests/integration/test_relief_globe_workflow.py tests/unit/test_cli.py pytest.ini README.md recipes/relief docs/acceptance/spherical-intensity-relief-globe.md docs/work/KIKU-F005.md docs/work/KIKU-T031.md docs/work/KIKU-T032.md docs/work/KIKU-T033.md docs/work/KIKU-T034.md docs/work/KIKU-T035.md docs/work/KIKU-T036.md
git commit -m "feat: build spherical intensity relief globes"
```

---

## Final Review Gate

After Task 6 review is clean:

1. Generate one review package covering the implementation range from this
   plan commit through the accepted head.
2. Dispatch a highest-judgment whole-feature reviewer against the design spec,
   this plan, task reports, and full diff package.
3. Fix every Critical or Important finding in one coordinated fix wave and
   re-review.
4. Run fresh completion evidence: fast suite, explicit slow relief suite,
   Ruff, tracker validation, and diff check.
5. Use `superpowers:finishing-a-development-branch` to offer merge, PR, keep,
   or discard; do not merge or push without the user's explicit choice.
