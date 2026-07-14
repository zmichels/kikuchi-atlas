# Spherical Intensity and MTEX Density Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export a forsterite kinematical master as an exact-node directional scalar field on S2, an explicitly validated axial derivative, and a bounded MTEX 6.1.1 density/3D visualization bundle.

**Architecture:** Consume the project-owned both-hemisphere stereographic product from `KIKU-F002`, map its valid source nodes through orix's public inverse stereographic transform, and preserve raw intensity alongside pointwise normalized and density-weight channels. Keep exact mapping, persistence, deterministic MATLAB generation, external-process execution, and workflow orchestration in separate modules; MTEX validation is optional for a Python-valid bundle but mandatory for feature acceptance.

**Tech Stack:** Python 3.12; NumPy 2.x; orix 0.14.x; kikuchipy 0.13.0 through the `KIKU-F002` contract; PyYAML 6.x; MATLAB R2025b; MTEX 6.1.1; pytest; Ruff; repo-native Markdown work tracking.

## Global Constraints

- The authoritative object is a sampled directional scalar field on S2; it is not an ODF.
- Consume only the project-owned `KinematicalSimulation.master_stereographic` contract from completed `KIKU-F002`; do not serialize upstream kikuchipy objects.
- The source must contain both stereographic hemispheres in `[upper, lower]` order with shape `(2, N, N)` and odd `N`.
- Use `orix.projections.InverseStereographicProjection`; do not reimplement the transform in production code.
- Define disk inclusion geometrically with `32 * eps(float64)`; never infer valid nodes from nonzero intensity.
- The upper hemisphere owns the equator. The exact count is `2 * inside_count - equator_count`.
- Compare seam values at the same equator indices; compare antipodes with both lower-array axes reversed.
- Keep `domain = S2` and `domain_semantics = directional` even when forsterite passes antipodal checks.
- Emit an axial artifact only when inversion is declared and normalized RMS is at most `1e-6` and normalized maximum residual is at most `1e-5`.
- Preserve immutable `intensity_raw`; derive `intensity_normalized` with percentiles `5.0` and `99.85`, then `density_weight = intensity_normalized ** 1.5`.
- Never use spatial smoothing, blur, neighborhood filters, morphology, downsample-upscale cleanup, or harmonic approximation.
- CSV floating-point columns use `%.17g`; arrays use fixed explicit dtypes and row order.
- Canonical node order is upper row-major in-disk, then lower row-major in-disk excluding the equator.
- Canonical MTEX nodes remain `antipodal = false`; an axial table and field are separate products.
- MTEX linear interpolation must yield `S2FunTri` and normalized maximum node error at most `1e-8`.
- Density sampling uses seed `20260713`, generator `twister`, and restores the caller RNG.
- Smoke profile is `half_size = 32`, `10000` points, `1.0 * degree`, timeout `300` seconds.
- Acceptance profile is `half_size = 128`, `100000` points, `0.25 * degree`, timeout `900` seconds.
- Never retry, widen a timeout, or automatically advance to `half_size = 256` or `1024`.
- Generated MATLAB contains no absolute local path; runtime paths come from explicit arguments or `KIKUCHI_MATLAB` and `KIKUCHI_MTEX_ROOT`.
- A missing, failed, or timed-out MTEX run preserves and promotes the valid Python bundle with an explicit status; feature acceptance still requires a passing MTEX run.
- Existing kinematical figures, dynamical products, `scientific-clean`, and final-bundle schemas remain unchanged.
- Use test-driven development, update the task's tracker acceptance evidence, and commit after every accepted task. Do not push a remote branch.

## Prerequisite Gate

This plan depends on every task in `KIKU-F002` (`KIKU-T013` through
`KIKU-T018`). At execution time, verify all six items are `done` and the
following imports exist before dispatching `KIKU-T019`:

```bash
uv run python scripts/validate_work_items.py
uv run python -c "from kikuchi_lab.kinematical import KinematicalSimulation, load_kinematical_recipe"
uv run python -c "from kikuchi_lab.workflows import render_kinematical"
```

If the gate fails, execute
`docs/superpowers/plans/2026-07-13-kikuchipy-kinematical-reference-products.md`
first. Do not create temporary duplicate kinematical contracts in this feature.

## Scope Boundary

This plan ends with the `half_size = 128` forsterite acceptance bundle and its
reviewed MTEX figures. It does not import the `half_size = 256` visual field or
the `half_size = 1024` production master; fit spherical harmonics; consume a
dynamical master; build an ODF; rotate an EBSD map; create an interactive web
viewer; or make a fabrication mesh.

The optional axial table is an antipodally folded interpretation of the same
single-crystal field. A later ODF-weighted aggregate is a different physical
product and remains parked.

## File Map

| Path | Responsibility |
| --- | --- |
| `src/kikuchi_lab/spherical_intensity/contracts.py` | Immutable recipes, directional and axial fields, build/result records, stable identities. |
| `src/kikuchi_lab/spherical_intensity/recipe.py` | Strict YAML loading and smoke/acceptance profile selection. |
| `src/kikuchi_lab/spherical_intensity/mapping.py` | Source validation, public orix mapping, seam ownership, tone channels, and antipodal diagnostics. |
| `src/kikuchi_lab/spherical_intensity/bundle.py` | Deterministic CSV/NPZ/JSON writes, staging, inventory, hashes, fsync, and atomic promotion. |
| `src/kikuchi_lab/spherical_intensity/mtex_script.py` | Pure deterministic generation of the MTEX 6.1.1 MATLAB script. |
| `src/kikuchi_lab/spherical_intensity/mtex_runner.py` | Runtime discovery and one bounded observed subprocess. |
| `src/kikuchi_lab/spherical_intensity/__init__.py` | Public project-owned spherical-intensity API only. |
| `src/kikuchi_lab/workflows/spherical_intensity.py` | Load recipes, run the bounded `KIKU-F002` source simulation, map, validate, bundle, and report. |
| `recipes/spherical/forsterite-s2-intensity.yml` | Fixed mapping/density semantics plus smoke and acceptance profiles. |
| `tests/unit/test_spherical_intensity_contracts.py` | Recipe validation, immutability, dtypes, shape invariants, and identities. |
| `tests/spherical_fixtures.py` | Small direct constructors shared by spherical unit and integration tests; never a production shortcut. |
| `tests/scientific/test_spherical_intensity_mapping.py` | Geometry mask, seam, antipodal, axial, and no-blur scientific invariants. |
| `tests/adapters/test_orix_spherical_intensity.py` | Direct public-orix parity and projection round trips. |
| `tests/unit/test_spherical_intensity_bundle.py` | Exact inventory, byte determinism, hashes, and atomic failure behavior. |
| `tests/unit/test_spherical_intensity_mtex_script.py` | Portable deterministic MATLAB source contract. |
| `tests/unit/test_spherical_intensity_mtex_runner.py` | Discovery, heartbeat capture, timeout, process-group termination, and status normalization. |
| `tests/integration/test_spherical_intensity_workflow.py` | Small end-to-end Python workflow and existing-product isolation. |
| `tests/integration/test_spherical_intensity_mtex.py` | Explicitly enabled local MATLAB/MTEX smoke integration. |
| `docs/acceptance/spherical-intensity-mtex.md` | Numeric and visual evidence, timing ladder, and production-size decision. |

---

### Task 1: Immutable S2 Contracts and Profiled Recipe (`KIKU-T019`)

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/contracts.py`
- Create: `src/kikuchi_lab/spherical_intensity/recipe.py`
- Create: `src/kikuchi_lab/spherical_intensity/__init__.py`
- Create: `recipes/spherical/forsterite-s2-intensity.yml`
- Create: `tests/unit/test_spherical_intensity_contracts.py`
- Modify: `docs/work/KIKU-T019.md`

**Interfaces:**
- Consumes: `plain_data()`, `canonical_json()`, and `stable_id()` from `kikuchi_lab.model.identity`.
- Produces: `ProfileName`, `DensityWeightRecipe`, `SphericalToleranceRecipe`, `SphericalProfile`, `SphericalIntensityRecipe`, `SphericalIntensityField`, `SphericalAxialField`, `SphericalIntensityBuild`, and `load_spherical_intensity_recipe(path: str | Path, *, profile: ProfileName) -> SphericalIntensityRecipe`.

- [ ] **Step 1: Write failing recipe and immutable-field tests**

```python
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.spherical_intensity import (
    SphericalIntensityField,
    load_spherical_intensity_recipe,
)

ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/spherical/forsterite-s2-intensity.yml"


def minimal_directional_metadata() -> dict[str, object]:
    return {
        "kind": "spherical_scalar_field",
        "domain": "S2",
        "domain_semantics": "directional",
        "source": {"product_id": "kinematical-0123456789abcdef", "array_sha256": "0" * 64},
        "projection": {"name": "stereographic", "hemisphere_order": ["upper", "lower"]},
        "frame": {"name": "standard-Pnma reciprocal Cartesian", "handedness": "right-handed"},
        "grid": {"size": 3, "row_axis": "Y ascending -1 to +1", "column_axis": "X ascending -1 to +1"},
        "phase": {"space_group": 62, "point_group": "mmm", "contains_inversion": True},
        "equator": {"owner": "upper"},
        "normalization": {"name": "quiet-density-v1"},
    }


def test_forsterite_s2_recipe_fixes_bounded_profiles_and_density() -> None:
    smoke = load_spherical_intensity_recipe(RECIPE, profile="smoke")
    acceptance = load_spherical_intensity_recipe(RECIPE, profile="acceptance")
    assert (smoke.profile.half_size, smoke.profile.point_count) == (32, 10_000)
    assert (smoke.profile.sampling_resolution_deg, smoke.profile.timeout_seconds) == (
        1.0,
        300,
    )
    assert (acceptance.profile.half_size, acceptance.profile.point_count) == (
        128,
        100_000,
    )
    assert acceptance.profile.sampling_resolution_deg == 0.25
    assert acceptance.profile.timeout_seconds == 900
    assert acceptance.density.to_dict() == {
        "name": "quiet-density-v1",
        "low_percentile": 5.0,
        "high_percentile": 99.85,
        "exponent": 1.5,
    }
    assert acceptance.rng_seed == 20260713
    assert acceptance.rng_generator == "twister"


def test_directional_field_owns_typed_immutable_columns() -> None:
    xyz = np.eye(3, dtype=np.float64)
    raw = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    field = SphericalIntensityField.from_columns(
        xyz=xyz,
        hemisphere=[1, 1, 1],
        source_row=[0, 1, 2],
        source_column=[2, 1, 0],
        intensity_raw=raw,
        intensity_normalized=[0.0, 0.5, 1.0],
        density_weight=[0.0, 0.5**1.5, 1.0],
        metadata=minimal_directional_metadata(),
    )
    xyz[:] = -1
    raw[:] = -1
    assert field.xyz.dtype == np.float64
    assert field.hemisphere.dtype == np.int8
    assert field.source_row.dtype == np.int32
    assert field.intensity_raw.dtype == np.float32
    assert field.intensity_normalized.dtype == np.float64
    assert field.density_weight.dtype == np.float64
    assert not field.xyz.flags.writeable
    assert field.xyz[0].tolist() == [1.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="unit vectors"):
        SphericalIntensityField.from_columns(
            xyz=[[2.0, 0.0, 0.0]],
            hemisphere=[1],
            source_row=[0],
            source_column=[0],
            intensity_raw=[1.0],
            intensity_normalized=[1.0],
            density_weight=[1.0],
            metadata=minimal_directional_metadata(),
        )
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `uv run pytest tests/unit/test_spherical_intensity_contracts.py -q`

Expected: collection fails because `kikuchi_lab.spherical_intensity` does not exist.

- [ ] **Step 3: Add frozen recipe and profile contracts**

Use these exact public dataclasses and validate all numbers as finite, positive
where required, and non-boolean integers where declared:

```python
from dataclasses import asdict, dataclass
from typing import Literal

ProfileName = Literal["smoke", "acceptance"]


@dataclass(frozen=True)
class DensityWeightRecipe:
    name: str
    low_percentile: float
    high_percentile: float
    exponent: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalToleranceRecipe:
    disk_epsilon_multiplier: int
    unit_norm_max: float
    stereo_round_trip_rad_max: float
    equator_normalized_max: float
    axial_normalized_rms_max: float
    axial_normalized_max: float
    mtex_node_normalized_max: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalProfile:
    name: ProfileName
    half_size: int
    point_count: int
    sampling_resolution_deg: float
    timeout_seconds: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalIntensityRecipe:
    schema_version: int
    name: str
    source_kinematical_recipe: str
    profile: SphericalProfile
    density: DensityWeightRecipe
    tolerances: SphericalToleranceRecipe
    rng_seed: int
    rng_generator: str
    csv_float_format: str
    display_resolution_deg: float
    emit_axial: bool
    expected_mtex_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_kinematical_recipe": self.source_kinematical_recipe,
            "profile": self.profile.to_dict(),
            "density": self.density.to_dict(),
            "tolerances": self.tolerances.to_dict(),
            "rng_seed": self.rng_seed,
            "rng_generator": self.rng_generator,
            "csv_float_format": self.csv_float_format,
            "display_resolution_deg": self.display_resolution_deg,
            "emit_axial": self.emit_axial,
            "expected_mtex_version": self.expected_mtex_version,
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())
```

The loader rejects unknown keys at every level, accepts only the named
`smoke` and `acceptance` profiles, and refuses any other half-size. Paths remain
relative strings in canonical recipe content and are resolved only by the
workflow.

- [ ] **Step 4: Add immutable directional and axial field contracts**

Use byte-backed immutable arrays. Do not use only `array.flags.writeable =
False`, because callers can re-enable writeability on an owning ndarray.

```python
def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _owned(value: object, dtype: np.dtype, shape_tail: tuple[int, ...]) -> np.ndarray:
    converted = np.array(value, dtype=dtype, order="C", copy=True)
    if converted.ndim != 1 + len(shape_tail) or converted.shape[1:] != shape_tail:
        raise ValueError(f"array shape must end with {shape_tail}")
    if not np.isfinite(converted).all():
        raise ValueError("array values must be finite")
    return np.frombuffer(converted.tobytes(order="C"), dtype=dtype).reshape(converted.shape)


@dataclass(frozen=True, init=False, eq=False)
class SphericalIntensityField:
    xyz: np.ndarray
    hemisphere: np.ndarray
    source_row: np.ndarray
    source_column: np.ndarray
    intensity_raw: np.ndarray
    intensity_normalized: np.ndarray
    density_weight: np.ndarray
    metadata: Mapping[str, object]
    channel_sha256: Mapping[str, str]
    field_id: str

    @classmethod
    def from_columns(
        cls,
        *,
        xyz: object,
        hemisphere: object,
        source_row: object,
        source_column: object,
        intensity_raw: object,
        intensity_normalized: object,
        density_weight: object,
        metadata: Mapping[str, object],
    ) -> "SphericalIntensityField":
        vectors = _owned(xyz, np.dtype("<f8"), (3,))
        columns = {
            "hemisphere": _owned(hemisphere, np.dtype("i1"), ()),
            "source_row": _owned(source_row, np.dtype("<i4"), ()),
            "source_column": _owned(source_column, np.dtype("<i4"), ()),
            "intensity_raw": _owned(intensity_raw, np.dtype("<f4"), ()),
            "intensity_normalized": _owned(
                intensity_normalized, np.dtype("<f8"), ()
            ),
            "density_weight": _owned(density_weight, np.dtype("<f8"), ()),
        }
        count = vectors.shape[0]
        if any(column.shape != (count,) for column in columns.values()):
            raise ValueError("spherical field columns must have equal length")
        if np.max(np.abs(np.linalg.norm(vectors, axis=1) - 1.0)) > 5e-13:
            raise ValueError("xyz must contain unit vectors")
        if not set(np.unique(columns["hemisphere"])).issubset({-1, 1}):
            raise ValueError("hemisphere must use +1 upper and -1 lower")
        if np.any(columns["density_weight"] < 0):
            raise ValueError("density_weight must be nonnegative")
        hashes = {
            "xyz": hashlib.sha256(vectors.tobytes()).hexdigest(),
            **{
                name: hashlib.sha256(column.tobytes()).hexdigest()
                for name, column in columns.items()
            },
        }
        plain = plain_data(metadata)
        field_id = stable_id(
            "s2-field", {"metadata": plain, "channel_sha256": hashes}
        )
        product = object.__new__(cls)
        object.__setattr__(product, "xyz", vectors)
        for name, column in columns.items():
            object.__setattr__(product, name, column)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "channel_sha256", _freeze(hashes))
        object.__setattr__(product, "field_id", field_id)
        return product
```

Define `SphericalAxialField` with immutable `xyz: float64[n,3]`,
`source_pairs: int32[n,2,3]` in `[hemisphere,row,column]` order, the same three
intensity channels, metadata, hashes, and `field_id`. Define
`SphericalIntensityBuild(field, axial_field, diagnostics)` as a frozen
dataclass. Export only these project-owned types from `__init__.py`.

Both field factories require metadata values
`kind="spherical_scalar_field"`, `domain="S2"`, and
`domain_semantics="directional"` or `"axial-derived"`; source product ID/hash,
projection, frame, hemisphere order/poles, grid formulas, phase symmetry,
equator policy, and normalization are also required nonempty mappings. Add
`metadata_dict()` methods that return `_thaw(self.metadata)` and never expose a
mutable reference owned by the product.

- [ ] **Step 5: Add the exact profiled YAML**

```yaml
schema_version: 1
name: forsterite-s2-intensity
source_kinematical_recipe: ../kinematical/forsterite-etched-master.yml
profiles:
  smoke:
    half_size: 32
    point_count: 10000
    sampling_resolution_deg: 1.0
    timeout_seconds: 300
  acceptance:
    half_size: 128
    point_count: 100000
    sampling_resolution_deg: 0.25
    timeout_seconds: 900
density:
  name: quiet-density-v1
  low_percentile: 5.0
  high_percentile: 99.85
  exponent: 1.5
tolerances:
  disk_epsilon_multiplier: 32
  unit_norm_max: 5.0e-13
  stereo_round_trip_rad_max: 1.0e-10
  equator_normalized_max: 1.0e-6
  axial_normalized_rms_max: 1.0e-6
  axial_normalized_max: 1.0e-5
  mtex_node_normalized_max: 1.0e-8
rng_seed: 20260713
rng_generator: twister
csv_float_format: "%.17g"
display_resolution_deg: 1.0
emit_axial: true
expected_mtex_version: mtex-6.1.1
```

- [ ] **Step 6: Run contracts, regression tests, and commit**

Run:

```bash
uv run pytest tests/unit/test_spherical_intensity_contracts.py -q
uv run pytest tests/unit/test_identity.py tests/unit/test_products.py -q
uv run ruff check src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_contracts.py
```

Expected: all pass with no Ruff findings.

Set `KIKU-T019` to `done`, check every criterion, and add the recipe, contract,
and focused test paths to `evidence`.

```bash
git add src/kikuchi_lab/spherical_intensity recipes/spherical tests/unit/test_spherical_intensity_contracts.py docs/work/KIKU-T019.md
git commit -m "feat: define spherical intensity contracts"
```

---

### Task 2: Exact Orix Mapping, Seam Policy, and Axial Diagnostics (`KIKU-T020`)

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/mapping.py`
- Create: `tests/spherical_fixtures.py`
- Create: `tests/scientific/test_spherical_intensity_mapping.py`
- Create: `tests/adapters/test_orix_spherical_intensity.py`
- Modify: `src/kikuchi_lab/spherical_intensity/__init__.py`
- Modify: `docs/work/KIKU-T020.md`

**Interfaces:**
- Consumes: completed `KinematicalSimulation`, verified `StructureRecord`, and `SphericalIntensityRecipe`.
- Produces: `build_spherical_intensity(simulation, source, recipe) -> SphericalIntensityBuild`.

- [ ] **Step 1: Write failing geometry, seam, and antipodal tests**

Build the fixture with a `5 x 5` symmetric grid and explicit sentinel values;
do not use a real simulation in these scientific unit tests.

Add these shared fixture constructors in `tests/spherical_fixtures.py`:

```python
ROOT = Path(__file__).parents[1]
SPHERICAL_RECIPE = ROOT / "recipes/spherical/forsterite-s2-intensity.yml"
SOURCE = ROOT / "phases/forsterite/source.yml"


def fixture_source() -> StructureRecord:
    return load_structure_record(SOURCE)


def centrosymmetric_source() -> StructureRecord:
    return fixture_source()


def noncentrosymmetric_source() -> StructureRecord:
    return replace(fixture_source(), name="synthetic-noncentrosymmetric", space_group_number=1)


def spherical_recipe(*, half_size: int = 2) -> SphericalIntensityRecipe:
    recipe = load_spherical_intensity_recipe(SPHERICAL_RECIPE, profile="smoke")
    return replace(recipe, profile=replace(recipe.profile, half_size=half_size))


def symmetric_master(*, half_size: int = 2) -> np.ndarray:
    coordinate = np.linspace(-1.0, 1.0, 2 * half_size + 1, dtype=np.float32)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    intensity = x_grid * x_grid + 2.0 * y_grid * y_grid + 1.0
    return np.stack([intensity, intensity]).astype(np.float32)


def synthetic_simulation(master: np.ndarray) -> KinematicalSimulation:
    stereo = KinematicalArrayProduct.from_array(
        "master-stereographic",
        master,
        metadata={"projection": "stereographic", "hemisphere": "both"},
    )
    lambert = KinematicalArrayProduct.from_array(
        "master-lambert",
        master,
        metadata={"projection": "lambert", "hemisphere": "both"},
    )
    detector = KinematicalArrayProduct.from_array(
        "detector",
        master[0],
        metadata={"projection": "gnomonic", "hemisphere": "upper"},
    )
    return KinematicalSimulation(
        master_stereographic=stereo,
        master_lambert=lambert,
        detector=detector,
        reflector_catalog={},
        projection_ledger={
            "frames": {"crystal": "standard-Pnma reciprocal Cartesian", "handedness": "right-handed"},
            "projections": {
                "stereographic": {
                    "hemisphere": "both",
                    "hemisphere_order": ["upper", "lower"],
                    "row_axis": "Y ascending -1 to +1",
                    "column_axis": "X ascending -1 to +1",
                    "grid_formula": "coordinate[k] = -1 + 2*k/(N-1)",
                }
            },
        },
    )


def small_spherical_build(*, half_size: int = 2) -> SphericalIntensityBuild:
    return build_spherical_intensity(
        synthetic_simulation(symmetric_master(half_size=half_size)),
        fixture_source(),
        spherical_recipe(half_size=half_size),
    )
```

The direct `half_size=2` constructor is test-only. The YAML loader continues to
admit only the exact `32` and `128` named profiles.

```python
def test_geometry_mask_keeps_zero_inside_and_discards_nonzero_outside() -> None:
    upper = np.full((5, 5), 9.0, dtype=np.float32)
    lower = np.full((5, 5), 9.0, dtype=np.float32)
    upper[2, 2] = 0.0
    build = build_spherical_intensity(
        synthetic_simulation(np.stack([upper, lower])),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    center = (
        (build.field.hemisphere == 1)
        & (build.field.source_row == 2)
        & (build.field.source_column == 2)
    )
    assert build.field.intensity_raw[center].tolist() == [0.0]
    assert not np.any(
        (build.field.source_row == 0) & (build.field.source_column == 0)
    )


def test_upper_owns_equator_and_count_is_exact() -> None:
    build = build_spherical_intensity(
        synthetic_simulation(symmetric_master(half_size=2)),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    diagnostics = build.diagnostics
    assert diagnostics["point_count"] == (
        2 * diagnostics["inside_count"] - diagnostics["equator_count"]
    )
    equator_rows = np.asarray(diagnostics["equator_source_indices"])
    for row, column in equator_rows:
        matches = (
            (build.field.source_row == row)
            & (build.field.source_column == column)
        )
        assert build.field.hemisphere[matches].tolist() == [1]


def test_seam_and_antipodal_diagnostics_use_different_index_rules() -> None:
    upper = np.arange(25, dtype=np.float32).reshape(5, 5)
    for row, column in ((0, 2), (2, 0), (2, 4), (4, 2)):
        upper[row, column] = 100.0
    lower = np.flip(upper, axis=(0, 1)).copy()
    build = build_spherical_intensity(
        synthetic_simulation(np.stack([upper, lower])),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    assert build.diagnostics["seam"]["index_rule"] == "same-index-equator"
    assert build.diagnostics["antipodal"]["index_rule"] == (
        "upper[i,j]-lower[N-1-i,N-1-j]"
    )
    assert build.diagnostics["antipodal"]["normalized_max"] == 0.0


def test_noncentrosymmetric_field_preserves_directional_values_and_refuses_axial() -> None:
    upper = np.ones((5, 5), dtype=np.float32)
    lower = np.full((5, 5), 2.0, dtype=np.float32)
    build = build_spherical_intensity(
        synthetic_simulation(np.stack([upper, lower])),
        noncentrosymmetric_source(),
        spherical_recipe(),
    )
    assert build.field.metadata["domain_semantics"] == "directional"
    assert build.axial_field is None
    assert build.diagnostics["axial"]["status"] == "phase-has-no-inversion"
```

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/scientific/test_spherical_intensity_mapping.py tests/adapters/test_orix_spherical_intensity.py -q`

Expected: import failure for `build_spherical_intensity`.

- [ ] **Step 3: Implement exact source validation and public-orix mapping**

Use one shared product and explicit array order; do not look for independent
upper/lower product IDs.

```python
def build_spherical_intensity(
    simulation: KinematicalSimulation,
    source: StructureRecord,
    recipe: SphericalIntensityRecipe,
) -> SphericalIntensityBuild:
    master = np.asarray(simulation.master_stereographic.intensity)
    expected_size = 2 * recipe.profile.half_size + 1
    if master.shape != (2, expected_size, expected_size):
        raise ValueError(
            "stereographic master shape must be (2, 2*half_size+1, 2*half_size+1)"
        )
    ledger = plain_data(simulation.projection_ledger)
    projection = ledger["projections"]["stereographic"]
    if projection["hemisphere_order"] != ["upper", "lower"]:
        raise ValueError("stereographic hemisphere order must be [upper, lower]")
    if projection.get("row_axis") != "Y ascending -1 to +1":
        raise ValueError("stereographic row-axis convention is missing or unsupported")
    if projection.get("column_axis") != "X ascending -1 to +1":
        raise ValueError("stereographic column-axis convention is missing or unsupported")

    size = master.shape[-1]
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    radius_squared = x_grid * x_grid + y_grid * y_grid
    disk_tolerance = (
        recipe.tolerances.disk_epsilon_multiplier * np.finfo(np.float64).eps
    )
    inside = radius_squared <= 1.0 + disk_tolerance
    equator = np.abs(radius_squared - 1.0) <= disk_tolerance
    lower_keep = inside & ~equator

    upper_vectors = np.asarray(
        InverseStereographicProjection(pole=-1)
        .xy2vector(x_grid[inside], y_grid[inside])
        .data,
        dtype=np.float64,
    )
    lower_vectors = np.asarray(
        InverseStereographicProjection(pole=1)
        .xy2vector(x_grid[lower_keep], y_grid[lower_keep])
        .data,
        dtype=np.float64,
    )
```

Append vectors and columns in exact upper-then-lower row-major order. Create
source row/column arrays with `np.indices`, not coordinate rounding. Assert the
point-count invariant before constructing the immutable field.

- [ ] **Step 4: Compute distinct seam, antipodal, and density diagnostics**

```python
upper = np.asarray(master[0], dtype=np.float64)
lower = np.asarray(master[1], dtype=np.float64)
scale = max(float(np.max(master) - np.min(master)), np.finfo(np.float64).eps)

seam_delta = upper[equator] - lower[equator]
antipodal_delta = upper[inside] - np.flip(lower, axis=(0, 1))[inside]

seam = {
    "index_rule": "same-index-equator",
    "maximum_absolute": float(np.max(np.abs(seam_delta), initial=0.0)),
    "rms": float(np.sqrt(np.mean(seam_delta * seam_delta))),
    "normalized_max": float(np.max(np.abs(seam_delta), initial=0.0) / scale),
}
antipodal = {
    "index_rule": "upper[i,j]-lower[N-1-i,N-1-j]",
    "maximum_absolute": float(np.max(np.abs(antipodal_delta), initial=0.0)),
    "rms": float(np.sqrt(np.mean(antipodal_delta * antipodal_delta))),
    "normalized_max": float(
        np.max(np.abs(antipodal_delta), initial=0.0) / scale
    ),
    "normalized_rms": float(np.sqrt(np.mean(antipodal_delta**2)) / scale),
}
if seam["normalized_max"] > recipe.tolerances.equator_normalized_max:
    raise ValueError("upper/lower equator intensity mismatch exceeds tolerance")

raw = np.concatenate([upper[inside], lower[lower_keep]])
low, high = np.percentile(
    raw, [recipe.density.low_percentile, recipe.density.high_percentile]
)
if not high > low:
    raise ValueError("density percentile window must be non-degenerate")
normalized = np.clip((raw - low) / (high - low), 0.0, 1.0)
density_weight = normalized ** recipe.density.exponent
```

Record `low` and `high` as realized values. There is no call to SciPy,
scikit-image, convolution, or any neighborhood operation in this module.

- [ ] **Step 5: Build the optional axial artifact before seam omission**

Use orix `Phase(name=source.name, space_group=source.space_group_number)` only
to obtain the point-group name and `contains_inversion`. Axial eligibility
requires both inversion and the two configured numeric residual thresholds.

For `z > 0`, every upper source sample is one representative. On the equator,
retain only `(X > 0) or (X == 0 and Y >= 0)`. Pair each representative
`(i,j)` with original lower source `(N-1-i,N-1-j)` and calculate raw pair means
before lower-equator omission. Apply the directional field's same realized
`low` and `high` to the axial channel.

```python
axial_allowed = (
    phase.point_group.contains_inversion
    and antipodal["normalized_rms"]
    <= recipe.tolerances.axial_normalized_rms_max
    and antipodal["normalized_max"]
    <= recipe.tolerances.axial_normalized_max
)
upper_z = upper_vectors[:, 2]
upper_x = upper_vectors[:, 0]
upper_y = upper_vectors[:, 1]
representative = (upper_z > disk_tolerance) | (
    (np.abs(upper_z) <= disk_tolerance)
    & ((upper_x > 0) | ((upper_x == 0) & (upper_y >= 0)))
)
```

The directional metadata includes `kind`, source product ID/hash, source shape
and dtype, formulas, row/column axes, frame and handedness, domain semantics,
phase symmetry, equator policy, normalization, diagnostics, and package
versions. Axial metadata additionally includes the representative and source-
pair rules.

- [ ] **Step 6: Add direct public-orix parity and round-trip tests**

```python
def test_cardinal_vectors_match_public_orix() -> None:
    upper = InverseStereographicProjection(pole=-1).xy2vector(
        np.array([0.0, 1.0]), np.array([0.0, 0.0])
    )
    lower = InverseStereographicProjection(pole=1).xy2vector(
        np.array([0.0, 1.0]), np.array([0.0, 0.0])
    )
    np.testing.assert_allclose(upper.data, [[0, 0, 1], [1, 0, 0]], atol=1e-15)
    np.testing.assert_allclose(lower.data, [[0, 0, -1], [1, 0, 0]], atol=1e-15)


def test_exported_vectors_round_trip_with_public_orix() -> None:
    build = small_spherical_build()
    for hemisphere, pole in ((1, -1), (-1, 1)):
        selected = build.field.hemisphere == hemisphere
        vectors = Vector3d(build.field.xyz[selected])
        x, y = StereographicProjection(pole=pole).vector2xy(vectors)
        round_trip = InverseStereographicProjection(pole=pole).xy2vector(x, y)
        cross = np.linalg.norm(np.cross(vectors.data, round_trip.data), axis=1)
        dot = np.sum(vectors.data * round_trip.data, axis=1)
        angular = np.arctan2(cross, dot)
        assert float(np.max(angular, initial=0.0)) <= 1e-10
```

- [ ] **Step 7: Run mapping, regression tests, and commit**

Run:

```bash
uv run pytest tests/scientific/test_spherical_intensity_mapping.py tests/adapters/test_orix_spherical_intensity.py -q
uv run pytest tests/adapters/test_kikuchipy_kinematical.py tests/scientific/test_kinematical_projection_ledger.py -q
uv run ruff check src/kikuchi_lab/spherical_intensity tests/scientific/test_spherical_intensity_mapping.py tests/adapters/test_orix_spherical_intensity.py
```

Expected: all pass; exact-orix parity and existing kinematical tests remain green.

Set `KIKU-T020` to `done`, check its criteria, and add both mapping test files
to `evidence`.

```bash
git add src/kikuchi_lab/spherical_intensity tests/spherical_fixtures.py tests/scientific/test_spherical_intensity_mapping.py tests/adapters/test_orix_spherical_intensity.py docs/work/KIKU-T020.md
git commit -m "feat: map stereographic masters onto S2"
```

---

### Task 3: Deterministic Atomic S2 Exchange Bundle (`KIKU-T021`)

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/bundle.py`
- Create: `tests/unit/test_spherical_intensity_bundle.py`
- Modify: `src/kikuchi_lab/spherical_intensity/__init__.py`
- Modify: `docs/work/KIKU-T021.md`

**Interfaces:**
- Consumes: `SphericalIntensityBuild`, recipe, and verified source identifiers.
- Produces: `SphericalBundleStage`, `SphericalIntensityBundleResult`, `stage_spherical_bundle()`, and `finalize_spherical_bundle()`.

- [ ] **Step 1: Write failing exact-inventory and deterministic-byte tests**

```python
BASE_FILES = {
    "forsterite-s2-intensity.csv",
    "forsterite-s2-intensity.npz",
    "forsterite-s2-intensity.json",
    "forsterite-s2-axial.csv",
    "diagnostics/mtex-status.json",
}


def materialize_stage(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stage = stage_spherical_bundle(
        root, small_spherical_build(), spherical_recipe(), fixture_source()
    )
    return stage.staging_path


def write_python_only_bundle(
    root: Path, build: SphericalIntensityBuild
) -> SphericalIntensityBundleResult:
    stage = stage_spherical_bundle(root, build, spherical_recipe(), fixture_source())
    return finalize_spherical_bundle(stage, mtex_result=None)


def test_python_bundle_has_exact_inventory_and_hashes(tmp_path: Path) -> None:
    stage = stage_spherical_bundle(
        tmp_path, small_spherical_build(), spherical_recipe(), fixture_source()
    )
    result = finalize_spherical_bundle(stage, mtex_result=None)
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert set(manifest["files"]) == BASE_FILES
    actual = {
        str(path.relative_to(result.path))
        for path in result.path.rglob("*")
        if path.is_file()
    }
    assert actual == BASE_FILES | {"manifest.json"}
    for relative, record in manifest["files"].items():
        payload = (result.path / relative).read_bytes()
        assert record == {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }


def test_repeated_staging_writes_identical_scientific_artifact_bytes(tmp_path: Path) -> None:
    first = materialize_stage(tmp_path / "first")
    second = materialize_stage(tmp_path / "second")
    for relative in (
        "forsterite-s2-intensity.csv",
        "forsterite-s2-intensity.npz",
        "forsterite-s2-intensity.json",
        "forsterite-s2-axial.csv",
    ):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_spherical_intensity_bundle.py -q`

Expected: missing bundle module and functions.

- [ ] **Step 3: Implement exact CSV and NPZ exchange**

The directional CSV header and order are exactly:

```text
x,y,z,hemisphere,source_row,source_column,intensity_raw,intensity_normalized,density_weight
```

Write each floating value with `recipe.csv_float_format`, integers as decimal
integers, commas as delimiters, and `\n` line endings. The axial CSV header is:

```text
x,y,z,member_a_hemisphere,member_a_row,member_a_column,member_b_hemisphere,member_b_row,member_b_column,intensity_raw,intensity_normalized,density_weight
```

Write the NPZ with exactly these sorted keys and fixed dtypes:

```python
arrays = {
    "density_weight": np.asarray(field.density_weight, dtype="<f8"),
    "hemisphere": np.asarray(field.hemisphere, dtype="i1"),
    "intensity_normalized": np.asarray(field.intensity_normalized, dtype="<f8"),
    "intensity_raw": np.asarray(field.intensity_raw, dtype="<f4"),
    "source_column": np.asarray(field.source_column, dtype="<i4"),
    "source_row": np.asarray(field.source_row, dtype="<i4"),
    "xyz": np.asarray(field.xyz, dtype="<f8"),
}
with zipfile.ZipFile(destination, mode="w") as archive:
    for key in sorted(arrays):
        payload = io.BytesIO()
        np.lib.format.write_array(payload, arrays[key], allow_pickle=False)
        info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        archive.writestr(info, payload.getvalue())
```

Do not use `np.savez_compressed()` directly: deterministic array equality is
insufficient if ZIP member timestamps make bundle bytes change between runs.

The JSON ledger contains field identity, metadata, channel hashes, recipe,
source links, axial availability and identity, and artifact hashes for CSV,
NPZ, and axial CSV. Task 4 adds the generated-script hash. The ledger cannot
contain its own hash; only `manifest.json` hashes the ledger.

- [ ] **Step 4: Implement staging and atomic finalization**

```python
@dataclass(frozen=True)
class SphericalBundleStage:
    staging_path: Path
    output_root: Path
    scientific_identity: Mapping[str, object]
    field_id: str


@dataclass(frozen=True)
class SphericalIntensityBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str
    field_id: str
    mtex_status: str
```

`stage_spherical_bundle()` validates every field before creating a sibling
`.s2-partial-<uuid>` directory. `finalize_spherical_bundle()` validates any
optional MTEX result, quarantines files still ending in `.partial`, writes
`diagnostics/mtex-status.json`, writes canonical `manifest.json` last, fsyncs
files and directories, calculates:

```python
run_identity = {
    "schema_version": 1,
    "field_id": stage.field_id,
    "scientific_identity": plain_data(stage.scientific_identity),
    "mtex": stable_mtex_identity,
}
run_id = stable_id("s2-run", run_identity)
```

and atomically renames the stage to `output_root / run_id`. Stable MTEX
identity contains request profile/status and actual tool versions only when
successful; it excludes paths, timestamps, elapsed time, commands, logs, and
error prose. Diagnostic files retain those excluded observations.

If no axial field exists, omit `forsterite-s2-axial.csv`, set
`axial_available=false`, and adjust the exact inventory accordingly. A write
failure leaves no promoted directory. An existing complete run raises a named
`SphericalBundleExistsError`.

- [ ] **Step 5: Add corruption, optional-axial, and atomic-failure tests**

Tests must prove:

```python
def test_failed_write_never_promotes_partial_bundle(tmp_path: Path, monkeypatch) -> None:
    def raising_writer(*args, **kwargs) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(bundle, "_write_csv", raising_writer)
    with pytest.raises(OSError, match="synthetic write failure"):
        stage_spherical_bundle(
            tmp_path, small_spherical_build(), spherical_recipe(), fixture_source()
        )
    assert not [path for path in tmp_path.iterdir() if not path.name.startswith(".s2-partial-")]


def test_noncentrosymmetric_bundle_omits_axial_csv(tmp_path: Path) -> None:
    master = symmetric_master()
    build = build_spherical_intensity(
        synthetic_simulation(master),
        noncentrosymmetric_source(),
        spherical_recipe(),
    )
    result = write_python_only_bundle(tmp_path, build)
    assert not (result.path / "forsterite-s2-axial.csv").exists()
    ledger = json.loads((result.path / "forsterite-s2-intensity.json").read_text())
    assert ledger["axial_available"] is False
```

- [ ] **Step 6: Run bundle, regression tests, and commit**

Run:

```bash
uv run pytest tests/unit/test_spherical_intensity_bundle.py -q
uv run pytest tests/unit/test_artifact_bundle.py tests/unit/test_persistence.py -q
uv run ruff check src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_bundle.py
```

Expected: deterministic artifacts, exact inventories, atomic failure tests, and
existing persistence tests pass.

Set `KIKU-T021` to `done`, check its criteria, and add the bundle test to
`evidence`.

```bash
git add src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_bundle.py docs/work/KIKU-T021.md
git commit -m "feat: bundle spherical intensity exchange"
```

---

### Task 4: Portable Generated MTEX Loader and Exact-Node Script (`KIKU-T022`)

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/mtex_script.py`
- Create: `tests/unit/test_spherical_intensity_mtex_script.py`
- Modify: `src/kikuchi_lab/spherical_intensity/bundle.py`
- Modify: `src/kikuchi_lab/spherical_intensity/__init__.py`
- Modify: `docs/work/KIKU-T022.md`

**Interfaces:**
- Consumes: recipe, expected directional node count, axial availability, and fixed bundle filenames.
- Produces: `generate_mtex_script(recipe, expected_node_count, axial_available) -> str`.

- [ ] **Step 1: Write failing deterministic and portability tests**

```python
def test_generated_mtex_script_is_portable_directional_and_exact_node() -> None:
    script = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=True
    )
    assert "getenv('KIKUCHI_MTEX_ROOT')" in script
    assert "startup_mtex('noMenu')" in script
    assert "nodes.antipodal = false" in script
    assert "unique(nodes(:), 'stable', 'noAntipodal')" in script
    assert "interp(nodes, T.intensity_raw, 'linear')" in script
    assert "isa(rawField, 'S2FunTri')" in script
    assert "nodeError / nodeScale <= 1e-08" in script
    assert "rng(20260713, 'twister')" in script
    assert "discreteSample" in script
    assert "onCleanup(@() rng(oldRng))" in script
    assert "MarkerAlpha" not in script
    assert "/Users/" not in script
    assert "C:\\" not in script
    assert script.endswith("\n")
    assert "\r\n" not in script


def test_generated_script_changes_only_profile_constants() -> None:
    smoke = generate_mtex_script(
        smoke_recipe(), expected_node_count=97, axial_available=False
    )
    acceptance = generate_mtex_script(
        acceptance_recipe(), expected_node_count=97, axial_available=False
    )
    assert "pointCount = 10000;" in smoke
    assert "sampleResolutionDeg = 1;" in smoke
    assert "pointCount = 100000;" in acceptance
    assert "sampleResolutionDeg = 0.25;" in acceptance
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_spherical_intensity_mtex_script.py -q`

Expected: missing `mtex_script` module.

- [ ] **Step 3: Generate one deterministic MATLAB script**

Render a static LF-only template with `str.format()` values created from
canonical recipe numbers. The script begins with this exact runtime and source
validation sequence:

```matlab
bundleRoot = fileparts(mfilename('fullpath'));
mtexRoot = getenv('KIKUCHI_MTEX_ROOT');
assert(isfolder(mtexRoot), 'KIKUCHI_MTEX_ROOT is missing or invalid');
assert(isfile(fullfile(mtexRoot, 'startup_mtex.m')));

progressPath = fullfile(bundleRoot, 'diagnostics', 'mtex-progress.jsonl');
writeHeartbeat(progressPath, 'startup', 'start');
originalFolder = pwd;
restoreFolder = onCleanup(@() cd(originalFolder));
cd(mtexRoot);
addpath(mtexRoot);
startup_mtex('noMenu');
matlabVersion = version;
mtexVersion = getMTEXpref('version');
cd(bundleRoot);
writeHeartbeat(progressPath, 'startup', 'end');

T = readtable(fullfile(bundleRoot, 'forsterite-s2-intensity.csv'));
requiredColumns = {'x','y','z','hemisphere','source_row','source_column', ...
  'intensity_raw','intensity_normalized','density_weight'};
assert(isequal(T.Properties.VariableNames, requiredColumns));
assert(height(T) == 97);
xyz = [T.x, T.y, T.z];
assert(all(isfinite(xyz), 'all'));
assert(max(abs(vecnorm(xyz, 2, 2) - 1)) <= 5e-13);
assert(all(isfinite(T.intensity_raw)));
assert(all(isfinite(T.density_weight) & T.density_weight >= 0));
assert(any(T.density_weight > 0));
```

MTEX initialization deliberately occurs while the current directory is
`mtexRoot`, because MTEX 6.1.1 reads its `VERSION` file relative to the current
directory. The script then returns to `bundleRoot`.

- [ ] **Step 4: Add duplicate rejection and exact-node triangulation**

```matlab
writeHeartbeat(progressPath, 'triangulation', 'start');
nodes = vector3d(xyz, 'normalize');
nodes.antipodal = false;
[uniqueNodes, ~, ~] = unique(nodes(:), 'stable', 'noAntipodal');
assert(length(uniqueNodes) == length(nodes), ...
  'Duplicate directions would be averaged by S2FunTri');
rawField = interp(nodes, T.intensity_raw, 'linear');
assert(isa(rawField, 'S2FunTri'));
densityField = interp(nodes, T.density_weight, 'linear');
assert(isa(densityField, 'S2FunTri'));
writeHeartbeat(progressPath, 'triangulation', 'end');

writeHeartbeat(progressPath, 'node-evaluation', 'start');
nodeError = max(abs(rawField.eval(nodes) - T.intensity_raw));
nodeScale = max(max(abs(T.intensity_raw)), eps);
assert(nodeError / nodeScale <= 1e-08);
writeHeartbeat(progressPath, 'node-evaluation', 'end');
```

Do not set the directional nodes or fields antipodal. If the axial CSV exists,
load it independently, mark only those representative nodes antipodal, build a
separate `S2FunTri`, and then explicitly set `axialField.antipodal = true`
because the constructor clears the node flag.

- [ ] **Step 5: Add bounded-profile density output and fixed preview**

```matlab
pointCount = 10000;
sampleResolutionDeg = 1;
seed = 20260713;

writeHeartbeat(progressPath, 'density-sampling', 'start');
oldRng = rng;
restoreRng = onCleanup(@() rng(oldRng));
rng(seed, 'twister');
densityVectors = discreteSample(densityField, pointCount, ...
  'resolution', sampleResolutionDeg * degree);
cloudXYZ = densityVectors.xyz;
clear restoreRng;
assert(size(cloudXYZ, 1) == pointCount);
assert(all(isfinite(cloudXYZ), 'all'));

cloudPartial = fullfile(bundleRoot, 'forsterite-s2-density-vectors.partial.csv');
cloudFinal = fullfile(bundleRoot, 'forsterite-s2-density-vectors.csv');
cloudFile = fopen(cloudPartial, 'w');
assert(cloudFile >= 0);
cloudCleanup = onCleanup(@() fclose(cloudFile));
fprintf(cloudFile, 'x,y,z\n');
fprintf(cloudFile, '%.17g,%.17g,%.17g\n', cloudXYZ.');
clear cloudCleanup;
movefile(cloudPartial, cloudFinal, 'f');
writeHeartbeat(progressPath, 'density-sampling', 'end');
```

Render an invisible `1600 x 900` fixed-camera figure with
raw exact-node scatter, `plot3d(rawField, 'resolution', 1 * degree)`, and the
density cloud. Use fixed grayscale limits, white background, no alpha-marker
options, `axis vis3d`, `drawnow`, and `exportgraphics`; write PNG to `.partial`
then rename.

Also export five fixed-view evidence PNGs under `figures/` with exact names:

```text
figures/exact-node-scatter.png
figures/colored-sphere.png
figures/density-cloud.png
figures/raw-vs-density-channels.png
figures/directional-vs-axial.png
```

The last file is emitted only when the validated axial CSV exists. Exact-node
scatter uses `scatter(nodes, T.intensity_raw, 'complete', ...)`; sphere uses
`plot3d(rawField, 'resolution', 1 * degree)`; density uses
`scatter(densityVectors, 'complete', ...)`; channel comparison uses identical
camera and limits for `intensity_raw` and `density_weight`; directional/axial
uses identical camera and raw-intensity limits. A sixth
`forsterite-s2-mtex-preview.png` is a labeled contact sheet of the available
panels. All files use `.partial.png` names until `exportgraphics` completes,
then rename atomically.

Write `diagnostics/mtex-result.json.partial`, including node count, normalized
node error, point count, seed, sampling/display resolutions, MATLAB version,
MTEX version, and completed stage names; rename only after every assertion and
artifact succeeds.

At the end of the file define a local `writeHeartbeat(path, stage, event)`
function that appends one compact JSON object plus newline, closes the file,
and therefore flushes every event to disk. Heartbeats occur before and after
startup, load, triangulation, node evaluation, density sampling, and figure
export.

- [ ] **Step 6: Integrate script bytes into the staged bundle**

`stage_spherical_bundle()` calls `generate_mtex_script()` exactly once and
writes its UTF-8 bytes to `forsterite-s2-mtex.m` before the ledger hashes the
script. Update the bundle inventory test so its final required base files equal
Task 3's `BASE_FILES | {"forsterite-s2-mtex.m"}`. No bundle or runner code
edits MATLAB after staging.

- [ ] **Step 7: Run script-generation, bundle tests, and commit**

Run:

```bash
uv run pytest tests/unit/test_spherical_intensity_mtex_script.py tests/unit/test_spherical_intensity_bundle.py -q
uv run ruff check src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_mtex_script.py
```

Expected: deterministic script assertions and the updated exact bundle
inventory pass without invoking MATLAB.

Set `KIKU-T022` to `done`, check its criteria, and add the generator test to
`evidence`.

```bash
git add src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_mtex_script.py tests/unit/test_spherical_intensity_bundle.py docs/work/KIKU-T022.md
git commit -m "feat: generate exact-node MTEX bridge"
```

---

### Task 5: Bounded MATLAB/MTEX Runner and Derivative Validation (`KIKU-T023`)

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/mtex_runner.py`
- Create: `tests/unit/test_spherical_intensity_mtex_runner.py`
- Create: `tests/integration/test_spherical_intensity_mtex.py`
- Modify: `src/kikuchi_lab/spherical_intensity/bundle.py`
- Modify: `src/kikuchi_lab/spherical_intensity/__init__.py`
- Modify: `pyproject.toml`
- Modify: `docs/work/KIKU-T023.md`

**Interfaces:**
- Consumes: staged bundle, selected profile, optional explicit MATLAB and MTEX paths.
- Produces: `MtexRuntime`, `MtexRunResult`, `discover_mtex_runtime()`, and `run_mtex_bridge()`.

- [ ] **Step 1: Write failing runtime discovery and fast observed-process tests**

```python
def executable_file(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def fake_mtex_root(path: Path, *, version: str) -> Path:
    path.mkdir(parents=True)
    (path / "startup_mtex.m").write_text("% fixture\n", encoding="utf-8")
    (path / "VERSION").write_text(version + "\n", encoding="utf-8")
    return path


def test_runtime_discovery_prefers_explicit_paths(tmp_path: Path) -> None:
    matlab = executable_file(tmp_path / "matlab")
    root = fake_mtex_root(tmp_path / "mtex", version="mtex-6.1.1")
    runtime = discover_mtex_runtime(
        matlab_executable=matlab,
        mtex_root=root,
        expected_mtex_version="mtex-6.1.1",
    )
    assert runtime.executable == matlab.resolve()
    assert runtime.root == root.resolve()
    assert runtime.expected_version == "mtex-6.1.1"


def test_observed_process_times_out_and_retains_last_heartbeat(tmp_path: Path) -> None:
    heartbeat = tmp_path / "progress.jsonl"
    command = [
        sys.executable,
        "-c",
        (
            "import pathlib,time; "
            f"p=pathlib.Path({str(heartbeat)!r}); "
            "p.write_text('{\"stage\":\"triangulation\",\"event\":\"start\"}\\n'); "
            "time.sleep(5)"
        ),
    ]
    result = _run_observed_process(
        command,
        cwd=tmp_path,
        heartbeat_path=heartbeat,
        stdout_path=tmp_path / "stdout.log",
        timeout_seconds=0.15,
        poll_interval_seconds=0.02,
        terminate_grace_seconds=0.1,
    )
    assert result.status == "timed-out"
    assert result.last_stage == "triangulation"
    assert result.elapsed_seconds < 1.0
    assert (tmp_path / "stdout.log").is_file()
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_spherical_intensity_mtex_runner.py -q`

Expected: missing runner module.

- [ ] **Step 3: Implement deterministic runtime discovery**

```python
@dataclass(frozen=True)
class MtexRuntime:
    executable: Path
    root: Path
    expected_version: str


@dataclass(frozen=True)
class MtexRunResult:
    status: Literal["passed", "unavailable", "failed", "timed-out"]
    command: tuple[str, ...]
    normalized_error: str | None
    metrics: Mapping[str, object]
    produced_files: tuple[str, ...]
    last_stage: str | None
    elapsed_seconds: float

    @classmethod
    def unavailable(cls, message: str) -> "MtexRunResult":
        return cls(
            status="unavailable",
            command=(),
            normalized_error=message,
            metrics={},
            produced_files=(),
            last_stage=None,
            elapsed_seconds=0.0,
        )


def discover_mtex_runtime(
    *,
    matlab_executable: str | Path | None = None,
    mtex_root: str | Path | None = None,
    expected_mtex_version: str = "mtex-6.1.1",
) -> MtexRuntime:
    matlab_candidates = [
        matlab_executable,
        os.environ.get("KIKUCHI_MATLAB"),
        shutil.which("matlab"),
        *_natural_sorted_matlab_app_candidates(),
    ]
    root_candidates = [mtex_root, os.environ.get("KIKUCHI_MTEX_ROOT")]
    executable = _first_executable(matlab_candidates)
    root = _first_mtex_root(root_candidates, expected_mtex_version)
    return MtexRuntime(executable, root, expected_mtex_version)
```

`_first_mtex_root()` requires `startup_mtex.m` and `VERSION`; stripped VERSION
content must exactly equal `expected_mtex_version`. Runtime discovery is
filesystem-only and does not launch MATLAB. If discovery fails, raise one
`MtexUnavailableError` listing which required resource was absent, without a
traceback at the CLI boundary.

- [ ] **Step 4: Implement one bounded observed process**

Use an argument list, `start_new_session=True`, and direct log file handles so
large MATLAB output cannot deadlock a pipe.

```python
def _run_observed_process(
    command: Sequence[str],
    *,
    cwd: Path,
    heartbeat_path: Path,
    stdout_path: Path,
    timeout_seconds: float,
    environment: Mapping[str, str] | None = None,
    poll_interval_seconds: float = 0.25,
    terminate_grace_seconds: float = 5.0,
) -> ObservedProcessResult:
    started = time.monotonic()
    with stdout_path.open("wb") as output:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=None if environment is None else dict(environment),
        )
        timed_out = False
        while process.poll() is None:
            if time.monotonic() - started >= timeout_seconds:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=terminate_grace_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            time.sleep(poll_interval_seconds)
    return _observed_result(
        process.returncode,
        timed_out=timed_out,
        elapsed_seconds=time.monotonic() - started,
        heartbeat_path=heartbeat_path,
        stdout_path=stdout_path,
    )
```

The wall clock is authoritative. Heartbeats identify the last stage but do not
create a second stale-heartbeat timeout. There is no retry loop.

- [ ] **Step 5: Implement MTEX invocation and output validation**

```python
def run_mtex_bridge(
    runtime: MtexRuntime,
    *,
    bundle_dir: Path,
    profile: SphericalProfile,
) -> MtexRunResult:
    environment = os.environ.copy()
    environment["KIKUCHI_MTEX_ROOT"] = str(runtime.root)
    command = (
        str(runtime.executable),
        "-batch",
        "run('forsterite-s2-mtex.m')",
    )
    observed = _run_observed_process(
        command,
        cwd=bundle_dir,
        heartbeat_path=bundle_dir / "diagnostics/mtex-progress.jsonl",
        stdout_path=bundle_dir / "diagnostics/mtex-stdout.log",
        timeout_seconds=profile.timeout_seconds,
        environment=environment,
    )
    return _validate_mtex_outputs(bundle_dir, command, observed, runtime, profile)
```

Add the `environment` parameter to `_run_observed_process()` and pass it to
`Popen`. On success, validate:

- result JSON parses and reports the requested point count, seed, resolution,
  `mtex-6.1.1`, a MATLAB version, and node error within `1e-8`;
- density CSV header is `x,y,z`, has exactly the requested row count, contains
  finite unit vectors, and hashes after validation;
- preview PNG is nonempty and decodable;
- no `.partial` output remains.

On nonzero exit or timeout, move any `.partial` derivatives into
`diagnostics/quarantine/`, return status `failed` or `timed-out`, record the
last stage and normalized error, and leave the Python field artifacts intact.

- [ ] **Step 6: Register and write an explicitly enabled local integration test**

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
  "mtex: requires explicit KIKUCHI_RUN_MTEX=1 plus local MATLAB and MTEX 6.1.1",
]
```

```python
@pytest.mark.mtex
def test_local_mtex_smoke_bundle_has_exact_nodes_cloud_and_preview(tmp_path: Path) -> None:
    if os.environ.get("KIKUCHI_RUN_MTEX") != "1":
        pytest.skip("set KIKUCHI_RUN_MTEX=1 for the bounded local MTEX smoke test")
    runtime = discover_mtex_runtime()
    recipe = spherical_recipe(half_size=2)
    stage = stage_spherical_bundle(
        tmp_path, small_spherical_build(half_size=2), recipe, fixture_source()
    )
    result = run_mtex_bridge(
        runtime, bundle_dir=stage.staging_path, profile=recipe.profile
    )
    assert result.status == "passed"
    assert result.metrics["node_normalized_error"] <= 1e-8
    assert result.metrics["point_count"] == 10_000
    assert set(result.produced_files) == {
        "forsterite-s2-density-vectors.csv",
        "forsterite-s2-mtex-preview.png",
        "diagnostics/mtex-result.json",
        "figures/exact-node-scatter.png",
        "figures/colored-sphere.png",
        "figures/density-cloud.png",
        "figures/raw-vs-density-channels.png",
        "figures/directional-vs-axial.png",
    }
```

- [ ] **Step 7: Run fast runner tests, optional smoke integration, and commit**

Run:

```bash
uv run pytest tests/unit/test_spherical_intensity_mtex_runner.py tests/unit/test_spherical_intensity_mtex_script.py -q
uv run ruff check src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_mtex_runner.py tests/integration/test_spherical_intensity_mtex.py
```

Expected: the synthetic timeout and success processes finish in under one
second; no MATLAB process launches.

Then, only when explicitly enabled:

```bash
KIKUCHI_MATLAB=/Applications/MATLAB_R2025b.app/bin/matlab \
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
KIKUCHI_RUN_MTEX=1 \
uv run pytest -m mtex tests/integration/test_spherical_intensity_mtex.py -q
```

Expected: one smoke test passes within `300` seconds. On timeout, stop; do not
retry or run acceptance.

Set `KIKU-T023` to `done` only after the unit runner tests and one bounded local
smoke pass. Check its criteria and add both test files plus the retained local
smoke diagnostics to `evidence`.

```bash
git add pyproject.toml src/kikuchi_lab/spherical_intensity tests/unit/test_spherical_intensity_mtex_runner.py tests/integration/test_spherical_intensity_mtex.py docs/work/KIKU-T023.md
git commit -m "feat: run bounded MTEX density validation"
```

---

### Task 6: Workflow, CLI, Forsterite Acceptance Figures, and Closure (`KIKU-T024`)

**Files:**
- Create: `src/kikuchi_lab/workflows/spherical_intensity.py`
- Create: `tests/integration/test_spherical_intensity_workflow.py`
- Create: `docs/acceptance/spherical-intensity-mtex.md`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`
- Modify: `docs/incubator/interactive-spherical-view.md`
- Modify: `docs/work/KIKU-T024.md`
- Modify after human acceptance: `docs/work/KIKU-F003.md`

**Interfaces:**
- Consumes: completed `KIKU-F002`, S2 mapping, bundle staging, optional MTEX runtime, and selected profile.
- Produces: `SphericalIntensityRunResult`, `export_spherical_intensity()`, and CLI command `export-spherical-intensity`.

- [ ] **Step 1: Write failing workflow and CLI tests**

```python
def test_smoke_workflow_overrides_only_source_half_size_and_promotes_python_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = {}

    def fake_simulate(record, recipe):
        observed["half_size"] = recipe.half_size
        return small_kinematical_simulation(), object()

    monkeypatch.setattr(
        "kikuchi_lab.workflows.spherical_intensity.simulate_kinematical_arrays",
        fake_simulate,
    )
    result = export_spherical_intensity(
        recipe_path=RECIPE,
        output_root=tmp_path / "runs",
        profile="smoke",
        run_mtex=False,
    )
    assert observed["half_size"] == 32
    assert result.profile == "smoke"
    assert result.mtex_status == "not-requested"
    assert result.path.is_dir()


def test_export_spherical_cli_prints_retained_bundle_on_mtex_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = SimpleNamespace(
        run_id="s2-run-0123456789abcdef",
        path=tmp_path / "s2-run-0123456789abcdef",
        field_id="s2-field-fedcba9876543210",
        profile="smoke",
        node_count=97,
        axial_available=True,
        mtex_status="timed-out",
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.export_spherical_intensity", lambda **kwargs: result
    )
    status = main(
        [
            "export-spherical-intensity",
            "--recipe",
            str(RECIPE),
            "--output",
            str(tmp_path / "runs"),
            "--profile",
            "smoke",
            "--run-mtex",
        ]
    )
    captured = capsys.readouterr()
    assert status == 1
    assert json.loads(captured.out)["path"] == str(result.path)
    assert "MTEX validation timed-out" in captured.err
```

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/integration/test_spherical_intensity_workflow.py tests/unit/test_cli.py::test_export_spherical_cli_prints_retained_bundle_on_mtex_failure -q`

Expected: missing workflow and argparse command.

- [ ] **Step 3: Implement the bounded source-to-bundle workflow**

```python
@dataclass(frozen=True)
class SphericalIntensityRunResult:
    run_id: str
    path: Path
    field_id: str
    profile: ProfileName
    node_count: int
    axial_available: bool
    mtex_status: str


def export_spherical_intensity(
    *,
    recipe_path: str | Path,
    output_root: str | Path,
    profile: ProfileName,
    run_mtex: bool,
    matlab_executable: str | Path | None = None,
    mtex_root: str | Path | None = None,
) -> SphericalIntensityRunResult:
    spherical_path = Path(recipe_path).resolve()
    recipe = load_spherical_intensity_recipe(spherical_path, profile=profile)
    kinematical_path = (
        spherical_path.parent / recipe.source_kinematical_recipe
    ).resolve()
    kinematical = load_kinematical_recipe(kinematical_path)
    bounded_kinematical = replace(
        kinematical, half_size=recipe.profile.half_size, hemisphere="both"
    )
    source_path = (kinematical_path.parent / bounded_kinematical.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    simulation, _context = simulate_kinematical_arrays(source, bounded_kinematical)
    build = build_spherical_intensity(simulation, source, recipe)
    stage = stage_spherical_bundle(output_root, build, recipe, source)
    mtex_result = None
    if run_mtex:
        try:
            runtime = discover_mtex_runtime(
                matlab_executable=matlab_executable,
                mtex_root=mtex_root,
                expected_mtex_version=recipe.expected_mtex_version,
            )
            mtex_result = run_mtex_bridge(
                runtime, bundle_dir=stage.staging_path, profile=recipe.profile
            )
        except MtexUnavailableError as error:
            mtex_result = MtexRunResult.unavailable(str(error))
    bundle = finalize_spherical_bundle(stage, mtex_result=mtex_result)
    return SphericalIntensityRunResult(
        run_id=bundle.run_id,
        path=bundle.path,
        field_id=build.field.field_id,
        profile=profile,
        node_count=build.field.xyz.shape[0],
        axial_available=build.axial_field is not None,
        mtex_status=bundle.mtex_status,
    )
```

The workflow never selects `half_size = 256` or `1024`, never calls the
dynamical simulator, and never modifies a `KIKU-F002` bundle. If runtime
discovery or MATLAB execution fails after Python staging, normalize the result,
finalize the valid Python bundle with failed status, then return it.

- [ ] **Step 4: Add the CLI command and normalized exit behavior**

Add exact arguments:

```text
kikuchi-lab export-spherical-intensity
  --recipe PATH
  --output PATH
  --profile {smoke,acceptance}
  [--run-mtex]
  [--matlab PATH]
  [--mtex-root PATH]
```

Default profile is `smoke`; MTEX is not run unless `--run-mtex` is present.
Acceptance profile without `--run-mtex` is rejected before simulation. Print
canonical JSON with `run_id`, `path`, `field_id`, `profile`, `node_count`,
`axial_available`, and `mtex_status`. Return `0` for `not-requested` or
`passed`, and `1` for requested `unavailable`, `failed`, or `timed-out`, while
retaining and printing the bundle path. Catch `OSError`, `ValueError`, bundle,
and MTEX errors without a traceback.

- [ ] **Step 5: Prove workflow determinism and existing-product isolation**

Run:

```bash
uv run pytest tests/integration/test_spherical_intensity_workflow.py tests/unit/test_cli.py -q
uv run pytest tests/unit/test_kinematical_bundle.py tests/integration/test_kinematical_workflow.py tests/unit/test_artifact_bundle.py tests/integration/test_final_workflow.py -q
```

Expected: repeated synthetic workflow artifacts hash identically; existing
kinematical and dynamical bundle inventories require no changes.

- [ ] **Step 6: Run all fast verification gates before external work**

```bash
uv run pytest -m "not slow and not gpu and not mtex" -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
git diff --check
```

Expected: all tests pass, Ruff is clean, the tracker validates, and no
whitespace errors are reported. Do not launch MATLAB if any gate fails.

- [ ] **Step 7: Run and inspect the bounded smoke profile**

```bash
KIKUCHI_MATLAB=/Applications/MATLAB_R2025b.app/bin/matlab \
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
uv run kikuchi-lab export-spherical-intensity \
  --recipe recipes/spherical/forsterite-s2-intensity.yml \
  --output local/runs/spherical-intensity \
  --profile smoke \
  --run-mtex
```

Expected: one promoted bundle within `300` seconds, `mtex_status=passed`, exact-
node error at most `1e-8`, `10000` density vectors, and a readable preview. If
the command times out or fails, inspect `diagnostics/mtex-progress.jsonl` and
`diagnostics/mtex-stdout.log`, record the cause, and stop. Do not retry or run
acceptance.

- [ ] **Step 8: Run the acceptance profile only after smoke passes**

```bash
KIKUCHI_MATLAB=/Applications/MATLAB_R2025b.app/bin/matlab \
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
uv run kikuchi-lab export-spherical-intensity \
  --recipe recipes/spherical/forsterite-s2-intensity.yml \
  --output local/runs/spherical-intensity \
  --profile acceptance \
  --run-mtex
```

Expected: one promoted bundle within `900` seconds, `mtex_status=passed`, exact-
node error at most `1e-8`, `100000` density vectors, and no `.partial` file. Do
not advance to `half_size = 256` or `1024`.

- [ ] **Step 9: Write and present acceptance evidence**

`docs/acceptance/spherical-intensity-mtex.md` records:

- source, recipe, field, bundle, and artifact IDs/hashes;
- node, inside, equator, seam, antipodal, and axial metrics;
- smoke and acceptance stage durations and last heartbeat;
- MATLAB and MTEX versions;
- exact-node residual, density seed/count/resolution, and output hash;
- explicit `no blur / no harmonic approximation` statement;
- paths to raw exact-node scatter, fixed 3D sphere, density cloud, channel
  comparison, and directional-versus-axial figures; and
- the explicit decision that `half_size = 256/1024` remains gated.

Present the five figures at fit-to-window and 100 percent. This is the one
human gate: stop and request acceptance or changes. Do not mark `KIKU-T024` or
`KIKU-F003` done before approval.

- [ ] **Step 10: Accept tracker items and commit after human approval**

After approval, set `KIKU-T024` and `KIKU-F003` to `done`, check their criteria,
add acceptance evidence paths, update the epic and tracker summary, and note in
`docs/incubator/interactive-spherical-view.md` that the validated full-sphere
field now satisfies its source-field promotion dependency.

```bash
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
git add src/kikuchi_lab/workflows src/kikuchi_lab/cli/main.py src/kikuchi_lab/spherical_intensity tests/integration/test_spherical_intensity_workflow.py tests/unit/test_cli.py docs/acceptance/spherical-intensity-mtex.md docs/incubator/interactive-spherical-view.md docs/work
git commit -m "feat: deliver forsterite spherical intensity proof"
```

Expected: tracker validation succeeds, the feature is closed with reviewed
evidence, and the branch remains local.

---

## Final Verification

After all task reviews and the human visual gate:

```bash
uv run pytest -m "not slow and not gpu and not mtex" -q
KIKUCHI_MATLAB=/Applications/MATLAB_R2025b.app/bin/matlab \
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
KIKUCHI_RUN_MTEX=1 \
uv run pytest -m mtex tests/integration/test_spherical_intensity_mtex.py -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
git diff --check
git status --short
```

Expected: every command succeeds, the MTEX smoke test remains bounded, no
unexpected file is modified, and the worktree is clean.
