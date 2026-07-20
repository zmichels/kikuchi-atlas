# Oriented Spherical Ice Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic Ice Ih proof that rotates the exact directional master field with active crystal-to-sample Bunge `(17, 31, 43)` degrees, then derives fixed specimen-frame hemisphere and full-sphere figures without rotating a flat image or introducing blur.

**Architecture:** The current both-hemisphere Ice master is mapped once to the project-owned exact `S2` field. A small orientation core applies `s = G_cs c` to those nodes and records a complete frame ledger; a separate pullback sampler evaluates `I_sample(s) = I_crystal(G_cs^-1 s)` on fixed specimen grids and sphere meshes. Scientific arrays, presentation luminance, render bytes, and publication identities remain separate, content-addressed products.

**Tech Stack:** Python 3.11, NumPy, SciPy-free vectorized bilinear interpolation, orix, kikuchipy/diffsims, Matplotlib, Pillow, PyYAML, pytest, the existing `kikuchi_lab` identity and atomic-bundle conventions.

## Global Constraints

- The canonical input is the Ice Ih both-hemisphere crystal-frame master, never a rendered PNG.
- The public orientation is active crystal-to-sample Bunge ZXZ in degrees with sample axes ordered `[RD, TD, ND]`.
- Exact node rotation is `s = G_cs c`; fixed-frame display pullback is `I_sample(s) = I_crystal(G_cs^-1 s)`.
- Node count, node order, raw intensity, normalized intensity, density weight, source row, source column, and source hemisphere remain unchanged by orientation.
- The authoritative output is a compressed exact-node NPZ plus a plain JSON orientation ledger; figures are display derivatives.
- Scientific raw intensity is never tone-mapped in place. The field-led luminance channel is explicitly `presentation_only`.
- Presentation parameters remain overlap threshold `0.22`, weight exponent `2.0`, normalization percentile `99.5`, optical gain `0.38`, and ceiling `0.985`.
- Both center and boundary vector-overlay layers must be disabled.
- No spatial blur, glow, denoising, morphology, image-space rotation, or interpolation fallback is permitted.
- Reprojection uses explicit bilinear interpolation between simulator nodes and bounded row tiles; identity at source grid size uses exact source-array correspondence.
- Figures use monochrome field-led luminance on `#101519`, a circular display rim, and no linework over the art figures.
- A `480 px`, `half_size=32` smoke bundle capped at `180 s` must finish before a `2400 px`, `half_size=512` review bundle capped at `600 s` starts.
- The slice excludes detector projection, reflector-regeneration parity, orientation galleries, indexed-EBSD orientations, ODF accumulation, interactive 3D, print geometry, quartz, phase generalization, dynamical simulation, and experimental matching.
- Preserve all pre-existing uncommitted spherical-intensity/MTEX edits. Do not stage or rewrite `src/kikuchi_lab/spherical_intensity/__init__.py`, `src/kikuchi_lab/spherical_intensity/mtex_script.py`, `pyproject.toml`, `pytest.ini`, or the existing MTEX tests and examples.

---

## File Structure

### New production files

- `src/kikuchi_lab/spherical_intensity/orientation.py` — strict oriented-proof recipe, profile selection, orientation-matrix construction, and plain orientation ledger.
- `src/kikuchi_lab/spherical_intensity/rotation.py` — immutable oriented-field wrapper and exact node rotation with channel-invariance checks.
- `src/kikuchi_lab/spherical_intensity/reprojection.py` — fixed specimen stereographic grids, inverse rotation, hemisphere ownership, and bounded direct bilinear sampling.
- `src/kikuchi_lab/spherical_intensity/presentation.py` — reusable field-led tone and exact axial-overlap evaluation for arbitrary crystal directions.
- `src/kikuchi_lab/spherical_intensity/oriented_render.py` — deterministic hemisphere, comparison, sphere, and axis-diagnostic PNG bytes.
- `src/kikuchi_lab/spherical_intensity/oriented_bundle.py` — deterministic NPZ/JSON/PNG inventory and atomic no-replace publication.
- `src/kikuchi_lab/workflows/oriented_spherical.py` — bounded Ice orchestration and smoke-before-review gate.
- `recipes/spherical/ice-ih-s2-intensity.yml` — reusable Ice exact-field mapping parameters.
- `recipes/spherical/ice-ih-oriented-s2-proof.yml` — the approved identity/oriented proof and bounded render profiles.

### Modified production files

- `src/kikuchi_lab/workflows/__init__.py` — export only the new public workflow result and entry point.
- `src/kikuchi_lab/cli/main.py` — add `render-oriented-spherical` with `smoke` and `review` profiles.

### New tests and acceptance evidence

- `tests/unit/test_oriented_spherical_recipe.py`
- `tests/scientific/test_oriented_spherical_rotation.py`
- `tests/scientific/test_oriented_spherical_reprojection.py`
- `tests/scientific/test_oriented_spherical_presentation.py`
- `tests/unit/test_oriented_spherical_render.py`
- `tests/unit/test_oriented_spherical_bundle.py`
- `tests/integration/test_oriented_ice_spherical.py`
- `docs/acceptance/ice-ih-oriented-spherical-master.md`

Do not add exports to the currently modified `spherical_intensity/__init__.py`; execution code imports the focused modules directly.

---

### Task 1: Strict Oriented-Proof Recipe and Ice Field Recipe

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/orientation.py`
- Create: `recipes/spherical/ice-ih-s2-intensity.yml`
- Create: `recipes/spherical/ice-ih-oriented-s2-proof.yml`
- Test: `tests/unit/test_oriented_spherical_recipe.py`

**Interfaces:**
- Consumes: `kikuchi_lab.model.recipes.Orientation`, `kikuchi_lab.model.identity.stable_id`.
- Produces: `OrientedProfile`, `OrientedSphericalRecipe`, `load_oriented_spherical_recipe(path, *, profile)`, `orientation_matrix(orientation)`, and `orientation_ledger(orientation)`.

- [ ] **Step 1: Write the failing contract and strict-loader tests**

```python
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.spherical_intensity.orientation import (
    load_oriented_spherical_recipe,
)


RECIPE = Path("recipes/spherical/ice-ih-oriented-s2-proof.yml")


def test_oriented_ice_recipe_has_approved_orientation_and_profiles() -> None:
    smoke = load_oriented_spherical_recipe(RECIPE, profile="smoke")
    review = load_oriented_spherical_recipe(RECIPE, profile="review")
    assert smoke.orientation.euler_bunge_deg == (17.0, 31.0, 43.0)
    assert smoke.orientation.frame == "crystal_to_sample"
    assert smoke.profile.source_half_size == 32
    assert smoke.profile.figure_size_px == 480
    assert smoke.profile.timeout_seconds == 180
    assert review.profile.source_half_size == 512
    assert review.profile.figure_size_px == 2400
    assert review.profile.timeout_seconds == 600
    assert review.interpolation == "bilinear"
    assert review.spatial_filter == "none"
    assert review.background_color == "#101519"


def test_oriented_recipe_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload["blur_radius"] = 1
    candidate = tmp_path / "invalid.yml"
    candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="fields differ"):
        load_oriented_spherical_recipe(candidate, profile="smoke")


def test_oriented_recipe_rejects_noncanonical_display_operations(tmp_path: Path) -> None:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload["spatial_filter"] = "gaussian"
    candidate = tmp_path / "invalid.yml"
    candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="spatial_filter must be none"):
        load_oriented_spherical_recipe(candidate, profile="smoke")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `uv run pytest tests/unit/test_oriented_spherical_recipe.py -q`

Expected: collection fails with `ModuleNotFoundError` for `kikuchi_lab.spherical_intensity.orientation`.

- [ ] **Step 3: Implement immutable recipe contracts and exact schema parsing**

```python
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np
import yaml
from importlib.metadata import version
from orix.quaternion import Rotation as OrixRotation

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)


OrientedProfileName = Literal["smoke", "review"]


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"oriented recipe {field} must be non-empty text")
    if Path(value).is_absolute():
        raise ValueError(f"oriented recipe {field} must be a relative path")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"oriented recipe {field} must be non-empty text")
    return value


@dataclass(frozen=True)
class OrientedProfile:
    name: OrientedProfileName
    source_half_size: int
    figure_size_px: int
    sphere_longitude_count: int
    sphere_latitude_count: int
    tile_rows: int
    timeout_seconds: int

    def __post_init__(self) -> None:
        for name in (
            "source_half_size",
            "figure_size_px",
            "sphere_longitude_count",
            "sphere_latitude_count",
            "tile_rows",
            "timeout_seconds",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"oriented profile {name} must be a positive integer")
        if self.sphere_longitude_count % 2 == 0 or self.sphere_latitude_count % 2 == 0:
            raise ValueError("oriented sphere grid counts must be odd")
        if self.tile_rows > self.figure_size_px:
            raise ValueError("oriented tile_rows cannot exceed figure_size_px")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OrientedSphericalRecipe:
    schema_version: int
    name: str
    source_spherical_recipe: str
    presentation_recipe: str
    orientation: Orientation
    profile: OrientedProfile
    interpolation: str
    spatial_filter: str
    background_color: str

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("oriented recipe schema_version must be integer 1")
        if self.interpolation != "bilinear":
            raise ValueError("oriented recipe interpolation must be bilinear")
        if self.spatial_filter != "none":
            raise ValueError("oriented recipe spatial_filter must be none")
        if self.background_color.lower() != "#101519":
            raise ValueError("oriented recipe background_color must be #101519")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_spherical_recipe": self.source_spherical_recipe,
            "presentation_recipe": self.presentation_recipe,
            "orientation": self.orientation.to_dict(),
            "profile": self.profile.to_dict(),
            "interpolation": self.interpolation,
            "spatial_filter": self.spatial_filter,
            "background_color": self.background_color,
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


def orientation_matrix(orientation: Orientation) -> np.ndarray:
    basis = np.eye(3, dtype=np.float64)
    matrix = np.column_stack(
        [transform_crystal_direction_to_sample(axis, orientation) for axis in basis]
    )
    if not np.allclose(matrix.T @ matrix, np.eye(3), rtol=0.0, atol=5e-13):
        raise ValueError("orientation matrix must be orthonormal")
    if not math.isclose(float(np.linalg.det(matrix)), 1.0, rel_tol=0.0, abs_tol=5e-13):
        raise ValueError("orientation matrix must be right-handed")
    return matrix


def load_oriented_spherical_recipe(
    path: str | Path, *, profile: OrientedProfileName
) -> OrientedSphericalRecipe:
    recipe_path = Path(path)
    try:
        root = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("oriented recipe YAML is invalid") from None
    required = {
        "schema_version", "name", "source_spherical_recipe", "presentation_recipe",
        "orientation", "profiles", "interpolation", "spatial_filter", "background_color",
    }
    if not isinstance(root, dict) or set(root) != required:
        raise ValueError("oriented recipe top-level fields differ from the schema")
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("oriented recipe schema_version must be integer 1")
    if profile not in {"smoke", "review"}:
        raise ValueError("oriented profile must be smoke or review")
    if not isinstance(root["profiles"], dict) or set(root["profiles"]) != {"smoke", "review"}:
        raise ValueError("oriented recipe profiles fields differ from the schema")
    profile_data = root["profiles"][profile]
    profile_fields = {
        "source_half_size", "figure_size_px", "sphere_longitude_count",
        "sphere_latitude_count", "tile_rows", "timeout_seconds",
    }
    if not isinstance(profile_data, dict) or set(profile_data) != profile_fields:
        raise ValueError("oriented profile fields differ from the schema")
    expected_bounds = {
        "smoke": (32, 480, 180),
        "review": (512, 2400, 600),
    }
    observed_bounds = (
        profile_data["source_half_size"],
        profile_data["figure_size_px"],
        profile_data["timeout_seconds"],
    )
    if observed_bounds != expected_bounds[profile]:
        raise ValueError(f"oriented {profile} size/time bounds differ from the approved proof")
    orientation_data = root["orientation"]
    if not isinstance(orientation_data, dict) or set(orientation_data) != {
        "euler_bunge_deg", "frame"
    }:
        raise ValueError("oriented orientation fields differ from the schema")
    return OrientedSphericalRecipe(
        schema_version=root["schema_version"],
        name=_text(root["name"], "name"),
        source_spherical_recipe=_relative_path(
            root["source_spherical_recipe"], "source_spherical_recipe"
        ),
        presentation_recipe=_relative_path(
            root["presentation_recipe"], "presentation_recipe"
        ),
        orientation=Orientation(
            tuple(float(value) for value in orientation_data["euler_bunge_deg"]),
            frame=str(orientation_data["frame"]),
        ),
        profile=OrientedProfile(name=cast(OrientedProfileName, profile), **profile_data),
        interpolation=str(root["interpolation"]),
        spatial_filter=str(root["spatial_filter"]),
        background_color=str(root["background_color"]),
    )
```

Keep the parser strict: reject absolute referenced paths, booleans in numeric fields, non-finite Euler values through `Orientation`, profile names other than `smoke|review`, even sphere counts, `tile_rows > figure_size_px`, and values other than the fixed size/time pairs `(32,480,180)` and `(512,2400,600)`.

- [ ] **Step 4: Add the reusable Ice field recipe and approved oriented recipe**

```yaml
# recipes/spherical/ice-ih-s2-intensity.yml
schema_version: 1
name: ice-ih-s2-intensity
source_kinematical_recipe: ../kinematical/ice-ih-oxygen-quiet-proof.yml
profiles:
  smoke: {half_size: 32, point_count: 10000, sampling_resolution_deg: 1.0, timeout_seconds: 180}
  acceptance: {half_size: 128, point_count: 100000, sampling_resolution_deg: 0.25, timeout_seconds: 600}
density: {name: quiet-density-v1, low_percentile: 5.0, high_percentile: 99.85, exponent: 1.5}
tolerances:
  disk_epsilon_multiplier: 32
  unit_norm_max: 5.0e-13
  stereo_round_trip_rad_max: 1.0e-10
  equator_normalized_max: 1.0e-6
  axial_normalized_rms_max: 1.0e-6
  axial_normalized_max: 1.0e-5
  mtex_node_normalized_max: 1.0e-8
rng_seed: 20260716
rng_generator: twister
csv_float_format: "%.17g"
display_resolution_deg: 1.0
emit_axial: false
expected_mtex_version: mtex-6.1.1
```

```yaml
# recipes/spherical/ice-ih-oriented-s2-proof.yml
schema_version: 1
name: ice-ih-oriented-s2-proof
source_spherical_recipe: ice-ih-s2-intensity.yml
presentation_recipe: ../presentation/ice-ih-near-depth-stepped-field-led.yml
orientation: {euler_bunge_deg: [17.0, 31.0, 43.0], frame: crystal_to_sample}
profiles:
  smoke:
    source_half_size: 32
    figure_size_px: 480
    sphere_longitude_count: 181
    sphere_latitude_count: 91
    tile_rows: 32
    timeout_seconds: 180
  review:
    source_half_size: 512
    figure_size_px: 2400
    sphere_longitude_count: 721
    sphere_latitude_count: 361
    tile_rows: 48
    timeout_seconds: 600
interpolation: bilinear
spatial_filter: none
background_color: "#101519"
```

- [ ] **Step 5: Complete the orientation ledger and its tests**

Add `orientation_ledger(orientation)` with this exact plain-data shape:

```python
def orientation_ledger(orientation: Orientation) -> dict[str, object]:
    matrix = orientation_matrix(orientation)
    rotation = OrixRotation.from_euler(
        orientation.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )
    return {
        "schema_version": 1,
        "orientation_id": orientation.orientation_id,
        "euler_bunge_deg": list(orientation.euler_bunge_deg),
        "angle_units": "degree",
        "euler_convention": "Bunge ZXZ",
        "direction": "active crystal_to_sample",
        "equation_forward": "s = G_cs c",
        "equation_pullback": "I_sample(s) = I_crystal(G_cs^-1 s)",
        "input_frame": "crystal",
        "output_frame": "EDAX-TSL:RD-TD-ND",
        "output_axis_order": ["RD", "TD", "ND"],
        "matrix_G_cs": matrix.tolist(),
        "matrix_G_cs_inverse": matrix.T.tolist(),
        "quaternion_abcd": np.asarray(rotation.data[0], dtype=np.float64).tolist(),
        "quaternion_component_order": ["a", "b", "c", "d"],
        "determinant": float(np.linalg.det(matrix)),
        "orthonormal_max_error": float(np.max(np.abs(matrix.T @ matrix - np.eye(3)))),
        "implementation_owner": "kikuchi_lab.projection.kikuchipy_adapter",
        "implementation_versions": {
            "kikuchi-lab": version("kikuchi-lab"),
            "orix": version("orix"),
        },
    }
```

Test determinant, inverse, basis-column parity with `transform_crystal_direction_to_sample`, and stable `orientation_id`.

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run pytest tests/unit/test_oriented_spherical_recipe.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/orientation.py recipes/spherical/ice-ih-s2-intensity.yml recipes/spherical/ice-ih-oriented-s2-proof.yml tests/unit/test_oriented_spherical_recipe.py
git commit -m "feat: define oriented Ice spherical recipe"
```

---

### Task 2: Exact Active Rotation of the Canonical S2 Field

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/rotation.py`
- Test: `tests/scientific/test_oriented_spherical_rotation.py`

**Interfaces:**
- Consumes: `SphericalIntensityField`, `Orientation`, `orientation_matrix()`, and `orientation_ledger()`.
- Produces: `OrientedSphericalIntensityField` and `rotate_spherical_field(source, orientation)`.

- [ ] **Step 1: Write failing identity, invariance, and adapter-parity tests**

```python
import numpy as np

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)
from kikuchi_lab.spherical_intensity.rotation import rotate_spherical_field
from importlib import import_module


_fixtures = import_module("spherical_fixtures")


def test_identity_rotation_preserves_every_channel_exactly() -> None:
    source = _fixtures.small_spherical_build().field
    oriented = rotate_spherical_field(source, Orientation((0.0, 0.0, 0.0)))
    np.testing.assert_array_equal(oriented.field.xyz, source.xyz)
    for name in (
        "hemisphere", "source_row", "source_column", "intensity_raw",
        "intensity_normalized", "density_weight",
    ):
        np.testing.assert_array_equal(getattr(oriented.field, name), getattr(source, name))
        assert oriented.field.channel_sha256[name] == source.channel_sha256[name]


def test_arbitrary_rotation_moves_only_xyz_and_matches_adapter() -> None:
    source = _fixtures.small_spherical_build().field
    orientation = Orientation((17.0, 31.0, 43.0))
    oriented = rotate_spherical_field(source, orientation)
    expected = np.stack(
        [transform_crystal_direction_to_sample(vector, orientation) for vector in source.xyz]
    )
    np.testing.assert_allclose(oriented.field.xyz, expected, rtol=0.0, atol=5e-13)
    np.testing.assert_allclose(np.linalg.norm(oriented.field.xyz, axis=1), 1.0, rtol=0.0, atol=5e-13)
    assert oriented.field.channel_sha256["xyz"] != source.channel_sha256["xyz"]
    for name in ("intensity_raw", "intensity_normalized", "density_weight"):
        assert oriented.field.channel_sha256[name] == source.channel_sha256[name]
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/scientific/test_oriented_spherical_rotation.py -q`

Expected: collection fails because `spherical_intensity.rotation` does not exist.

- [ ] **Step 3: Implement the immutable oriented wrapper and exact rotation**

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation

from .contracts import SphericalIntensityField
from .orientation import orientation_ledger, orientation_matrix


@dataclass(frozen=True)
class OrientedSphericalIntensityField:
    source_field_id: str
    field: SphericalIntensityField
    orientation_id: str
    ledger: Mapping[str, object]
    product_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def rotate_spherical_field(
    source: SphericalIntensityField,
    orientation: Orientation,
) -> OrientedSphericalIntensityField:
    matrix = orientation_matrix(orientation)
    if orientation.euler_bunge_deg == (0.0, 0.0, 0.0):
        xyz = source.xyz
    else:
        xyz = source.xyz @ matrix.T
    round_trip = xyz @ matrix
    if not np.allclose(round_trip, source.xyz, rtol=0.0, atol=5e-13):
        raise ValueError("oriented field inverse rotation exceeds 5e-13")
    metadata = source.metadata_dict()
    metadata["frame"] = {
        "name": "EDAX-TSL:RD-TD-ND",
        "handedness": "right-handed",
        "vector_units": "dimensionless",
    }
    metadata["orientation"] = orientation_ledger(orientation)
    metadata["oriented_from"] = {
        "source_field_id": source.field_id,
        "source_xyz_sha256": source.channel_sha256["xyz"],
    }
    field = SphericalIntensityField.from_columns(
        xyz=xyz,
        hemisphere=source.hemisphere,
        source_row=source.source_row,
        source_column=source.source_column,
        intensity_raw=source.intensity_raw,
        intensity_normalized=source.intensity_normalized,
        density_weight=source.density_weight,
        metadata=metadata,
    )
    unchanged = (
        "hemisphere", "source_row", "source_column", "intensity_raw",
        "intensity_normalized", "density_weight",
    )
    if any(field.channel_sha256[name] != source.channel_sha256[name] for name in unchanged):
        raise ValueError("orientation changed a non-coordinate field channel")
    ledger = {
        **orientation_ledger(orientation),
        "source_field_id": source.field_id,
        "oriented_field_id": field.field_id,
        "channel_sha256_before": dict(source.channel_sha256),
        "channel_sha256_after": dict(field.channel_sha256),
        "maximum_inverse_error": float(np.max(np.abs(round_trip - source.xyz))),
    }
    product_id = stable_id("oriented-s2", plain_data(ledger))
    return OrientedSphericalIntensityField(
        source_field_id=source.field_id,
        field=field,
        orientation_id=orientation.orientation_id,
        ledger=ledger,
        product_id=product_id,
    )
```

- [ ] **Step 4: Add mutation, inversion, and metadata regression tests**

Assert all arrays reject assignment, `matrix.T` returns every rotated node to its source within `5e-13`, the non-identity product ID differs from identity, the ledger names `RD/TD/ND`, and no absolute filesystem path occurs in metadata.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run pytest tests/scientific/test_oriented_spherical_rotation.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/rotation.py tests/scientific/test_oriented_spherical_rotation.py
git commit -m "feat: rotate exact spherical intensity nodes"
```

---

### Task 3: Fixed Specimen-Frame Reprojection and Direct Bilinear Sampling

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/reprojection.py`
- Test: `tests/scientific/test_oriented_spherical_reprojection.py`

**Interfaces:**
- Consumes: a `(2, N, N)` upper/lower source channel, `Orientation`, hemisphere `upper|lower`, output size, tile size, and an optional deadline callback.
- Produces: `StereographicGrid`, `ReprojectedHemisphere`, `stereographic_grid_rows()`, `inverse_rotate_directions()`, `sample_stereographic_channel()`, and `reproject_hemisphere()`.

- [ ] **Step 1: Write failing exact-node and identity tests**

```python
import numpy as np

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.spherical_intensity.reprojection import (
    reproject_hemisphere,
    sample_stereographic_channel,
)


def indexed_master(size: int) -> np.ndarray:
    values = np.arange(2 * size * size, dtype=np.float32)
    return values.reshape(2, size, size)


def test_identity_returns_source_upper_and_lower_arrays_exactly() -> None:
    master = indexed_master(9)
    for index, hemisphere in enumerate(("upper", "lower")):
        result = reproject_hemisphere(
            master,
            Orientation((0.0, 0.0, 0.0)),
            hemisphere=hemisphere,
            size=9,
            tile_rows=3,
        )
        np.testing.assert_array_equal(result.values[result.valid], master[index][result.valid])
        assert result.ledger["identity_source_grid_fast_path"] is True


def test_bilinear_sampler_reproduces_exact_source_nodes() -> None:
    master = indexed_master(9)
    directions = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
    sampled, hemisphere_index = sample_stereographic_channel(master, directions)
    np.testing.assert_array_equal(sampled, [master[0, 4, 4], master[1, 4, 4]])
    np.testing.assert_array_equal(hemisphere_index, [0, 1])
```

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/scientific/test_oriented_spherical_reprojection.py -q`

Expected: collection fails because `spherical_intensity.reprojection` does not exist.

- [ ] **Step 3: Implement grid construction and inverse rotation**

```python
@dataclass(frozen=True)
class StereographicGrid:
    x: np.ndarray
    y: np.ndarray
    directions: np.ndarray
    valid: np.ndarray


def stereographic_grid(size: int, hemisphere: str) -> StereographicGrid:
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate)
    valid = x * x + y * y <= 1.0 + 32 * np.finfo(np.float64).eps
    pole = -1 if hemisphere == "upper" else 1
    directions = np.full((size, size, 3), np.nan, dtype=np.float64)
    directions[valid] = np.asarray(
        InverseStereographicProjection(pole=pole)
        .xy2vector(x[valid], y[valid])
        .data,
        dtype=np.float64,
    )
    return StereographicGrid(x=x, y=y, directions=directions, valid=valid)


def stereographic_grid_rows(
    size: int,
    hemisphere: str,
    row_start: int,
    row_stop: int,
) -> StereographicGrid:
    if not 0 <= row_start < row_stop <= size:
        raise ValueError("stereographic row tile is outside the output grid")
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate[row_start:row_stop])
    valid = x * x + y * y <= 1.0 + 32 * np.finfo(np.float64).eps
    pole = -1 if hemisphere == "upper" else 1
    directions = np.full((row_stop - row_start, size, 3), np.nan, dtype=np.float64)
    directions[valid] = np.asarray(
        InverseStereographicProjection(pole=pole)
        .xy2vector(x[valid], y[valid])
        .data,
        dtype=np.float64,
    )
    return StereographicGrid(x=x, y=y, directions=directions, valid=valid)


def inverse_rotate_directions(
    specimen_directions: np.ndarray,
    orientation: Orientation,
) -> np.ndarray:
    matrix = orientation_matrix(orientation)
    crystal = np.asarray(specimen_directions, dtype=np.float64) @ matrix
    if not np.isfinite(crystal).all():
        raise ValueError("inverse-oriented crystal directions must be finite")
    return crystal
```

- [ ] **Step 4: Implement explicit source projection and bilinear interpolation**

```python
def sample_stereographic_channel(
    source: np.ndarray,
    crystal_directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    master = np.asarray(source)
    directions = np.asarray(crystal_directions, dtype=np.float64)
    if master.ndim != 3 or master.shape[0] != 2 or master.shape[1] != master.shape[2]:
        raise ValueError("source channel must have shape (2, N, N)")
    if directions.ndim != 2 or directions.shape[1] != 3 or not np.isfinite(directions).all():
        raise ValueError("crystal directions must have shape (M, 3) and be finite")
    if not np.allclose(np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=5e-13):
        raise ValueError("crystal directions must be unit vectors within 5e-13")
    tolerance = 32 * np.finfo(np.float64).eps
    hemisphere_index = np.where(directions[:, 2] >= -tolerance, 0, 1)
    pole = np.where(hemisphere_index == 0, -1.0, 1.0)
    denominator = 1.0 - pole * directions[:, 2]
    if np.any(denominator <= 0.0):
        raise ValueError("stereographic projection denominator must be positive")
    x = directions[:, 0] / denominator
    y = directions[:, 1] / denominator
    if np.any(np.abs(x) > 1.0 + 5e-12) or np.any(np.abs(y) > 1.0 + 5e-12):
        raise ValueError("stereographic source coordinates fall outside the source square")
    size = master.shape[-1]
    column = np.clip((x + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    row = np.clip((y + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    c0 = np.floor(column).astype(np.int64)
    r0 = np.floor(row).astype(np.int64)
    c1 = np.minimum(c0 + 1, size - 1)
    r1 = np.minimum(r0 + 1, size - 1)
    dc = column - c0
    dr = row - r0
    values = (
        (1.0 - dr) * (1.0 - dc) * master[hemisphere_index, r0, c0]
        + (1.0 - dr) * dc * master[hemisphere_index, r0, c1]
        + dr * (1.0 - dc) * master[hemisphere_index, r1, c0]
        + dr * dc * master[hemisphere_index, r1, c1]
    )
    if not np.isfinite(values).all():
        raise ValueError("bilinear stereographic samples must be finite")
    return values, hemisphere_index.astype(np.int8)
```

Before clipping, reject any projected coordinate outside `[-1-5e-12, 1+5e-12]`; clipping is permitted only for roundoff at the square boundary. The equator owner is upper for arbitrary orientations.

- [ ] **Step 5: Implement tiled hemisphere pullback and identity fast path**

```python
@dataclass(frozen=True)
class ReprojectedHemisphere:
    values: np.ndarray
    valid: np.ndarray
    source_hemisphere: np.ndarray
    ledger: Mapping[str, object]


def reproject_hemisphere(
    source: np.ndarray,
    orientation: Orientation,
    *,
    hemisphere: str,
    size: int,
    tile_rows: int,
    check_deadline: Callable[[], None] | None = None,
) -> ReprojectedHemisphere:
    values = np.zeros((size, size), dtype=np.float32)
    valid = np.zeros((size, size), dtype=bool)
    source_hemisphere = np.zeros((size, size), dtype=np.int8)
    identity_fast_path = (
        orientation.euler_bunge_deg == (0.0, 0.0, 0.0)
        and source.shape[-1] == size
    )
    if identity_fast_path:
        source_index = 0 if hemisphere == "upper" else 1
        for row_start in range(0, size, tile_rows):
            row_stop = min(row_start + tile_rows, size)
            grid = stereographic_grid_rows(size, hemisphere, row_start, row_stop)
            valid[row_start:row_stop] = grid.valid
            values[row_start:row_stop][grid.valid] = source[source_index, row_start:row_stop][grid.valid]
            source_hemisphere[row_start:row_stop][grid.valid] = 1 if source_index == 0 else -1
    else:
        for row_start in range(0, size, tile_rows):
            if check_deadline is not None:
                check_deadline()
            row_stop = min(row_start + tile_rows, size)
            grid = stereographic_grid_rows(size, hemisphere, row_start, row_stop)
            tile_valid = grid.valid
            valid[row_start:row_stop] = tile_valid
            specimen = grid.directions[tile_valid]
            pulled = inverse_rotate_directions(specimen, orientation)
            sampled, owner = sample_stereographic_channel(source, pulled)
            values[row_start:row_stop][tile_valid] = sampled.astype(np.float32)
            source_hemisphere[row_start:row_stop][tile_valid] = np.where(owner == 0, 1, -1)
    ledger = {
        "projection": "stereographic",
        "display_frame": "EDAX-TSL:RD-TD-ND",
        "hemisphere": hemisphere,
        "interpolation": "bilinear",
        "spatial_filter": "none",
        "equator_owner": "upper",
        "identity_source_grid_fast_path": identity_fast_path,
        "tile_rows": tile_rows,
    }
    return ReprojectedHemisphere(values, valid, source_hemisphere, ledger)
```

- [ ] **Step 6: Add arbitrary-rotation ownership and analytic-function tests**

Use a smooth linear channel defined from known `x,y,z` values. Verify bilinear samples against the analytic values at exact nodes, ensure every valid output pixel receives one owner in `{-1,+1}`, require both owners to appear at `(17,31,43)`, and assert the invalid square corners remain masked rather than filled.

```python
def test_arbitrary_rotation_assigns_every_valid_pixel_once() -> None:
    master = indexed_master(17)
    result = reproject_hemisphere(
        master,
        Orientation((17.0, 31.0, 43.0)),
        hemisphere="upper",
        size=33,
        tile_rows=5,
    )
    assert set(np.unique(result.source_hemisphere[result.valid])) == {-1, 1}
    assert np.isfinite(result.values[result.valid]).all()
    assert np.count_nonzero(result.source_hemisphere[~result.valid]) == 0
    assert not bool(result.valid[0, 0])


def test_sampler_rejects_nonunit_or_out_of_domain_directions() -> None:
    with pytest.raises(ValueError, match="unit"):
        sample_stereographic_channel(indexed_master(9), np.array([[2.0, 0.0, 0.0]]))
```

- [ ] **Step 7: Verify GREEN and commit**

Run: `uv run pytest tests/scientific/test_oriented_spherical_reprojection.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/reprojection.py tests/scientific/test_oriented_spherical_reprojection.py
git commit -m "feat: reproject oriented spherical masters"
```

---

### Task 4: Field-Led Presentation Channel on Arbitrary Directions

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/presentation.py`
- Test: `tests/scientific/test_oriented_spherical_presentation.py`

**Interfaces:**
- Consumes: both-hemisphere raw master, kinematical tone settings, selected reflectors, and the existing field-led `NearDepthTreatmentRecipe`.
- Produces: `PresentationSource`, `build_presentation_source()`, and `evaluate_presentation()`.

- [ ] **Step 1: Write failing parity and no-linework tests**

```python
import numpy as np
import pytest

from kikuchi_lab.kinematical.render import asinh_tone_map
from kikuchi_lab.near_depth.overlap import apply_optical_depth, compute_overlap_field
from kikuchi_lab.spherical_intensity.presentation import (
    build_presentation_source,
    evaluate_presentation,
)


@lru_cache(maxsize=1)
def _ice_inputs():
    base_path = Path("recipes/kinematical/ice-ih-oxygen-quiet-proof.yml")
    base = replace(load_kinematical_recipe(base_path), half_size=32, figure_size_px=480)
    source_path = (base_path.parent / base.source_record).resolve()
    structure = load_structure_record(source_path)
    simulation, context = simulate_kinematical_arrays(structure, base)
    treatment = load_near_depth_recipe(
        "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
    )
    return simulation, context, base, treatment


def test_identity_upper_matches_existing_field_led_recipe() -> None:
    simulation, context, ice_base_recipe, ice_treatment = _ice_inputs()
    source = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        ice_base_recipe,
        ice_treatment,
    )
    size = simulation.master_stereographic.intensity.shape[-1]
    overlap = compute_overlap_field(
        context.master_simulator.reflectors,
        size=size,
        relative_factor=ice_treatment.overlap_relative_factor,
        weight_exponent=ice_treatment.weight_exponent,
        normalization_percentile=ice_treatment.normalization_percentile,
    )
    base = asinh_tone_map(
        simulation.master_stereographic.intensity[0],
        percentiles=ice_base_recipe.tone_percentiles,
        scale=ice_base_recipe.tone_asinh_scale,
    )
    expected = apply_optical_depth(
        base, overlap.normalized,
        gain=ice_treatment.optical_depth_gain,
        luminance_ceiling=ice_treatment.luminance_ceiling,
    )
    actual = evaluate_presentation(source, source.upper_directions)
    np.testing.assert_allclose(actual, expected[source.upper_valid], rtol=0.0, atol=2e-7)


def test_presentation_rejects_enabled_vector_layers() -> None:
    simulation, context, ice_base_recipe, ice_treatment = _ice_inputs()
    ice_treatment_with_center = replace(
        ice_treatment,
        center=replace(ice_treatment.center, enabled=True),
    )
    with pytest.raises(ValueError, match="vector overlays must be disabled"):
        build_presentation_source(
            simulation.master_stereographic.intensity,
            context.master_simulator.reflectors,
            ice_base_recipe,
            ice_treatment_with_center,
        )
```

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/scientific/test_oriented_spherical_presentation.py -q`

Expected: collection fails because `spherical_intensity.presentation` does not exist.

- [ ] **Step 3: Implement a source object using existing exact axial overlap**

```python
@dataclass(frozen=True)
class PresentationSource:
    toned_master: np.ndarray
    axial_bands: AxialBandSet
    band_weights: np.ndarray
    overlap_normalization: float
    upper_directions: np.ndarray
    upper_valid: np.ndarray
    gain: float
    ceiling: float
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        for name, dtype in (
            ("toned_master", np.dtype("<f4")),
            ("band_weights", np.dtype("<f8")),
            ("upper_directions", np.dtype("<f8")),
            ("upper_valid", np.dtype("bool")),
        ):
            array = np.ascontiguousarray(np.asarray(getattr(self, name), dtype=dtype))
            owned = np.frombuffer(array.tobytes(order="C"), dtype=dtype).reshape(array.shape)
            object.__setattr__(self, name, owned)
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def build_presentation_source(
    master: np.ndarray,
    reflectors: object,
    base_recipe: KinematicalRecipe,
    treatment: NearDepthTreatmentRecipe,
) -> PresentationSource:
    if treatment.center.enabled or treatment.boundary.enabled:
        raise ValueError("oriented presentation vector overlays must be disabled")
    raw = np.asarray(master, dtype=np.float32)
    toned = np.stack(
        [
            asinh_tone_map(
                raw[index],
                percentiles=base_recipe.tone_percentiles,
                scale=base_recipe.tone_asinh_scale,
            )
            for index in (0, 1)
        ]
    )
    strengths = np.abs(np.asarray(reflectors.structure_factor))
    selected = reflectors[
        strengths >= treatment.overlap_relative_factor * float(strengths.max())
    ]
    axial = collapse_antipodal_reflectors(selected)
    weights = (
        axial.structure_factor_abs / float(strengths.max())
    ) ** treatment.weight_exponent
    overlap = compute_overlap_field(
        reflectors,
        size=raw.shape[-1],
        relative_factor=treatment.overlap_relative_factor,
        weight_exponent=treatment.weight_exponent,
        normalization_percentile=treatment.normalization_percentile,
    )
    grid = stereographic_grid(raw.shape[-1], "upper")
    ledger = {
        "scientific_claim": "presentation_only",
        "base_tone": "pointwise_asinh",
        "spatial_filter": "none",
        "interpolation": "bilinear",
        "relative_factor": treatment.overlap_relative_factor,
        "weight_exponent": treatment.weight_exponent,
        "normalization_percentile": treatment.normalization_percentile,
        "normalization_value": overlap.normalization_value,
        "optical_gain": treatment.optical_depth_gain,
        "luminance_ceiling": treatment.luminance_ceiling,
        "center_overlay": False,
        "boundary_overlay": False,
    }
    return PresentationSource(
        toned_master=toned,
        axial_bands=axial,
        band_weights=weights,
        overlap_normalization=overlap.normalization_value,
        upper_directions=grid.directions[grid.valid],
        upper_valid=grid.valid,
        gain=treatment.optical_depth_gain,
        ceiling=treatment.luminance_ceiling,
        ledger=ledger,
    )
```

- [ ] **Step 4: Evaluate base tone and overlap at arbitrary crystal directions**

```python
def evaluate_presentation(
    source: PresentationSource,
    crystal_directions: np.ndarray,
) -> np.ndarray:
    directions = np.asarray(crystal_directions, dtype=np.float64)
    base, _ = sample_stereographic_channel(source.toned_master, directions)
    raw_overlap = accumulate_additional_overlap(
        directions=directions,
        normals=source.axial_bands.normals,
        half_width_sines=np.sin(source.axial_bands.theta_radian),
        weights=source.band_weights,
    )
    normalized = np.clip(
        raw_overlap / source.overlap_normalization,
        0.0,
        1.0,
    )
    return apply_optical_depth(
        base,
        normalized,
        gain=source.gain,
        luminance_ceiling=source.ceiling,
    )
```

- [ ] **Step 5: Add direction-order, antipodal, and immutability tests**

Verify output order follows input order, repeated directions repeat values exactly, all luminance values lie in `[0, 0.985]`, overlap evaluation allocates only per-direction running arrays, and the ledger contains no blur/glow/line path fields.

```python
def test_presentation_is_ordered_bounded_and_immutable() -> None:
    simulation, context, base, treatment = _ice_inputs()
    source = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base,
        treatment,
    )
    directions = source.upper_directions[[5, 5, 2, 9]]
    values = evaluate_presentation(source, directions)
    assert values[0] == values[1]
    assert np.all((0.0 <= values) & (values <= 0.985))
    with pytest.raises(ValueError):
        source.band_weights[0] = 0.0
    assert "blur" not in source.ledger
    assert "glow" not in source.ledger
    assert source.ledger["center_overlay"] is False
    assert source.ledger["boundary_overlay"] is False
```

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run pytest tests/scientific/test_oriented_spherical_presentation.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/presentation.py tests/scientific/test_oriented_spherical_presentation.py
git commit -m "feat: evaluate field-led luminance on the sphere"
```

---

### Task 5: Deterministic Hemisphere, Sphere, and Axis Figures

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/oriented_render.py`
- Test: `tests/unit/test_oriented_spherical_render.py`

**Interfaces:**
- Consumes: `PresentationSource`, identity/oriented `Orientation`, `OrientedProfile`, and a deadline callback.
- Produces: `OrientedSphericalRender(figures, ledger)` through `render_oriented_spherical()`.

- [ ] **Step 1: Write failing inventory and pixel-size tests**

```python
from io import BytesIO

from PIL import Image

from kikuchi_lab.spherical_intensity.oriented_render import (
    render_oriented_spherical,
)


EXPECTED = {
    "identity-vs-oriented-upper.png",
    "oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "orientation-axes.png",
}


def test_render_has_canonical_inventory_and_final_dimensions(
    synthetic_presentation_source, smoke_oriented_recipe
) -> None:
    render = render_oriented_spherical(
        synthetic_presentation_source,
        smoke_oriented_recipe,
    )
    assert set(render.figures) == EXPECTED
    for name, payload in render.figures.items():
        with Image.open(BytesIO(payload)) as image:
            expected = (960, 480) if name == "identity-vs-oriented-upper.png" else (480, 480)
            assert image.size == expected
    assert render.ledger["spatial_filter"] == "none"
    assert render.ledger["center_overlay"] is False
    assert render.ledger["boundary_overlay"] is False
```

Define those fixtures in the same test file so the test is self-contained:

```python
@pytest.fixture
def smoke_oriented_recipe():
    return load_oriented_spherical_recipe(
        "recipes/spherical/ice-ih-oriented-s2-proof.yml",
        profile="smoke",
    )


@pytest.fixture
def synthetic_presentation_source():
    size = 17
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    x, y = np.meshgrid(coordinate, coordinate)
    upper = np.clip(0.25 + 0.25 * x + 0.15 * y, 0.0, 1.0)
    lower = np.flip(upper, axis=(0, 1)).copy()
    grid = stereographic_grid(size, "upper")
    axial = AxialBandSet(
        hkl=np.array([[1, 0, 0]], dtype=np.int32),
        normals=np.array([[1.0, 0.0, 0.0]]),
        theta_radian=np.array([0.1]),
        structure_factor_abs=np.array([1.0]),
    )
    return PresentationSource(
        toned_master=np.stack([upper, lower]),
        axial_bands=axial,
        band_weights=np.array([1.0]),
        overlap_normalization=1.0,
        upper_directions=grid.directions[grid.valid],
        upper_valid=grid.valid,
        gain=0.38,
        ceiling=0.985,
        ledger={
            "scientific_claim": "presentation_only",
            "spatial_filter": "none",
            "center_overlay": False,
            "boundary_overlay": False,
        },
    )
```

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/unit/test_oriented_spherical_render.py -q`

Expected: collection fails because `spherical_intensity.oriented_render` does not exist.

- [ ] **Step 3: Implement canonical render payload and PNG helpers**

```python
_FIGURES = {
    "identity-vs-oriented-upper.png",
    "oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "orientation-axes.png",
}
_PNG_METADATA = {
    "Software": "kikuchi-lab deterministic oriented-spherical renderer",
    "Creation Time": "1970-01-01T00:00:00Z",
}


@dataclass(frozen=True)
class OrientedSphericalRender:
    figures: Mapping[str, bytes]
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        if set(self.figures) != _FIGURES:
            raise ValueError("oriented render figure inventory is not canonical")
        object.__setattr__(self, "figures", MappingProxyType(dict(self.figures)))
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def _hemisphere_png(values: np.ndarray, valid: np.ndarray, *, size_px: int, background: str) -> bytes:
    figure, axis = plt.subplots(figsize=(size_px / 100, size_px / 100), dpi=100)
    figure.patch.set_facecolor(background)
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_facecolor(background)
    axis.imshow(
        np.ma.array(values, mask=~valid),
        origin="lower",
        extent=(-1.0, 1.0, -1.0, 1.0),
        interpolation="nearest",
        cmap=colormaps["gray"].with_extremes(bad=background),
        vmin=0.0,
        vmax=1.0,
    )
    axis.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor="#d7e0e5", linewidth=0.8))
    axis.set_xlim(-1.025, 1.025)
    axis.set_ylim(-1.025, 1.025)
    axis.set_aspect("equal")
    axis.set_axis_off()
    output = BytesIO()
    figure.savefig(output, format="png", dpi=100, facecolor=background, metadata=_PNG_METADATA)
    plt.close(figure)
    return output.getvalue()


def _save_figure_png(figure: Figure, *, size_px: int, background: str) -> bytes:
    figure.set_size_inches(size_px / 100, size_px / 100, forward=True)
    figure.patch.set_facecolor(background)
    output = BytesIO()
    figure.savefig(
        output,
        format="png",
        dpi=100,
        facecolor=background,
        metadata=_PNG_METADATA,
    )
    plt.close(figure)
    return output.getvalue()
```

- [ ] **Step 4: Render identity and oriented specimen hemispheres**

For each profile, build fixed specimen grids at `profile.figure_size_px`, inverse-rotate valid directions, and call `evaluate_presentation()`. For identity use the same path but retain the source-grid exact fast path when the requested size equals the master size. Write `oriented-upper.png` and `oriented-lower.png`; concatenate decoded identity and oriented upper PNGs without resizing to make `identity-vs-oriented-upper.png`.

The art-field evaluator is explicitly tiled and never retains a `(2400,2400,3)` direction cube:

```python
def _presentation_hemisphere(
    source: PresentationSource,
    orientation: Orientation,
    *,
    hemisphere: str,
    size: int,
    tile_rows: int,
    check_deadline: Callable[[], None],
) -> tuple[np.ndarray, np.ndarray]:
    values = np.zeros((size, size), dtype=np.float32)
    valid = np.zeros((size, size), dtype=bool)
    for row_start in range(0, size, tile_rows):
        check_deadline()
        row_stop = min(row_start + tile_rows, size)
        grid = stereographic_grid_rows(size, hemisphere, row_start, row_stop)
        valid[row_start:row_stop] = grid.valid
        crystal = inverse_rotate_directions(grid.directions[grid.valid], orientation)
        values[row_start:row_stop][grid.valid] = evaluate_presentation(source, crystal)
    return values, valid
```

```python
def _join_horizontal(left: bytes, right: bytes, background: str) -> bytes:
    with Image.open(BytesIO(left)) as left_source:
        left_image = left_source.convert("RGBA")
    with Image.open(BytesIO(right)) as right_source:
        right_image = right_source.convert("RGBA")
    if left_image.size != right_image.size:
        raise ValueError("comparison images must have identical sizes")
    canvas = Image.new("RGBA", (2 * left_image.width, left_image.height), background)
    canvas.paste(left_image, (0, 0))
    canvas.paste(right_image, (left_image.width, 0))
    output = BytesIO()
    canvas.save(output, format="PNG", compress_level=9)
    return output.getvalue()
```

- [ ] **Step 5: Render two fixed specimen-frame sphere views**

Create a deterministic longitude/latitude mesh from the profile counts, inverse-map the specimen directions once, evaluate the same presentation channel, and render it with this exact surface call:

```python
def _sphere_png(
    source: PresentationSource,
    orientation: Orientation,
    profile: OrientedProfile,
    *,
    elev: float,
    azim: float,
    background: str,
) -> bytes:
    longitude = np.linspace(-np.pi, np.pi, profile.sphere_longitude_count)
    latitude = np.linspace(-np.pi / 2.0, np.pi / 2.0, profile.sphere_latitude_count)
    lon, lat = np.meshgrid(longitude, latitude)
    specimen_x = np.cos(lat) * np.cos(lon)
    specimen_y = np.cos(lat) * np.sin(lon)
    specimen_z = np.sin(lat)
    specimen = np.stack([specimen_x, specimen_y, specimen_z], axis=-1)
    crystal = inverse_rotate_directions(specimen.reshape(-1, 3), orientation)
    luminance = evaluate_presentation(source, crystal).reshape(specimen_x.shape)
    gray_facecolors = colormaps["gray"](luminance)
    figure = plt.figure(figsize=(profile.figure_size_px / 100, profile.figure_size_px / 100), dpi=100)
    figure.patch.set_facecolor(background)
    axis = figure.add_subplot(111, projection="3d")
    axis.plot_surface(
        specimen_x,
        specimen_y,
        specimen_z,
        facecolors=gray_facecolors,
        shade=False,
        antialiased=False,
        linewidth=0.0,
    )
    axis.view_init(elev=elev, azim=azim)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_axis_off()
    axis.set_facecolor(background)
    return _save_figure_png(figure, size_px=profile.figure_size_px, background=background)
```

Fixed camera views are `(elev=20, azim=-65)` and `(elev=-20, azim=115)`. The camera values appear in the render ledger and never enter the orientation transform.

- [ ] **Step 6: Render the axis diagnostic from the same transform**

Plot specimen `RD`, `TD`, `ND` and `G_cs[100]`, `G_cs[010]`, `G_cs[001]` as labeled 3D arrows on a unit sphere. Assert the transformed crystal-axis endpoints equal `transform_crystal_direction_to_sample` outputs within `5e-13`. This is the only figure permitted to contain explanatory labels.

```python
def _axis_png(
    orientation: Orientation,
    *,
    size_px: int,
    background: str,
) -> bytes:
    specimen_axes = {
        "RD": np.array([1.0, 0.0, 0.0]),
        "TD": np.array([0.0, 1.0, 0.0]),
        "ND": np.array([0.0, 0.0, 1.0]),
    }
    crystal_axes = {
        "[100]": transform_crystal_direction_to_sample([1.0, 0.0, 0.0], orientation),
        "[010]": transform_crystal_direction_to_sample([0.0, 1.0, 0.0], orientation),
        "[001]": transform_crystal_direction_to_sample([0.0, 0.0, 1.0], orientation),
    }
    if not np.allclose(
        np.column_stack(list(crystal_axes.values())),
        orientation_matrix(orientation),
        rtol=0.0,
        atol=5e-13,
    ):
        raise ValueError("axis diagnostic disagrees with orientation matrix")
    figure = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    figure.patch.set_facecolor(background)
    axis = figure.add_subplot(111, projection="3d")
    for label, endpoint in specimen_axes.items():
        axis.quiver(0, 0, 0, *endpoint, color="#e4edf2", linewidth=1.4)
        axis.text(*endpoint, label, color="#e4edf2")
    for label, endpoint in crystal_axes.items():
        axis.quiver(0, 0, 0, *endpoint, color="#8cc9ff", linewidth=1.2)
        axis.text(*endpoint, label, color="#8cc9ff")
    axis.set_xlim(-1.05, 1.05)
    axis.set_ylim(-1.05, 1.05)
    axis.set_zlim(-1.05, 1.05)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_axis_off()
    axis.set_facecolor(background)
    return _save_figure_png(figure, size_px=size_px, background=background)
```

Complete the public render function with one orientation source for every derivative:

```python
def render_oriented_spherical(
    source: PresentationSource,
    recipe: OrientedSphericalRecipe,
    *,
    check_deadline: Callable[[], None] | None = None,
) -> OrientedSphericalRender:
    check = check_deadline if check_deadline is not None else lambda: None
    identity = Orientation((0.0, 0.0, 0.0))
    identity_upper, identity_valid = _presentation_hemisphere(
        source, identity, hemisphere="upper",
        size=recipe.profile.figure_size_px,
        tile_rows=recipe.profile.tile_rows, check_deadline=check,
    )
    oriented_upper, upper_valid = _presentation_hemisphere(
        source, recipe.orientation, hemisphere="upper",
        size=recipe.profile.figure_size_px,
        tile_rows=recipe.profile.tile_rows, check_deadline=check,
    )
    oriented_lower, lower_valid = _presentation_hemisphere(
        source, recipe.orientation, hemisphere="lower",
        size=recipe.profile.figure_size_px,
        tile_rows=recipe.profile.tile_rows, check_deadline=check,
    )
    identity_png = _hemisphere_png(
        identity_upper, identity_valid,
        size_px=recipe.profile.figure_size_px, background=recipe.background_color,
    )
    upper_png = _hemisphere_png(
        oriented_upper, upper_valid,
        size_px=recipe.profile.figure_size_px, background=recipe.background_color,
    )
    lower_png = _hemisphere_png(
        oriented_lower, lower_valid,
        size_px=recipe.profile.figure_size_px, background=recipe.background_color,
    )
    figures = {
        "identity-vs-oriented-upper.png": _join_horizontal(
            identity_png, upper_png, recipe.background_color
        ),
        "oriented-upper.png": upper_png,
        "oriented-lower.png": lower_png,
        "oriented-sphere-front.png": _sphere_png(
            source, recipe.orientation, recipe.profile,
            elev=20.0, azim=-65.0, background=recipe.background_color,
        ),
        "oriented-sphere-rear.png": _sphere_png(
            source, recipe.orientation, recipe.profile,
            elev=-20.0, azim=115.0, background=recipe.background_color,
        ),
        "orientation-axes.png": _axis_png(
            recipe.orientation,
            size_px=recipe.profile.figure_size_px,
            background=recipe.background_color,
        ),
    }
    ledger = {
        "schema_version": 1,
        "orientation_id": recipe.orientation.orientation_id,
        "figure_size_px": recipe.profile.figure_size_px,
        "sphere_cameras": [
            {"elevation_deg": 20.0, "azimuth_deg": -65.0},
            {"elevation_deg": -20.0, "azimuth_deg": 115.0},
        ],
        "raster_interpolation": "nearest",
        "field_interpolation": "bilinear",
        "spatial_filter": "none",
        "center_overlay": False,
        "boundary_overlay": False,
        "annotated_figures": ["orientation-axes.png"],
    }
    return OrientedSphericalRender(figures=figures, ledger=ledger)
```

- [ ] **Step 7: Add deterministic-byte and no-linework tests**

Run the synthetic render twice and require identical SHA-256 values for all six PNGs. Assert the art-figure ledger contains `center_overlay=false`, `boundary_overlay=false`, `spatial_filter=none`, and `raster_interpolation=nearest`; assert only `orientation-axes.png` is marked diagnostic/annotated.

```python
def test_render_bytes_are_deterministic_and_art_has_no_line_layers(
    synthetic_presentation_source,
    smoke_oriented_recipe,
) -> None:
    first = render_oriented_spherical(synthetic_presentation_source, smoke_oriented_recipe)
    second = render_oriented_spherical(synthetic_presentation_source, smoke_oriented_recipe)
    assert {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in first.figures.items()
    } == {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in second.figures.items()
    }
    assert first.ledger["center_overlay"] is False
    assert first.ledger["boundary_overlay"] is False
    assert first.ledger["spatial_filter"] == "none"
    assert first.ledger["raster_interpolation"] == "nearest"
    assert first.ledger["annotated_figures"] == ["orientation-axes.png"]
```

- [ ] **Step 8: Verify GREEN and commit**

Run: `uv run pytest tests/unit/test_oriented_spherical_render.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/oriented_render.py tests/unit/test_oriented_spherical_render.py
git commit -m "feat: render oriented spherical Ice views"
```

---

### Task 6: Immutable Oriented Bundle with Deterministic NPZ

**Files:**
- Create: `src/kikuchi_lab/spherical_intensity/oriented_bundle.py`
- Test: `tests/unit/test_oriented_spherical_bundle.py`

**Interfaces:**
- Consumes: source field, oriented field, render, oriented/source/presentation recipes, structure source, and run-stage metrics.
- Produces: `OrientedSphericalBundleResult` through `write_oriented_spherical_bundle()`.

- [ ] **Step 1: Write failing inventory, hash, and collision tests**

```python
import json

import pytest

from kikuchi_lab.artifacts import BundleExistsError
from kikuchi_lab.spherical_intensity.oriented_bundle import (
    write_oriented_spherical_bundle,
)


def test_bundle_contains_exact_field_ledgers_and_six_figures(oriented_bundle_inputs, tmp_path) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert set(manifest["files"]) == {
        "data/oriented-s2-field.npz",
        "diagnostics/source-field-ledger.json",
        "diagnostics/orientation-ledger.json",
        "diagnostics/reprojection-ledger.json",
        "diagnostics/presentation-ledger.json",
        "diagnostics/figure-ledger.json",
        "diagnostics/stage-timing.json",
        "figures/identity-vs-oriented-upper.png",
        "figures/oriented-upper.png",
        "figures/oriented-lower.png",
        "figures/oriented-sphere-front.png",
        "figures/oriented-sphere-rear.png",
        "figures/orientation-axes.png",
        "recipes/oriented-spherical.json",
        "recipes/source-spherical.json",
        "recipes/presentation.json",
        "source/structure.json",
    }
    with pytest.raises(BundleExistsError):
        write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
```

Build the fixture from a small real Ice simulation, then reduce only the display canvas so bundle tests stay fast:

```python
@pytest.fixture(scope="module")
def oriented_bundle_inputs():
    oriented = load_oriented_spherical_recipe(
        "recipes/spherical/ice-ih-oriented-s2-proof.yml",
        profile="smoke",
    )
    oriented = replace(
        oriented,
        profile=replace(
            oriented.profile,
            figure_size_px=64,
            sphere_longitude_count=37,
            sphere_latitude_count=19,
            tile_rows=8,
        ),
    )
    spherical_path = Path("recipes/spherical/ice-ih-s2-intensity.yml")
    source_recipe = load_spherical_intensity_recipe(spherical_path, profile="smoke")
    base_path = (spherical_path.parent / source_recipe.source_kinematical_recipe).resolve()
    base = replace(load_kinematical_recipe(base_path), half_size=32, figure_size_px=64)
    structure = load_structure_record((base_path.parent / base.source_record).resolve())
    simulation, context = simulate_kinematical_arrays(structure, base)
    build = build_spherical_intensity(simulation, structure, source_recipe)
    identity_field = rotate_spherical_field(build.field, Orientation((0.0, 0.0, 0.0)))
    oriented_field = rotate_spherical_field(build.field, oriented.orientation)
    treatment = load_near_depth_recipe(
        "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
    )
    presentation_source = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base,
        treatment,
    )
    render = render_oriented_spherical(presentation_source, oriented)
    return {
        "source_build": build,
        "identity_field": identity_field,
        "oriented_field": oriented_field,
        "render": render,
        "oriented_recipe": oriented,
        "source_recipe": source_recipe,
        "presentation_recipe": treatment,
        "presentation_source": presentation_source,
        "source": structure,
        "stage_timing": {"elapsed_seconds": 1.0},
    }
```

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/unit/test_oriented_spherical_bundle.py -q`

Expected: collection fails because `spherical_intensity.oriented_bundle` does not exist.

- [ ] **Step 3: Implement deterministic compressed NPZ writing**

```python
def _write_oriented_npz(path: Path, field: SphericalIntensityField) -> None:
    arrays = {
        "density_weight": np.asarray(field.density_weight, dtype="<f8"),
        "hemisphere": np.asarray(field.hemisphere, dtype="i1"),
        "intensity_normalized": np.asarray(field.intensity_normalized, dtype="<f8"),
        "intensity_raw": np.asarray(field.intensity_raw, dtype="<f4"),
        "source_column": np.asarray(field.source_column, dtype="<i4"),
        "source_row": np.asarray(field.source_row, dtype="<i4"),
        "xyz_sample": np.asarray(field.xyz, dtype="<f8"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with zipfile.ZipFile(handle, mode="w") as archive:
            for name in sorted(arrays):
                payload = io.BytesIO()
                np.lib.format.write_array(payload, arrays[name], allow_pickle=False)
                info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue())
        handle.flush()
        os.fsync(handle.fileno())
```

- [ ] **Step 4: Implement run identity, canonical inventory, and atomic publication**

Run identity must contain oriented recipe ID, source spherical recipe ID, presentation recipe ID, Ice source ID/hash, source field ID, oriented field ID, orientation ID, figure hashes, and numeric channel hashes. Derive `run_id = stable_id("oriented-spherical-run", run_identity)`.

Use the existing bundle convention: create `.<run_id>.publishing`, reject an existing completed or partial path, write a unique `.<run_id>.partial-<uuid>`, fsync every file and directory, and promote without replacement using the same macOS `renameatx_np(RENAME_EXCL)` / portable hard failure semantics already exercised by `kinematical.bundle`. Never import or alter `spherical_intensity.bundle.py`.

Define the result and public writer with these exact boundaries:

```python
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _source_payload,
    _write_bytes,
    _write_json,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_without_manifest(root: Path) -> dict[str, dict[str, object]]:
    return {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }


@dataclass(frozen=True)
class OrientedSphericalBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str


def write_oriented_spherical_bundle(
    output_root: str | Path,
    *,
    source_build: SphericalIntensityBuild,
    identity_field: OrientedSphericalIntensityField,
    oriented_field: OrientedSphericalIntensityField,
    render: OrientedSphericalRender,
    oriented_recipe: OrientedSphericalRecipe,
    source_recipe: SphericalIntensityRecipe,
    presentation_recipe: NearDepthTreatmentRecipe,
    presentation_source: PresentationSource,
    source: StructureRecord,
    stage_timing: Mapping[str, object],
) -> OrientedSphericalBundleResult:
    if identity_field.source_field_id != source_build.field.field_id:
        raise ValueError("identity field does not derive from the supplied source field")
    if oriented_field.source_field_id != source_build.field.field_id:
        raise ValueError("oriented field does not derive from the supplied source field")
    recorded_after = oriented_field.ledger.get("channel_sha256_after")
    if dict(recorded_after) != dict(oriented_field.field.channel_sha256):
        raise ValueError("oriented field ledger channel hashes are inconsistent")
    run_identity = {
        "oriented_recipe_id": oriented_recipe.recipe_id,
        "source_recipe_id": source_recipe.recipe_id,
        "presentation_recipe_id": presentation_recipe.recipe_id,
        "presentation_ledger_id": stable_id(
            "presentation-ledger", presentation_source.ledger
        ),
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "source_field_id": source_build.field.field_id,
        "identity_field_id": identity_field.field.field_id,
        "oriented_field_id": oriented_field.field.field_id,
        "orientation_id": oriented_field.orientation_id,
        "oriented_channel_sha256": dict(oriented_field.field.channel_sha256),
        "figure_sha256": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in sorted(render.figures.items())
        },
    }
    run_id = stable_id("oriented-spherical-run", run_identity)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(f"same-run publication already in progress: {ownership}") from None
    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(f"partial bundle already exists: {existing_partials[0]}")
        partial = root / f".{run_id}.partial-{uuid4().hex}"
        partial.mkdir()
        _write_oriented_npz(partial / "data/oriented-s2-field.npz", oriented_field.field)
        _write_json(partial / "diagnostics/source-field-ledger.json", {
            "field_id": source_build.field.field_id,
            "channel_sha256": dict(source_build.field.channel_sha256),
            "metadata": source_build.field.metadata_dict(),
        })
        _write_json(partial / "diagnostics/orientation-ledger.json", oriented_field.ledger)
        _write_json(partial / "diagnostics/reprojection-ledger.json", {
            "interpolation": "bilinear",
            "spatial_filter": "none",
            "equator_owner": "upper",
            "output_size_px": oriented_recipe.profile.figure_size_px,
            "tile_rows": oriented_recipe.profile.tile_rows,
        })
        _write_json(
            partial / "diagnostics/presentation-ledger.json",
            presentation_source.ledger,
        )
        _write_json(partial / "diagnostics/figure-ledger.json", render.ledger)
        _write_json(partial / "diagnostics/stage-timing.json", stage_timing)
        for name, payload in render.figures.items():
            _write_bytes(partial / "figures" / name, payload)
        _write_json(partial / "recipes/oriented-spherical.json", oriented_recipe.to_dict())
        _write_json(partial / "recipes/source-spherical.json", source_recipe.to_dict())
        _write_json(partial / "recipes/presentation.json", presentation_recipe.to_dict())
        _write_json(partial / "source/structure.json", _source_payload(source))
        files = _inventory_without_manifest(partial)
        _write_json(partial / "manifest.json", {
            "schema_version": 1, "run_id": run_id,
            "run_identity": run_identity, "files": files,
        })
        manifest_sha256 = _sha256(partial / "manifest.json")
        _fsync_directory_tree(partial)
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(f"completed bundle already exists: {completed}") from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return OrientedSphericalBundleResult(run_id, completed, manifest_sha256)
    finally:
        ownership.rmdir()
        _fsync_directory(root)
```

The oriented bundle reuses the already tested kinematical atomic helpers exactly as `near_depth.bundle` does. It defines only the local SHA-256 and inventory helpers above, so the dirty spherical/MTEX bundle remains untouched.

- [ ] **Step 5: Add corruption and determinism tests**

Open the NPZ with `allow_pickle=False`; assert all seven arrays and dtypes. Rebuild into a second empty root and require the same `run_id`, manifest SHA-256, NPZ SHA-256, JSON SHA-256 values, and PNG SHA-256 values. Mutate one copied numeric channel before publication and require identity validation to fail rather than writing a partial bundle.

```python
def test_bundle_npz_and_manifest_are_deterministic(oriented_bundle_inputs, tmp_path) -> None:
    def file_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    first = write_oriented_spherical_bundle(tmp_path / "a", **oriented_bundle_inputs)
    second = write_oriented_spherical_bundle(tmp_path / "b", **oriented_bundle_inputs)
    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256
    assert file_sha256(first.path / "data/oriented-s2-field.npz") == file_sha256(
        second.path / "data/oriented-s2-field.npz"
    )
    with np.load(first.path / "data/oriented-s2-field.npz", allow_pickle=False) as archive:
        assert set(archive.files) == {
            "density_weight", "hemisphere", "intensity_normalized", "intensity_raw",
            "source_column", "source_row", "xyz_sample",
        }
        assert archive["xyz_sample"].dtype == np.dtype("<f8")
        assert archive["intensity_raw"].dtype == np.dtype("<f4")


def test_bundle_rejects_inconsistent_oriented_ledger(oriented_bundle_inputs, tmp_path) -> None:
    inputs = dict(oriented_bundle_inputs)
    field = inputs["oriented_field"]
    bad_ledger = dict(field.ledger)
    bad_ledger["channel_sha256_after"] = {"xyz": "0" * 64}
    inputs["oriented_field"] = replace(field, ledger=bad_ledger)
    with pytest.raises(ValueError, match="channel hashes are inconsistent"):
        write_oriented_spherical_bundle(tmp_path, **inputs)
```

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run pytest tests/unit/test_oriented_spherical_bundle.py -q`

Expected: all tests pass.

```bash
git add src/kikuchi_lab/spherical_intensity/oriented_bundle.py tests/unit/test_oriented_spherical_bundle.py
git commit -m "feat: publish oriented spherical bundles"
```

---

### Task 7: Bounded Ice Workflow with Smoke-Before-Review Gate

**Files:**
- Create: `src/kikuchi_lab/workflows/oriented_spherical.py`
- Test: `tests/integration/test_oriented_ice_spherical.py`

**Interfaces:**
- Consumes: oriented recipe path, output root, and requested profile `smoke|review`.
- Produces: `OrientedSphericalRunResult` through `render_oriented_spherical_master()`; `review` returns both the prerequisite smoke result and the review result.

- [ ] **Step 1: Write failing smoke and review-gate tests**

```python
from pathlib import Path

from kikuchi_lab.workflows.oriented_spherical import (
    render_oriented_spherical_master,
)


RECIPE = Path("recipes/spherical/ice-ih-oriented-s2-proof.yml")


def test_real_ice_smoke_builds_both_orientations_and_all_views(tmp_path: Path) -> None:
    result = render_oriented_spherical_master(
        recipe_path=RECIPE,
        output_root=tmp_path,
        profile="smoke",
    )
    assert result.smoke is not None
    assert result.review is None
    assert result.smoke.path.is_dir()
    assert len(result.smoke.figure_names) == 6
    assert result.smoke.source_half_size == 32


def test_review_runs_and_publishes_smoke_first(monkeypatch, tmp_path: Path) -> None:
    stages: list[str] = []
    fake_result = object()
    monkeypatch.setattr(
        "kikuchi_lab.workflows.oriented_spherical._run_profile",
        lambda **kwargs: stages.append(kwargs["profile_name"]) or fake_result,
    )
    result = render_oriented_spherical_master(
        recipe_path=RECIPE,
        output_root=tmp_path,
        profile="review",
    )
    assert stages == ["smoke", "review"]
    assert result.smoke is fake_result
    assert result.review is fake_result
```

- [ ] **Step 2: Run the smoke integration test and verify RED**

Run: `uv run pytest tests/integration/test_oriented_ice_spherical.py -q`

Expected: collection fails because `workflows.oriented_spherical` does not exist.

- [ ] **Step 3: Implement profile materialization without changing shared recipe loaders**

```python
def _materialize_source_recipes(
    oriented_path: Path,
    oriented: OrientedSphericalRecipe,
) -> tuple[SphericalIntensityRecipe, KinematicalRecipe, Path, Path]:
    spherical_path = (oriented_path.parent / oriented.source_spherical_recipe).resolve()
    source_profile_name = "smoke" if oriented.profile.name == "smoke" else "acceptance"
    source_recipe = load_spherical_intensity_recipe(
        spherical_path,
        profile=source_profile_name,
    )
    source_recipe = replace(
        source_recipe,
        profile=replace(
            source_recipe.profile,
            half_size=oriented.profile.source_half_size,
            timeout_seconds=oriented.profile.timeout_seconds,
        ),
    )
    base_path = (spherical_path.parent / source_recipe.source_kinematical_recipe).resolve()
    base = load_kinematical_recipe(base_path)
    if base.hemisphere != "both":
        raise ValueError("oriented source master must contain both hemispheres")
    base = replace(
        base,
        orientation=Orientation((0.0, 0.0, 0.0)),
        half_size=oriented.profile.source_half_size,
        figure_size_px=oriented.profile.figure_size_px,
    )
    return source_recipe, base, spherical_path, base_path
```

The spherical loader stays unchanged at its current smoke/acceptance contract; the oriented recipe's explicit profile creates a new content ID through `dataclasses.replace`.

- [ ] **Step 4: Implement deadline checks and one profile execution**

```python
class OrientedSphericalTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrientedSphericalProfileResult:
    profile: OrientedProfileName
    run_id: str
    path: Path
    source_half_size: int
    figure_names: Sequence[str]
    manifest_sha256: str
    elapsed_seconds: float


def _deadline(started: float, timeout_seconds: int, stage: str) -> Callable[[], None]:
    def check() -> None:
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise OrientedSphericalTimeoutError(
                f"oriented spherical {stage} exceeded {timeout_seconds} seconds"
            )
    return check


def _run_profile(
    *,
    recipe_path: Path,
    output_root: Path,
    profile_name: OrientedProfileName,
) -> OrientedSphericalProfileResult:
    started = time.monotonic()
    oriented_recipe = load_oriented_spherical_recipe(recipe_path, profile=profile_name)
    check = _deadline(started, oriented_recipe.profile.timeout_seconds, profile_name)
    source_recipe, base, spherical_path, base_path = _materialize_source_recipes(
        recipe_path, oriented_recipe
    )
    source_path = (base_path.parent / base.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    check()
    simulation, context = simulate_kinematical_arrays(source, base)
    check()
    build = build_spherical_intensity(simulation, source, source_recipe)
    identity = rotate_spherical_field(build.field, Orientation((0.0, 0.0, 0.0)))
    oriented = rotate_spherical_field(build.field, oriented_recipe.orientation)
    treatment_path = (recipe_path.parent / oriented_recipe.presentation_recipe).resolve()
    treatment = load_near_depth_recipe(treatment_path)
    if treatment.expected_kinematical_recipe_id != load_kinematical_recipe(base_path).recipe_id:
        raise ValueError("presentation recipe does not identify the tracked Ice base recipe")
    presentation = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base,
        treatment,
    )
    check()
    render = render_oriented_spherical(presentation, oriented_recipe, check_deadline=check)
    check()
    bundle = write_oriented_spherical_bundle(
        output_root,
        source_build=build,
        identity_field=identity,
        oriented_field=oriented,
        render=render,
        oriented_recipe=oriented_recipe,
        source_recipe=source_recipe,
        presentation_recipe=treatment,
        presentation_source=presentation,
        source=source,
        stage_timing={"elapsed_seconds": time.monotonic() - started},
    )
    return OrientedSphericalProfileResult(
        profile=profile_name,
        run_id=bundle.run_id,
        path=bundle.path,
        source_half_size=oriented_recipe.profile.source_half_size,
        figure_names=tuple(sorted(render.figures)),
        manifest_sha256=bundle.manifest_sha256,
        elapsed_seconds=time.monotonic() - started,
    )
```

Log stage names and elapsed seconds to stderr before simulation, S2 mapping, presentation, figures, and publication. The render calls `check_deadline()` between row tiles and before each figure. A timeout or smoke failure leaves no completed review bundle.

- [ ] **Step 5: Implement the public smoke-before-review result**

```python
@dataclass(frozen=True)
class OrientedSphericalRunResult:
    smoke: OrientedSphericalProfileResult
    review: OrientedSphericalProfileResult | None


def render_oriented_spherical_master(
    *,
    recipe_path: str | Path,
    output_root: str | Path,
    profile: OrientedProfileName,
) -> OrientedSphericalRunResult:
    recipe_file = Path(recipe_path).resolve()
    root = Path(output_root).resolve()
    smoke = _run_profile(
        recipe_path=recipe_file,
        output_root=root / "smoke",
        profile_name="smoke",
    )
    if profile == "smoke":
        return OrientedSphericalRunResult(smoke=smoke, review=None)
    review = _run_profile(
        recipe_path=recipe_file,
        output_root=root / "review",
        profile_name="review",
    )
    return OrientedSphericalRunResult(smoke=smoke, review=review)
```

Reject an invalid profile before starting smoke. If a content-identical smoke bundle already exists, do not overwrite it; require a new empty output root so the review command remains a single auditable transaction.

- [ ] **Step 6: Verify real smoke, inspect its six images, and commit**

Run: `uv run pytest tests/integration/test_oriented_ice_spherical.py -q`

Expected: the real `65 x 65` Ice smoke passes in under `180 s` and the review gate-order test passes.

Open all six PNGs from the test bundle at native size and verify the oriented band/intersection network moves while the circular specimen canvas stays fixed.

```bash
git add src/kikuchi_lab/workflows/oriented_spherical.py tests/integration/test_oriented_ice_spherical.py
git commit -m "feat: orchestrate bounded oriented Ice proof"
```

---

### Task 8: CLI Surface and Public Workflow Export

**Files:**
- Modify: `src/kikuchi_lab/cli/main.py:43-57,233-265`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `render_oriented_spherical_master(recipe_path, output_root, profile)`.
- Produces: CLI command `kikuchi-lab render-oriented-spherical --recipe PATH --output DIR --profile smoke|review` and JSON summary.

- [ ] **Step 1: Write the failing CLI dispatch and error tests**

```python
def test_render_oriented_spherical_dispatches_review(monkeypatch, capsys, tmp_path) -> None:
    called = {}
    smoke = SimpleNamespace(
        profile="smoke", run_id="smoke-run", path=tmp_path / "smoke",
        source_half_size=32, figure_names=("a.png",),
        manifest_sha256="a" * 64, elapsed_seconds=1.0,
    )
    review = SimpleNamespace(
        profile="review", run_id="review-run", path=tmp_path / "review",
        source_half_size=512, figure_names=("b.png",),
        manifest_sha256="b" * 64, elapsed_seconds=2.0,
    )
    fake_result = SimpleNamespace(smoke=smoke, review=review)
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_oriented_spherical_master",
        lambda **kwargs: called.update(kwargs) or fake_result,
    )
    status = main([
        "render-oriented-spherical",
        "--recipe", "recipes/spherical/ice-ih-oriented-s2-proof.yml",
        "--output", str(tmp_path),
        "--profile", "review",
    ])
    assert status == 0
    assert called["profile"] == "review"
    payload = json.loads(capsys.readouterr().out)
    assert payload["smoke"]["profile"] == "smoke"
    assert payload["review"]["profile"] == "review"


def test_render_oriented_spherical_normalizes_timeout(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_oriented_spherical_master",
        Mock(side_effect=RuntimeError("bounded failure")),
    )
    status = main([
        "render-oriented-spherical", "--recipe", "x.yml",
        "--output", "out", "--profile", "smoke",
    ])
    assert status == 1
    assert "oriented spherical render failed: bounded failure" in capsys.readouterr().err
```

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/unit/test_cli.py -q`

Expected: argparse rejects `render-oriented-spherical` as an invalid command.

- [ ] **Step 3: Add parser, dispatch, and normalized JSON output**

```python
render_oriented = subparsers.add_parser(
    "render-oriented-spherical",
    help="Rotate an exact spherical master and render fixed specimen views.",
)
render_oriented.add_argument("--recipe", required=True)
render_oriented.add_argument("--output", required=True)
render_oriented.add_argument("--profile", choices=("smoke", "review"), default="smoke")
```

```python
if args.command == "render-oriented-spherical":
    from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
    from kikuchi_lab.workflows import render_oriented_spherical_master

    try:
        result = render_oriented_spherical_master(
            recipe_path=args.recipe,
            output_root=args.output,
            profile=args.profile,
        )
    except (BundleExistsError, PartialBundleError, OSError, ValueError, RuntimeError) as error:
        print(f"oriented spherical render failed: {error}", file=sys.stderr)
        return 1
    def payload(item):
        if item is None:
            return None
        return {
            "profile": item.profile,
            "run_id": item.run_id,
            "path": str(item.path),
            "source_half_size": item.source_half_size,
            "figures": list(item.figure_names),
            "manifest_sha256": item.manifest_sha256,
            "elapsed_seconds": item.elapsed_seconds,
        }
    print(json.dumps({"smoke": payload(result.smoke), "review": payload(result.review)}, indent=2, sort_keys=True))
    return 0
```

Export `OrientedSphericalRunResult` and `render_oriented_spherical_master` from `workflows/__init__.py`; do not touch `spherical_intensity/__init__.py`.

- [ ] **Step 4: Verify GREEN and commit**

Run: `uv run pytest tests/unit/test_cli.py -q`

Expected: all CLI tests pass.

```bash
git add src/kikuchi_lab/cli/main.py src/kikuchi_lab/workflows/__init__.py tests/unit/test_cli.py
git commit -m "feat: expose oriented spherical render CLI"
```

---

### Task 9: Review Render, Acceptance Evidence, and Full Verification

**Files:**
- Create: `docs/acceptance/ice-ih-oriented-spherical-master.md`
- Modify: `docs/work/KIKU-T027.md`

**Interfaces:**
- Consumes: completed smoke/review manifests, six review figures, exact oriented NPZ, and test output.
- Produces: one auditable review candidate and tracker evidence; the task remains `active` until the user reviews the figures.

- [ ] **Step 1: Run the focused scientific and unit suite before expensive review**

Run:

```bash
uv run pytest \
  tests/unit/test_oriented_spherical_recipe.py \
  tests/scientific/test_oriented_spherical_rotation.py \
  tests/scientific/test_oriented_spherical_reprojection.py \
  tests/scientific/test_oriented_spherical_presentation.py \
  tests/unit/test_oriented_spherical_render.py \
  tests/unit/test_oriented_spherical_bundle.py \
  tests/unit/test_cli.py -q
```

Expected: all focused tests pass with no warnings attributable to the new slice.

- [ ] **Step 2: Produce the bounded smoke-plus-review candidate once**

Run:

```bash
uv run kikuchi-lab render-oriented-spherical \
  --recipe recipes/spherical/ice-ih-oriented-s2-proof.yml \
  --output local/runs/ice-ih-oriented-s2 \
  --profile review
```

Expected: stderr reports smoke stages before review stages; stdout contains both immutable bundle paths; smoke finishes within `180 s`; complete review finishes within `600 s`.

- [ ] **Step 3: Inspect and record the review artifacts**

Open at native scale:

```text
figures/identity-vs-oriented-upper.png
figures/oriented-upper.png
figures/oriented-lower.png
figures/oriented-sphere-front.png
figures/oriented-sphere-rear.png
figures/orientation-axes.png
```

Verify visually that the circular specimen canvas is fixed, the full band/intersection network moves coherently, no center/boundary line layer appears, the sphere views match the hemisphere orientation, and the field remains crisp rather than blurred.

Record exact run IDs, manifest SHA-256 values, figure SHA-256 values, elapsed seconds, orientation ID, source field ID, oriented field ID, and review paths in `docs/acceptance/ice-ih-oriented-spherical-master.md`. Include the acceptance statement `presentation_status: awaiting_user_review`; do not claim dynamical or experimental fidelity.

- [ ] **Step 4: Run project verification and tracker validation**

Run:

```bash
uv run pytest -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
```

Expected: the full suite passes, Ruff reports no violations, and all work items validate.

- [ ] **Step 5: Update KIKU-T027 evidence without prematurely completing it**

Set `status: active`, check every machine-verifiable acceptance item, leave the user-review checkbox open, and add links to:

```yaml
evidence:
  - ../acceptance/ice-ih-oriented-spherical-master.md
  - ../superpowers/specs/2026-07-15-oriented-spherical-master-design.md
  - ../superpowers/plans/2026-07-16-oriented-spherical-master.md
```

- [ ] **Step 6: Commit the review candidate evidence**

```bash
git add docs/acceptance/ice-ih-oriented-spherical-master.md docs/work/KIKU-T027.md
git commit -m "docs: record oriented Ice review candidate"
```

- [ ] **Step 7: Request user review with the images embedded**

Show the identity comparison, upper and lower hemispheres, both sphere views, and axis diagnostic directly from the review bundle. Ask the user whether the oriented field-led treatment is accepted as the first orientation proof. Only a later explicit approval may check the final tracker item and mark `KIKU-T027` complete.
