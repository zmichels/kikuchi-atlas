# Crystal Habit Mesh Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-native pipeline that turns an arbitrary conforming CIF plus an explicit crystal-habit recipe into a reproducible, provenance-rich, watertight STL, with quartz validated against MTEX 6.1.1.

**Architecture:** A strict YAML recipe loader owns source identity and explicit Miller-family support distances. A boundary adapter uses orix/diffpy only to parse the CIF, construct an `X||a*, Z||c` crystal frame, and expand reciprocal-plane normals; project-owned arrays then flow through a SciPy half-space solver, deterministic polygon triangulation, Trimesh validation with `process=False`, and an atomic artifact writer. MTEX remains an optional plain-JSON reference oracle and is never imported by the production package.

**Tech Stack:** Python 3.12, NumPy 2.x, SciPy 1.x (`HalfspaceIntersection`, `ConvexHull`), orix 0.14.x, diffpy-structure 3.x, PyYAML 6.x, Trimesh 4.12.x, Matplotlib 3.11.x with the noninteractive Agg backend, pytest 8.x, MATLAB R2025b, MTEX 6.1.1.

## Global Constraints

- The canonical product is one convex idealized crystal habit, not an atomic model, growth simulation, twin, aggregate, cavity, base, label, support, or Kikuchi relief.
- The CIF supplies lattice and symmetry; the recipe explicitly supplies every Miller family and positive relative support distance.
- Four-index `hkil` input must satisfy `h + k + i = 0` exactly before reducing to three reciprocal coordinates.
- The recorded Cartesian crystal frame is right-handed `X||a*`, `Z||c`, `Y = Z x X`.
- The solver must retain labeled polygon faces as the scientific geometry contract; triangles are a derived export contract.
- Final scale is the greatest axis-aligned mesh extent and must equal `60.0 mm` within `1e-8 mm` for the quartz acceptance recipe.
- Trimesh must always be constructed with `process=False`; no validator may merge, fill, repair, reorient, simplify, or otherwise mutate geometry.
- Canonical acceptance requires one connected, convex, watertight, consistently outward-oriented, positive-volume mesh with no duplicate or degenerate triangles.
- FDM checks are advisory and may not change geometry.
- Quartz/MTEX parity tolerances are: identical visible labeled family set and vertex/polygon counts, vertex Hausdorff distance `<= 1e-7` after unit-extent normalization, relative volume difference `<= 1e-6`, and corresponding face-normal angle `<= 1e-7 rad`.
- STL numeric coordinates are millimetres; the manifest remains authoritative because STL does not carry standardized units.
- Generated meshes and previews remain local run artifacts; recipes, compact fixtures, tests, the MTEX ledger, and acceptance evidence belong in git.
- Existing exceptional-forsterite products, recipes, and acceptance criteria must remain unchanged.

---

## File Map

| File | Responsibility |
| --- | --- |
| `src/kikuchi_lab/habit/recipes.py` | Immutable habit recipe types, YAML validation, CIF checksum verification, and content identity. |
| `src/kikuchi_lab/habit/crystallography.py` | CIF/orix boundary, reciprocal normals, explicit crystal frame, and symmetry expansion into plain project data. |
| `src/kikuchi_lab/habit/geometry.py` | Labeled half-spaces, convex intersection, ordered polygon faces, inactive-plane diagnostics, scaling, and deterministic triangulation. |
| `src/kikuchi_lab/habit/mesh.py` | Non-mutating Trimesh validation, FDM observations, STL bytes, and fixed-view PNG preview. |
| `src/kikuchi_lab/habit/workflow.py` | Atomic content-addressed habit bundle, file inventory, hashes, and public build result. |
| `src/kikuchi_lab/habit/parity.py` | Plain MTEX-ledger loading and geometry-level parity metrics. |
| `scripts/export_mtex_habit_reference.m` | Optional MTEX 6.1.1 exporter from a plain JSON reference request. |
| `phases/quartz/COD-9000775.cif` | Public-domain quartz acceptance source used by MTEX's bundled `quartz.cif`. |
| `recipes/habits/quartz-mtex-example.yml` | Canonical 60 mm quartz habit acceptance recipe. |
| `reference/habits/quartz-mtex-request.json` | Exact MTEX Miller families and normal multipliers from the approved example. |
| `reference/habits/quartz-mtex-6.1.1.json` | Compact generated MTEX vertices, polygon faces, normals, labels, and environment ledger. |

---

### Task 1: Define the habit recipe and quartz reference source (`KIKU-T025`)

**Files:**
- Create: `src/kikuchi_lab/habit/__init__.py`
- Create: `src/kikuchi_lab/habit/recipes.py`
- Create: `phases/quartz/COD-9000775.cif`
- Create: `recipes/habits/quartz-mtex-example.yml`
- Create: `tests/unit/habit/test_habit_recipes.py`

**Interfaces:**
- Consumes: `kikuchi_lab.model.identity.canonical_json` and `stable_id`.
- Produces: `HabitFace`, `PhaseSource`, `FDMContext`, `HabitRecipe`, and `load_habit_recipe(path: str | Path) -> HabitRecipe`.
- `HabitRecipe.identity_dict()` excludes machine-local paths and includes CIF SHA-256, semantic recipe content, and optional FDM context.

- [ ] **Step 1: Write failing recipe-contract tests**

```python
# tests/unit/habit/test_habit_recipes.py
from pathlib import Path

import pytest

from kikuchi_lab.habit.recipes import load_habit_recipe

ROOT = Path(__file__).parents[3]
RECIPE = ROOT / "recipes/habits/quartz-mtex-example.yml"


def test_quartz_recipe_preserves_explicit_support_distances_and_source_identity():
    recipe = load_habit_recipe(RECIPE)

    assert recipe.schema == "kikuchi.habit-recipe/v1"
    assert recipe.phase.name == "quartz"
    assert recipe.phase.space_group_number == 154
    assert recipe.index_convention == "hkil"
    assert recipe.maximum_dimension_mm == 60.0
    assert {face.label: face.relative_distance for face in recipe.faces} == {
        "m": pytest.approx(0.5091702048436217),
        "r": pytest.approx(1.0),
        "z": pytest.approx(1.1111111111111112),
        "s1": pytest.approx(0.9557191976124586),
        "x1": pytest.approx(0.7545681549701853),
    }
    assert recipe.phase.cif_sha256 == (
        "10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57"
    )
    assert recipe.recipe_id == load_habit_recipe(RECIPE).recipe_id
    assert str(ROOT) not in str(recipe.identity_dict())


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("relative_distance: 1.0", "relative_distance"),
        ("family: [1, 0, 0, 0]", "h + k + i"),
        ("maximum_dimension_mm: 0", "maximum_dimension_mm"),
    ],
)
def test_recipe_rejects_nonpositive_distance_invalid_hkil_and_scale(
    tmp_path: Path, replacement: str, message: str
):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = RECIPE.read_text(encoding="utf-8").replace(
        "../../phases/quartz/COD-9000775.cif", str(cif)
    )
    if "relative_distance" in replacement:
        text = text.replace("relative_distance: 0.5091702048436217", "relative_distance: 0")
    elif "family" in replacement:
        text = text.replace("family: [1, 0, -1, 0]", replacement)
    else:
        text = text.replace("maximum_dimension_mm: 60.0", replacement)
    candidate = tmp_path / "habit.yml"
    candidate.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_habit_recipe(candidate)
```

- [ ] **Step 2: Run the focused test and confirm the missing package failure**

Run: `uv run pytest tests/unit/habit/test_habit_recipes.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'kikuchi_lab.habit'`.

- [ ] **Step 3: Add the tracked quartz CIF and exact recipe**

Add the byte-for-byte public-domain COD 9000775 file currently verified at `/Users/Z/Documents/MATLAB/mtex-6.1.1/data/cif/quartz.cif`; preserve its COD public-domain header, publication citation, lattice, space-group name `P 32 2 1`, symmetry operations, and Si/O sites. Verify before adding:

```bash
shasum -a 256 /Users/Z/Documents/MATLAB/mtex-6.1.1/data/cif/quartz.cif
# 10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57
```

Create the recipe with this exact semantic content:

```yaml
schema: kikuchi.habit-recipe/v1
phase:
  name: quartz
  formula: SiO2
  space_group_number: 154
  cif: ../../phases/quartz/COD-9000775.cif
  sha256: 10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57
  provenance:
    uri: https://www.crystallography.net/cod/9000775.cif
    license: public-domain
    citation: Levien, Prewitt, and Weidner (1980), American Mineralogist 65, 920-930.
habit:
  index_convention: hkil
  faces:
    - {family: [1, 0, -1, 0], relative_distance: 0.5091702048436217, label: m}
    - {family: [1, 0, -1, 1], relative_distance: 1.0, label: r}
    - {family: [0, 1, -1, 1], relative_distance: 1.1111111111111112, label: z}
    - {family: [2, -1, -1, 1], relative_distance: 0.9557191976124586, label: s1}
    - {family: [6, -1, -5, 1], relative_distance: 0.7545681549701853, label: x1}
geometry:
  maximum_dimension_mm: 60.0
exports: [stl]
fdm_context:
  nozzle_width_mm: 0.4
  layer_height_mm: 0.2
```

- [ ] **Step 4: Implement immutable recipe types and strict loading**

Implement the public shape below. Validation helpers must reject booleans as
numbers, non-finite/non-positive values, duplicate labels, checksum mismatch,
unsupported exports, improper orientation matrices, and family
length/convention mismatch. CIF locators may be absolute or recipe-relative;
machine-local paths never enter content identity.

```python
# src/kikuchi_lab/habit/recipes.py
@dataclass(frozen=True)
class HabitFace:
    family: tuple[int, ...]
    relative_distance: float
    label: str


@dataclass(frozen=True)
class PhaseSource:
    name: str
    formula: str
    space_group_number: int
    cif_path: Path
    cif_sha256: str
    provenance: Mapping[str, str]


@dataclass(frozen=True)
class FDMContext:
    nozzle_width_mm: float
    layer_height_mm: float


@dataclass(frozen=True)
class HabitRecipe:
    schema: str
    phase: PhaseSource
    index_convention: str
    faces: tuple[HabitFace, ...]
    maximum_dimension_mm: float
    orientation_matrix: tuple[tuple[float, float, float], ...]
    exports: tuple[str, ...]
    fdm_context: FDMContext | None

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "phase": {
                "name": self.phase.name,
                "formula": self.phase.formula,
                "space_group_number": self.phase.space_group_number,
                "cif_sha256": self.phase.cif_sha256,
                "provenance": dict(self.phase.provenance),
            },
            "habit": {
                "index_convention": self.index_convention,
                "faces": [asdict(face) for face in self.faces],
            },
            "geometry": {
                "maximum_dimension_mm": self.maximum_dimension_mm,
                "orientation_matrix": [list(row) for row in self.orientation_matrix],
            },
            "exports": list(self.exports),
            "fdm_context": None if self.fdm_context is None else asdict(self.fdm_context),
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("habit-recipe", self.identity_dict())


def load_habit_recipe(path: str | Path) -> HabitRecipe:
    recipe_path = Path(path).resolve()
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "kikuchi.habit-recipe/v1":
        raise ValueError("unsupported habit recipe schema")
    phase_raw = _required_mapping(raw, "phase")
    habit_raw = _required_mapping(raw, "habit")
    geometry_raw = _required_mapping(raw, "geometry")
    convention = _required_text(habit_raw, "index_convention")
    if convention not in {"hkl", "hkil"}:
        raise ValueError("index_convention must be hkl or hkil")
    cif_locator = Path(_required_text(phase_raw, "cif"))
    cif_path = cif_locator if cif_locator.is_absolute() else recipe_path.parent / cif_locator
    cif_path = cif_path.resolve()
    observed_hash = hashlib.sha256(cif_path.read_bytes()).hexdigest()
    if observed_hash != _required_text(phase_raw, "sha256"):
        raise ValueError("habit CIF checksum mismatch")
    raw_faces = habit_raw.get("faces")
    if not isinstance(raw_faces, list) or not raw_faces:
        raise ValueError("habit faces must be a non-empty list")
    faces = tuple(_parse_face(item, convention) for item in raw_faces)
    if len({face.label for face in faces}) != len(faces):
        raise ValueError("habit face labels must be unique")
    orientation = np.asarray(geometry_raw.get("orientation_matrix", np.eye(3)), dtype=float)
    if orientation.shape != (3, 3) or not np.isfinite(orientation).all():
        raise ValueError("orientation_matrix must be a finite 3 by 3 matrix")
    if not np.allclose(orientation.T @ orientation, np.eye(3), atol=1e-12) or not np.isclose(
        np.linalg.det(orientation), 1.0, atol=1e-12
    ):
        raise ValueError("orientation_matrix must be a proper orthogonal rotation")
    return HabitRecipe(
        schema="kikuchi.habit-recipe/v1",
        phase=_parse_phase(phase_raw, cif_path, observed_hash),
        index_convention=convention,
        faces=faces,
        maximum_dimension_mm=_positive_float(geometry_raw, "maximum_dimension_mm"),
        orientation_matrix=tuple(tuple(float(v) for v in row) for row in orientation),
        exports=_parse_exports(raw.get("exports")),
        fdm_context=_parse_fdm_context(raw.get("fdm_context")),
    )
```

Implement `_required_mapping`, `_required_text`, and `_positive_float` as strict
type guards that reject booleans, blanks, and non-finite numbers. `_parse_face`
must enforce exact integer indices, convention length, `hkil` closure, positive
distance, and a safe non-empty label. `_parse_phase` validates name, formula,
space-group integer `[1, 230]`, three required provenance strings, and freezes
the mapping. `_parse_exports` accepts exactly the non-empty tuple `("stl",)`;
`_parse_fdm_context` accepts `None` or two positive finite millimetre values.
Export the five public types and loader from `src/kikuchi_lab/habit/__init__.py`.

Add tests asserting an omitted orientation becomes exact identity and a matrix
with determinant `-1` fails with `proper orthogonal rotation`.

```python
def test_orientation_defaults_to_identity():
    recipe = load_habit_recipe(RECIPE)
    assert recipe.orientation_matrix == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def test_recipe_rejects_reflection_matrix(tmp_path: Path):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = RECIPE.read_text(encoding="utf-8").replace(
        "../../phases/quartz/COD-9000775.cif", str(cif)
    ).replace(
        "maximum_dimension_mm: 60.0",
        "maximum_dimension_mm: 60.0\n  orientation_matrix: [[-1,0,0],[0,1,0],[0,0,1]]",
    )
    candidate = tmp_path / "reflection.yml"
    candidate.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="proper orthogonal rotation"):
        load_habit_recipe(candidate)
```

- [ ] **Step 5: Run recipe and existing regression tests**

Run: `uv run pytest tests/unit/habit/test_habit_recipes.py tests/unit/test_recipes.py tests/adapters/test_forsterite_source.py -q`

Expected: all selected tests pass; quartz loading does not change the stricter forsterite simulation-source contract.

- [ ] **Step 6: Commit the accepted recipe slice**

```bash
git add src/kikuchi_lab/habit phases/quartz recipes/habits tests/unit/habit
git commit -m "feat: define crystal habit recipes"
```

---

### Task 2: Expand crystallographic habit planes (`KIKU-T026`)

**Files:**
- Create: `src/kikuchi_lab/habit/crystallography.py`
- Create: `tests/scientific/habit/test_crystallography.py`
- Modify: `src/kikuchi_lab/habit/__init__.py`

**Interfaces:**
- Consumes: `HabitRecipe` from Task 1 and `orix.crystal_map.Phase.from_cif` only at this boundary.
- Produces: `CrystalPhase`, `ExpandedPlane`, and `expand_habit_planes(recipe: HabitRecipe) -> tuple[CrystalPhase, tuple[ExpandedPlane, ...]]`.
- `ExpandedPlane.normal` is an immutable three-float tuple in the recorded `X||a*, Z||c` frame; downstream code never receives orix or diffpy objects.

- [ ] **Step 1: Write failing frame and symmetry-expansion tests**

```python
# tests/scientific/habit/test_crystallography.py
import numpy as np
import pytest

from kikuchi_lab.habit.crystallography import expand_habit_planes
from kikuchi_lab.habit.recipes import load_habit_recipe


def test_quartz_expansion_is_in_explicit_mtex_compatible_crystal_frame():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    phase, planes = expand_habit_planes(recipe)

    assert phase.space_group_number == 154
    assert phase.point_group == "32"
    assert phase.frame == "X||a*, Y||cross(c,a*), Z||c"
    assert len(planes) == 30
    assert {label: sum(p.family_label == label for p in planes) for label in "mrz"} == {
        "m": 6,
        "r": 6,
        "z": 6,
    }
    m_normals = np.array([p.normal for p in planes if p.family_label == "m"])
    assert np.max(np.abs(m_normals[:, 2])) <= 1e-12
    assert any(np.allclose(normal, [1.0, 0.0, 0.0], atol=1e-12) for normal in m_normals)
    assert all(np.linalg.norm(p.normal) == pytest.approx(1.0) for p in planes)


def test_expansion_keeps_positive_and_negative_rhombohedra_distinct():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    r = {tuple(np.round(p.normal, 10)) for p in planes if p.family_label == "r"}
    z = {tuple(np.round(p.normal, 10)) for p in planes if p.family_label == "z"}
    assert r.isdisjoint(z)
```

- [ ] **Step 2: Run the focused test and confirm the missing module failure**

Run: `uv run pytest tests/scientific/habit/test_crystallography.py -q`

Expected: collection fails because `kikuchi_lab.habit.crystallography` does not exist.

- [ ] **Step 3: Implement the crystallography boundary and explicit frame**

Use column-vector reciprocal coordinates (`lattice.recbase @ hkl`), not row multiplication. The latter gives the wrong hexagonal `d100`. Construct the frame before symmetry expansion and sort deduplicated normals lexicographically after rounding only for ordering, never for stored values.

```python
# src/kikuchi_lab/habit/crystallography.py
@dataclass(frozen=True)
class CrystalPhase:
    name: str
    formula: str
    space_group_number: int
    point_group: str
    lattice_angstrom: tuple[float, float, float, float, float, float]
    frame: str
    cif_sha256: str


@dataclass(frozen=True)
class ExpandedPlane:
    plane_id: str
    family_label: str
    family_indices: tuple[int, ...]
    symmetry_index: int
    normal: tuple[float, float, float]
    relative_distance: float


def _hkl(indices: tuple[int, ...], convention: str) -> np.ndarray:
    if convention == "hkil":
        h, k, i, ell = indices
        if h + k + i != 0:
            raise ValueError("hkil family requires h + k + i = 0")
        return np.array([h, k, ell], dtype=np.float64)
    return np.array(indices, dtype=np.float64)


def _frame_matrix(lattice: Lattice) -> np.ndarray:
    a_star = lattice.recbase @ np.array([1.0, 0.0, 0.0])
    c_axis = lattice.cartesian([0.0, 0.0, 1.0])
    x = a_star / np.linalg.norm(a_star)
    z = c_axis / np.linalg.norm(c_axis)
    y = np.cross(z, x)
    y /= np.linalg.norm(y)
    return np.vstack([x, y, z])


def expand_habit_planes(recipe: HabitRecipe) -> tuple[CrystalPhase, tuple[ExpandedPlane, ...]]:
    upstream = Phase.from_cif(recipe.phase.cif_path)
    if upstream.space_group is None or upstream.space_group.number != recipe.phase.space_group_number:
        raise ValueError("CIF space group disagrees with habit recipe")
    lattice = upstream.structure.lattice
    frame = _frame_matrix(lattice)
    expanded: list[ExpandedPlane] = []
    for family in recipe.faces:
        reciprocal = lattice.recbase @ _hkl(family.family, recipe.index_convention)
        reciprocal /= np.linalg.norm(reciprocal)
        native_orbit = upstream.point_group.outer(Vector3d(reciprocal)).data.reshape(-1, 3)
        orbit = (frame @ native_orbit.T).T
        orbit = _deduplicate_and_sort_unit_normals(orbit, tolerance=1e-12)
        for symmetry_index, normal in enumerate(orbit):
            content = {
                "family_label": family.label,
                "family_indices": list(family.family),
                "symmetry_index": symmetry_index,
                "normal": normal.tolist(),
                "relative_distance": family.relative_distance,
            }
            expanded.append(ExpandedPlane(
                plane_id=stable_id("habit-plane", content),
                family_label=family.label,
                family_indices=family.family,
                symmetry_index=symmetry_index,
                normal=tuple(float(value) for value in normal),
                relative_distance=family.relative_distance,
            ))
    return _plain_phase(recipe, upstream), tuple(expanded)
```

- [ ] **Step 4: Add failure tests for zero reciprocal vectors and mismatched space groups**

```python
from dataclasses import replace


def test_expansion_rejects_zero_reciprocal_normal():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    invalid_face = replace(recipe.faces[0], family=(0, 0, 0, 0))
    invalid = replace(recipe, faces=(invalid_face, *recipe.faces[1:]))
    with pytest.raises(ValueError, match="zero reciprocal-plane normal"):
        expand_habit_planes(invalid)


def test_expansion_rejects_declared_space_group_mismatch():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    invalid = replace(recipe, phase=replace(recipe.phase, space_group_number=152))
    with pytest.raises(ValueError, match="space group disagrees"):
        expand_habit_planes(invalid)
```

- [ ] **Step 5: Run the crystallography ladder**

Run: `uv run pytest tests/scientific/habit/test_crystallography.py tests/adapters/test_kikuchipy_projection.py -q`

Expected: all tests pass and existing projection-frame behavior is unchanged.

- [ ] **Step 6: Commit the crystallography slice**

```bash
git add src/kikuchi_lab/habit tests/scientific/habit
git commit -m "feat: expand crystallographic habit planes"
```

---

### Task 3: Solve labeled convex crystal habits (`KIKU-T027`)

**Files:**
- Create: `src/kikuchi_lab/habit/geometry.py`
- Create: `tests/scientific/habit/test_habit_geometry.py`
- Modify: `src/kikuchi_lab/habit/__init__.py`

**Interfaces:**
- Consumes: `ExpandedPlane` from Task 2.
- Produces: `PolygonFace`, `LabeledPolygonMesh`, `TriangleMesh`,
  `solve_convex_habit(planes)`,
  `orient_and_scale_habit(mesh, orientation_matrix, maximum_dimension_mm)`, and
  `triangulate_habit(mesh)`.
- Polygon faces retain plane IDs and Miller-family provenance; `TriangleMesh.triangle_face_indices` maps every triangle back to its source polygon.

- [ ] **Step 1: Write analytic cube and quartz topology tests**

```python
# tests/scientific/habit/test_habit_geometry.py
import numpy as np
import pytest

from kikuchi_lab.habit.crystallography import ExpandedPlane, expand_habit_planes
from kikuchi_lab.habit.geometry import (
    orient_and_scale_habit,
    solve_convex_habit,
    triangulate_habit,
)
from kikuchi_lab.habit.recipes import load_habit_recipe


def _plane(label: str, normal: tuple[float, float, float]) -> ExpandedPlane:
    return ExpandedPlane(label, label, (1, 0, 0), 0, normal, 1.0)


def test_cube_has_ordered_labeled_faces_and_deterministic_triangles():
    planes = tuple(
        _plane(label, normal)
        for label, normal in (
            ("+x", (1, 0, 0)), ("-x", (-1, 0, 0)),
            ("+y", (0, 1, 0)), ("-y", (0, -1, 0)),
            ("+z", (0, 0, 1)), ("-z", (0, 0, -1)),
        )
    )
    polygon = solve_convex_habit(planes)
    triangle = triangulate_habit(polygon)

    assert polygon.vertices.shape == (8, 3)
    assert len(polygon.faces) == 6
    assert polygon.inactive_plane_ids == ()
    assert triangle.triangles.shape == (12, 3)
    assert np.array_equal(triangle.triangles, triangulate_habit(polygon).triangles)


def test_quartz_matches_reference_topology_before_parity_metrics():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    polygon = solve_convex_habit(planes)
    scaled = orient_and_scale_habit(
        polygon, recipe.orientation_matrix, recipe.maximum_dimension_mm
    )

    assert polygon.vertices.shape == (32, 3)
    assert len(polygon.faces) == 18
    assert len(polygon.inactive_plane_ids) == 12
    assert np.ptp(scaled.vertices, axis=0).max() == pytest.approx(60.0, abs=1e-8)
```

- [ ] **Step 2: Run the focused tests and confirm the missing geometry module failure**

Run: `uv run pytest tests/scientific/habit/test_habit_geometry.py -q`

Expected: collection fails because `kikuchi_lab.habit.geometry` does not exist.

- [ ] **Step 3: Implement bounded half-space intersection and labeled polygons**

Use the strict interior point `[0, 0, 0]` because every support distance is positive. Convert each plane to Qhull form `[nx, ny, nz, -distance]`. Catch `QhullError` and raise a domain message naming an empty, unbounded, or numerically unstable plane set.

```python
# src/kikuchi_lab/habit/geometry.py
@dataclass(frozen=True)
class PolygonFace:
    plane_id: str
    family_label: str
    family_indices: tuple[int, ...]
    symmetry_index: int
    normal: tuple[float, float, float]
    support_distance: float
    vertex_indices: tuple[int, ...]


@dataclass(frozen=True)
class LabeledPolygonMesh:
    vertices: np.ndarray
    faces: tuple[PolygonFace, ...]
    inactive_plane_ids: tuple[str, ...]


def solve_convex_habit(
    planes: tuple[ExpandedPlane, ...], *, relative_tolerance: float = 1e-9
) -> LabeledPolygonMesh:
    unique_planes, duplicate_ids = _deduplicate_halfspaces(planes, relative_tolerance)
    halfspaces = np.array([
        (*plane.normal, -plane.relative_distance) for plane in unique_planes
    ])
    try:
        raw_vertices = HalfspaceIntersection(halfspaces, np.zeros(3)).intersections
    except QhullError as error:
        raise ValueError("habit planes do not define one stable bounded solid") from error
    vertices = _deduplicate_vertices(raw_vertices, relative_tolerance)
    faces: list[PolygonFace] = []
    inactive: list[str] = []
    scale = max(float(np.linalg.norm(vertices, axis=1).max()), 1.0)
    tolerance = relative_tolerance * scale
    for plane in unique_planes:
        normal = np.asarray(plane.normal)
        members = np.flatnonzero(
            np.abs(vertices @ normal - plane.relative_distance) <= tolerance
        )
        if len(members) < 3:
            inactive.append(plane.plane_id)
            continue
        ordered = _counterclockwise_face_order(vertices, members, normal)
        faces.append(_polygon_face(plane, ordered))
    if not faces:
        raise ValueError("habit intersection has no visible polygon faces")
    return LabeledPolygonMesh(
        _immutable_vertices(vertices), tuple(faces), tuple((*duplicate_ids, *inactive))
    )
```

`_counterclockwise_face_order` must build an orthonormal in-plane basis, sort `atan2` around the centroid, rotate the index cycle so its smallest vertex ID is first, and reverse once when the polygon cross-sum points inward.
`_deduplicate_halfspaces` compares normalized normals and support distances at
the recorded relative tolerance, retains the lexicographically smallest
`plane_id`, and records every removed plane ID as inactive evidence.

- [ ] **Step 4: Implement explicit scaling and deterministic fan triangulation**

```python
@dataclass(frozen=True)
class TriangleMesh:
    vertices: np.ndarray
    triangles: np.ndarray
    triangle_face_indices: np.ndarray


def orient_and_scale_habit(
    mesh: LabeledPolygonMesh,
    orientation_matrix: tuple[tuple[float, float, float], ...],
    maximum_dimension_mm: float,
) -> LabeledPolygonMesh:
    rotation = np.asarray(orientation_matrix, dtype=float)
    oriented = mesh.vertices @ rotation.T
    extent = float(np.ptp(oriented, axis=0).max())
    if not np.isfinite(extent) or extent <= 0:
        raise ValueError("habit has no positive finite axis-aligned extent")
    center = (oriented.min(axis=0) + oriented.max(axis=0)) / 2
    centered = oriented - center
    factor = maximum_dimension_mm / extent
    rotated_faces = []
    for face in mesh.faces:
        normal = rotation @ np.asarray(face.normal)
        rotated_faces.append(replace(
            face,
            normal=tuple(float(value) for value in normal),
            support_distance=float(factor * (face.support_distance - np.dot(normal, center))),
        ))
    return replace(
        mesh,
        vertices=_immutable_vertices(centered * factor),
        faces=tuple(rotated_faces),
    )


def triangulate_habit(mesh: LabeledPolygonMesh) -> TriangleMesh:
    triangles: list[tuple[int, int, int]] = []
    owners: list[int] = []
    for face_index, face in enumerate(mesh.faces):
        anchor, *ring = face.vertex_indices
        for left, right in zip(ring, ring[1:], strict=False):
            triangle = (anchor, left, right)
            if np.dot(
                np.cross(mesh.vertices[left] - mesh.vertices[anchor],
                         mesh.vertices[right] - mesh.vertices[anchor]),
                face.normal,
            ) < 0:
                triangle = (anchor, right, left)
            triangles.append(triangle)
            owners.append(face_index)
    return TriangleMesh(
        _immutable_vertices(mesh.vertices),
        _immutable_int_array(triangles, width=3),
        _immutable_int_array(owners, width=None),
    )
```

- [ ] **Step 5: Add explicit invalid-geometry tests**

```python
def test_solver_rejects_unbounded_slab():
    with pytest.raises(ValueError, match="stable bounded solid"):
        solve_convex_habit((_plane("+x", (1, 0, 0)), _plane("-x", (-1, 0, 0))))


def test_solver_records_duplicate_plane_as_inactive():
    cube = tuple(
        _plane(label, normal)
        for label, normal in (
            ("+x", (1, 0, 0)), ("-x", (-1, 0, 0)),
            ("+y", (0, 1, 0)), ("-y", (0, -1, 0)),
            ("+z", (0, 0, 1)), ("-z", (0, 0, -1)),
        )
    )
    duplicate = replace(cube[0], plane_id="duplicate-+x")
    mesh = solve_convex_habit((*cube, duplicate))
    assert "duplicate-+x" in mesh.inactive_plane_ids
    assert len(mesh.faces) == 6
```

Also rotate a rectangular analytic habit by a proper 90-degree matrix, assert
its X/Y extents swap before normalization, and assert a reflection matrix is
rejected by the recipe layer rather than accepted here.

- [ ] **Step 6: Run the solver ladder**

Run: `uv run pytest tests/scientific/habit/test_habit_geometry.py tests/scientific/habit/test_crystallography.py -q`

Expected: all tests pass, including the `32`-vertex/`18`-face quartz pre-parity topology gate.

- [ ] **Step 7: Commit the solver slice**

```bash
git add src/kikuchi_lab/habit tests/scientific/habit
git commit -m "feat: solve labeled convex crystal habits"
```

---

### Task 4: Validate and export printable triangle meshes (`KIKU-T028`)

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/kikuchi_lab/habit/mesh.py`
- Create: `tests/unit/habit/test_habit_mesh.py`
- Modify: `src/kikuchi_lab/habit/__init__.py`

**Interfaces:**
- Consumes: `LabeledPolygonMesh`, `TriangleMesh`, and optional `FDMContext`.
- Produces: `MeshValidation`, `validate_triangle_mesh(mesh, polygon, fdm_context)`, `stl_bytes(mesh)`, and `write_habit_preview(path, polygon)`.
- Trimesh is an inspection/export adapter instantiated only as `trimesh.Trimesh(..., process=False)`.

- [ ] **Step 1: Add direct pinned-major dependencies**

Run:

```bash
uv add "trimesh>=4.12.2,<5" "matplotlib>=3.11,<4"
```

Expected: `pyproject.toml` gains direct dependencies and `uv.lock` resolves stable Trimesh `4.12.2`, not the `5.0.0rc1` prerelease.

- [ ] **Step 2: Write failing non-mutation, validation, STL, and preview tests**

```python
# tests/unit/habit/test_habit_mesh.py
import hashlib
import io
from dataclasses import replace
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pytest
import trimesh

from kikuchi_lab.habit.mesh import stl_bytes, validate_triangle_mesh, write_habit_preview


def test_cube_validation_and_stl_export_do_not_mutate_geometry(cube_polygon, cube_triangles):
    before_vertices = cube_triangles.vertices.copy()
    before_faces = cube_triangles.triangles.copy()
    report = validate_triangle_mesh(cube_triangles, cube_polygon, fdm_context=None)
    payload = stl_bytes(cube_triangles)

    assert report.passed is True
    assert report.watertight is True
    assert report.winding_consistent is True
    assert report.body_count == 1
    assert report.convex is True
    assert report.volume > 0
    assert np.array_equal(cube_triangles.vertices, before_vertices)
    assert np.array_equal(cube_triangles.triangles, before_faces)
    assert payload == stl_bytes(cube_triangles)
    loaded = trimesh.load_mesh(file_obj=io.BytesIO(payload), file_type="stl", process=False)
    assert loaded.is_volume


def test_validation_rejects_missing_triangle_without_repair(cube_polygon, cube_triangles):
    broken = replace(cube_triangles, triangles=cube_triangles.triangles[:-1])
    with pytest.raises(ValueError, match="watertight"):
        validate_triangle_mesh(broken, cube_polygon, fdm_context=None)


def test_preview_is_deterministic_rgba_png(tmp_path: Path, cube_polygon):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    write_habit_preview(first, cube_polygon)
    write_habit_preview(second, cube_polygon)
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    assert iio.imread(first).shape == (900, 900, 4)
```

- [ ] **Step 3: Run focused tests and confirm the missing mesh module failure**

Run: `uv run pytest tests/unit/habit/test_habit_mesh.py -q`

Expected: collection fails because `kikuchi_lab.habit.mesh` does not exist.

- [ ] **Step 4: Implement non-mutating canonical validation**

```python
# src/kikuchi_lab/habit/mesh.py
@dataclass(frozen=True)
class MeshValidation:
    passed: bool
    watertight: bool
    winding_consistent: bool
    body_count: int
    convex: bool
    volume: float
    surface_area: float
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    maximum_dimension_mm: float
    degenerate_triangle_count: int
    duplicate_triangle_count: int
    self_intersection_contract: str
    warnings: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def _trimesh(mesh: TriangleMesh) -> trimesh.Trimesh:
    return trimesh.Trimesh(
        vertices=np.array(mesh.vertices, copy=True),
        faces=np.array(mesh.triangles, copy=True),
        process=False,
        validate=False,
    )


def validate_triangle_mesh(
    mesh: TriangleMesh,
    polygon: LabeledPolygonMesh,
    fdm_context: FDMContext | None,
) -> MeshValidation:
    inspected = _trimesh(mesh)
    duplicate_count = _duplicate_triangle_count(mesh.triangles)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= 1e-12))
    failures = []
    if not inspected.is_watertight: failures.append("watertight")
    if not inspected.is_winding_consistent: failures.append("winding")
    if inspected.body_count != 1: failures.append("one connected body")
    if not inspected.is_convex: failures.append("convex")
    if not inspected.is_volume or inspected.volume <= 0: failures.append("positive volume")
    if duplicate_count: failures.append("duplicate triangles")
    if degenerate_count: failures.append("degenerate triangles")
    _assert_triangle_face_provenance(mesh, polygon)
    if failures:
        raise ValueError("mesh validation failed: " + ", ".join(failures))
    bounds = np.asarray(inspected.bounds, dtype=float)
    return MeshValidation(
        passed=True,
        watertight=True,
        winding_consistent=True,
        body_count=1,
        convex=True,
        volume=float(inspected.volume),
        surface_area=float(inspected.area),
        bounds_mm=(tuple(bounds[0]), tuple(bounds[1])),
        maximum_dimension_mm=float(inspected.extents.max()),
        degenerate_triangle_count=0,
        duplicate_triangle_count=0,
        self_intersection_contract="convex-watertight-volume-proof",
        warnings=_fdm_warnings(inspected, polygon, fdm_context),
    )
```

`_assert_triangle_face_provenance` must verify every triangle's three vertices belong to its source polygon and its cross product points along the polygon's outward normal. FDM warnings must include exact face/edge IDs and thresholds; they may inspect minimum edge length, minimum triangle altitude, acute vertex solid angle, and downward face angle, but return data only.

- [ ] **Step 5: Implement deterministic binary STL and fixed preview**

`stl_bytes` may call `inspected.export(file_type="stl")` only after canonical validation has passed; assert the result is `bytes`. `write_habit_preview` must use Matplotlib Agg, `Poly3DCollection`, a stable family-label color map, fixed camera `(elev=22, azim=38)`, equal axis limits, a family legend, transparent=False, and fixed `figsize=(9, 9), dpi=100`.

- [ ] **Step 6: Run mesh and regression tests**

Run: `uv run pytest tests/unit/habit/test_habit_mesh.py tests/scientific/habit/test_habit_geometry.py -q`

Expected: all tests pass; the broken mesh is rejected rather than repaired.

Run: `uv run ruff check src/kikuchi_lab/habit tests/unit/habit tests/scientific/habit`

Expected: no lint violations.

- [ ] **Step 7: Commit the mesh spine**

```bash
git add pyproject.toml uv.lock src/kikuchi_lab/habit tests/unit/habit tests/scientific/habit
git commit -m "feat: validate and export crystal habit meshes"
```

---

### Task 5: Build atomic habit bundles through the CLI (`KIKU-T029`)

**Files:**
- Create: `src/kikuchi_lab/habit/workflow.py`
- Create: `tests/integration/test_habit_workflow.py`
- Modify: `src/kikuchi_lab/habit/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1-4 public contracts.
- Produces: `HabitBuildResult` and `build_habit(recipe_path, output_root) -> HabitBuildResult`.
- CLI: `kikuchi-lab habit build --recipe PATH --output ROOT` prints one JSON result and returns `1` with a concise `habit build failed` message on domain errors.

- [ ] **Step 1: Write failing atomic-bundle and CLI tests**

```python
# tests/integration/test_habit_workflow.py
import hashlib
import json
from pathlib import Path

import pytest
import trimesh

from kikuchi_lab.habit.workflow import build_habit


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def test_quartz_build_is_atomic_reproducible_and_complete(tmp_path: Path):
    recipe = "recipes/habits/quartz-mtex-example.yml"
    first = build_habit(recipe, tmp_path / "first")
    second = build_habit(recipe, tmp_path / "second")

    assert first.build_id == second.build_id
    assert _tree_hashes(first.path) == _tree_hashes(second.path)
    assert {path.name for path in first.path.iterdir()} == {
        "quartz-habit.stl",
        "quartz-habit-preview.png",
        "habit-manifest.json",
        "mesh-validation.json",
    }
    manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
    assert manifest["units"] == "millimetre"
    assert manifest["recipe_id"].startswith("habit-recipe-")
    assert manifest["visible_family_labels"] == ["m", "r", "z"]
    assert manifest["inactive_plane_count"] == 12
    loaded = trimesh.load_mesh(first.stl, process=False)
    assert loaded.is_volume and loaded.body_count == 1
    assert loaded.extents.max() == pytest.approx(60.0, abs=1e-8)
```

```python
# additions to tests/unit/test_cli.py
from pathlib import Path
from types import SimpleNamespace


def test_habit_build_cli_routes_arguments_and_prints_json(monkeypatch, capsys):
    expected = SimpleNamespace(
        build_id="habit-build-abc123",
        path=Path("/tmp/habit-build-abc123"),
        stl=Path("/tmp/habit-build-abc123/quartz-habit.stl"),
        preview=Path("/tmp/habit-build-abc123/quartz-habit-preview.png"),
        validation=Path("/tmp/habit-build-abc123/mesh-validation.json"),
    )
    calls = []
    monkeypatch.setattr(
        "kikuchi_lab.habit.build_habit",
        lambda recipe, output: calls.append((recipe, output)) or expected,
    )

    assert main(["habit", "build", "--recipe", "r.yml", "--output", "out"]) == 0
    assert calls == [("r.yml", "out")]
    assert json.loads(capsys.readouterr().out)["build_id"] == expected.build_id


def test_habit_build_cli_reports_domain_error_without_traceback(monkeypatch, capsys):
    def fail(*_args):
        raise ValueError("maximum_dimension_mm must be positive")

    monkeypatch.setattr("kikuchi_lab.habit.build_habit", fail)
    assert main(["habit", "build", "--recipe", "bad.yml", "--output", "out"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "kikuchi-lab: habit build failed: maximum_dimension_mm must be positive\n"
    )
    assert "Traceback" not in captured.err
```

- [ ] **Step 2: Run focused tests and confirm the missing workflow/command failures**

Run: `uv run pytest tests/integration/test_habit_workflow.py tests/unit/test_cli.py -q`

Expected: habit workflow import or `habit` CLI parsing fails.

- [ ] **Step 3: Implement the content-addressed atomic workflow**

```python
# src/kikuchi_lab/habit/workflow.py
@dataclass(frozen=True)
class HabitBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    validation: Path
    parity: Path | None = None


def build_habit(recipe_path: str | Path, output_root: str | Path) -> HabitBuildResult:
    recipe = load_habit_recipe(recipe_path)
    phase, planes = expand_habit_planes(recipe)
    polygon = orient_and_scale_habit(
        solve_convex_habit(planes),
        recipe.orientation_matrix,
        recipe.maximum_dimension_mm,
    )
    triangles = triangulate_habit(polygon)
    report = validate_triangle_mesh(triangles, polygon, recipe.fdm_context)
    identity = {
        "schema": "kikuchi.habit-build/v1",
        "recipe": recipe.identity_dict(),
        "phase": asdict(phase),
        "solver": SOLVER_CONTRACT,
        "mesh_contract": MESH_CONTRACT,
    }
    build_id = stable_id("habit-build", identity)
    root = Path(output_root).resolve()
    staging = root / f"{build_id}.partial"
    completed = root / build_id
    _require_fresh_destinations(staging, completed)
    staging.mkdir(parents=True)
    try:
        stem = f"{_safe_slug(recipe.phase.name)}-habit"
        (staging / f"{stem}.stl").write_bytes(stl_bytes(triangles))
        write_habit_preview(staging / f"{stem}-preview.png", polygon)
        _write_json(staging / "mesh-validation.json", report.to_dict())
        manifest = _manifest(identity, recipe, phase, planes, polygon, triangles, report, staging)
        _write_json(staging / "habit-manifest.json", manifest)
        _fsync_tree(staging)
        os.replace(staging, completed)
        _fsync_directory(root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return _result(build_id, completed)
```

`_safe_slug` must require lowercase ASCII alphanumerics separated only by single
hyphens and reject an empty result. The manifest must contain recipe/CIF
identity, phase and frame, orientation matrix, expanded planes, visible
polygons, inactive plane IDs, triangle-to-polygon mapping, units, tolerances,
software versions, validation report link, and a complete SHA-256/byte-size
inventory excluding the manifest itself.

- [ ] **Step 4: Add the nested `habit build` CLI**

```python
habit = subparsers.add_parser("habit", help="Build and inspect printable crystal habits.")
habit_commands = habit.add_subparsers(dest="habit_command", required=True)
habit_build = habit_commands.add_parser("build", help="Build one validated habit bundle.")
habit_build.add_argument("--recipe", required=True)
habit_build.add_argument("--output", required=True)

# After parsing:
if args.command == "habit" and args.habit_command == "build":
    from kikuchi_lab.habit import build_habit
    try:
        result = build_habit(args.recipe, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"kikuchi-lab: habit build failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({
        "build_id": result.build_id,
        "path": str(result.path),
        "stl": str(result.stl),
        "preview": str(result.preview),
        "validation": str(result.validation),
    }, indent=2, sort_keys=True))
    return 0
```

- [ ] **Step 5: Run workflow, CLI, reproducibility, and full fast tests**

Run: `uv run pytest tests/integration/test_habit_workflow.py tests/unit/test_cli.py -q`

Expected: focused workflow and CLI tests pass.

Run: `uv run pytest -m "not gpu and not slow" -q`

Expected: full fast suite passes with no changes to existing pattern products.

- [ ] **Step 6: Build and inspect the first real local quartz bundle**

Run:

```bash
uv run kikuchi-lab habit build \
  --recipe recipes/habits/quartz-mtex-example.yml \
  --output local/habits/quartz
```

Expected: JSON names a content-addressed bundle containing the four required files; `mesh-validation.json` reports `passed: true`, `body_count: 1`, `watertight: true`, and `maximum_dimension_mm: 60.0` within tolerance. Open the PNG and STL/slicer view for human inspection before committing.

- [ ] **Step 7: Commit the production workflow**

```bash
git add src/kikuchi_lab/habit src/kikuchi_lab/cli/main.py tests/integration/test_habit_workflow.py tests/unit/test_cli.py
git commit -m "feat: build atomic crystal habit bundles"
```

---

### Task 6: Prove quartz parity against MTEX (`KIKU-T030`)

**Files:**
- Create: `scripts/export_mtex_habit_reference.m`
- Create: `reference/habits/quartz-mtex-request.json`
- Create: `reference/habits/quartz-mtex-6.1.1.json`
- Create: `src/kikuchi_lab/habit/parity.py`
- Create: `tests/integration/test_mtex_habit_parity.py`
- Modify: `src/kikuchi_lab/habit/workflow.py`
- Modify: `src/kikuchi_lab/habit/__init__.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `pytest.ini`
- Create: `docs/acceptance/crystal-habit-mesh.md`
- Modify: `docs/work/KIKU-T025.md` through `docs/work/KIKU-T030.md`
- Modify: `docs/work/KIKU-F004.md`

**Interfaces:**
- Consumes: accepted polygon/triangle geometry from Tasks 3-5 and a plain MTEX JSON ledger.
- Produces: `MTEXParityReport`, `compare_mtex_reference(polygon, ledger_path)`, optional `build_habit(..., mtex_reference=...)`, CLI `--mtex-reference`, and `mtex-parity.json` in acceptance bundles.

- [ ] **Step 1: Add the exact plain MTEX reference request**

```json
{
  "schema": "kikuchi.mtex-habit-request/v1",
  "cif": "../../phases/quartz/COD-9000775.cif",
  "mtex_version": "6.1.1",
  "families": [
    {"label": "m", "indices": [1, 0, -1, 0], "normal_multiplier": 2.5},
    {"label": "r", "indices": [1, 0, -1, 1], "normal_multiplier": 1.0},
    {"label": "z", "indices": [0, 1, -1, 1], "normal_multiplier": 0.9},
    {"label": "s1", "indices": [2, -1, -1, 1], "normal_multiplier": 0.7},
    {"label": "x1", "indices": [6, -1, -5, 1], "normal_multiplier": 0.3}
  ]
}
```

- [ ] **Step 2: Write the MTEX exporter and generate the compact ledger**

The MATLAB function must resolve CIF paths relative to the request, initialize `KIKUCHI_MTEX_ROOT`, build each `Miller` family, construct `crystalShape`, remove `NaN` face padding, assign each expanded face to the nearest same-direction symmetrized input family, and write vertices/faces/normals/labels plus request/CIF hashes. Recompute volume downstream; record MTEX's convenience `cS.volume` only as non-authoritative diagnostic because it returned `NaN` for this shape.

Run:

```bash
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
  /Applications/MATLAB_R2025b.app/bin/matlab -batch \
  "addpath('scripts'); export_mtex_habit_reference('reference/habits/quartz-mtex-request.json','reference/habits/quartz-mtex-6.1.1.json')"
```

The MATLAB implementation must include this non-interactive spine:

```matlab
function export_mtex_habit_reference(requestPath, outputPath)
requestPath = char(java.io.File(requestPath).getCanonicalPath());
outputPath = char(java.io.File(outputPath).getCanonicalPath());
request = jsondecode(fileread(requestPath));
mtexRoot = getenv('KIKUCHI_MTEX_ROOT');
assert(isfolder(mtexRoot), 'KIKUCHI_MTEX_ROOT must name MTEX 6.1.1');
oldFolder = pwd; restoreFolder = onCleanup(@() cd(oldFolder));
cd(mtexRoot); addpath(mtexRoot); startup_mtex('noMenu');
assert(strcmp(mtexVersion, request.mtex_version));
requestRoot = fileparts(requestPath);
cifPath = char(java.io.File(requestRoot, request.cif).getCanonicalPath());
cs = loadCIF(cifPath);
familyNormals = cell(numel(request.families), 1);
for k = 1:numel(request.families)
  item = request.families(k);
  values = num2cell(double(item.indices));
  familyNormals{k} = item.normal_multiplier * Miller(values{:}, cs);
end
N = [familyNormals{:}];
cS = crystalShape(N);
expanded = unique(vector3d(N.symmetrise), 'stable');
faces = struct('vertex_indices', {}, 'normal', {}, 'family_label', {});
for k = 1:size(cS.F, 1)
  ids = cS.F(k, ~isnan(cS.F(k, :)));
  if isempty(ids), continue; end
  faces(end + 1).vertex_indices = int32(ids - 1); %#ok<AGROW>
  faces(end).normal = expanded(k).xyz;
  faces(end).family_label = matchFamilyLabel(expanded(k), request.families, cs);
end
ledger.schema = 'kikuchi.mtex-habit-reference/v1';
ledger.mtex.version = mtexVersion;
ledger.vertices = cS.V.xyz;
ledger.faces = faces;
ledger.non_authoritative_crystal_shape_volume = [];
ledger.non_authoritative_volume_diagnostic = 'crystalShape.volume returned NaN';
writeCanonicalJson(outputPath, ledger);
end
```

Implement `matchFamilyLabel` by converting each request entry's numeric index
array with `values = num2cell(double(item.indices))`, constructing
`candidate = Miller(values{:}, cs)`, and comparing the expanded normal against
`unique(vector3d(candidate.symmetrise))`. Require a same-direction normalized
dot product of at least `1 - 1e-10`. `writeCanonicalJson` writes
`jsonencode(ledger)` plus one newline and errors rather than emitting non-finite
numeric JSON.

Expected ledger summary: MTEX `6.1.1`, `32` vertices, `18` visible polygon
faces, visible labels `m`, `r`, and `z`, unit MTEX crystal-shape diameter,
finite coordinates, and no empty visible face.

- [ ] **Step 3: Write failing parity tests against the committed ledger**

```python
# tests/integration/test_mtex_habit_parity.py
import json
import os
from pathlib import Path
import subprocess

import pytest

from kikuchi_lab.habit.crystallography import expand_habit_planes
from kikuchi_lab.habit.geometry import solve_convex_habit
from kikuchi_lab.habit.parity import compare_mtex_reference
from kikuchi_lab.habit.recipes import load_habit_recipe

ROOT = Path(__file__).parents[2]


def test_quartz_python_geometry_passes_mtex_611_contract():
    recipe = load_habit_recipe(ROOT / "recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    polygon = solve_convex_habit(planes)
    report = compare_mtex_reference(
        polygon, ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    )

    assert report.passed is True
    assert report.python_vertex_count == report.mtex_vertex_count == 32
    assert report.python_face_count == report.mtex_face_count == 18
    assert report.vertex_hausdorff <= 1e-7
    assert report.relative_volume_difference <= 1e-6
    assert report.maximum_face_normal_angle_rad <= 1e-7
    assert report.visible_family_labels == ("m", "r", "z")
```

```python
def test_parity_names_vertex_hausdorff_when_ledger_vertex_is_perturbed(
    tmp_path: Path,
):
    source = ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    ledger = json.loads(source.read_text(encoding="utf-8"))
    ledger["vertices"][0][0] += 1e-4
    perturbed = tmp_path / "perturbed.json"
    perturbed.write_text(json.dumps(ledger) + "\n", encoding="utf-8")
    recipe = load_habit_recipe(ROOT / "recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)

    with pytest.raises(ValueError, match=r"MTEX parity failed: .*vertex_hausdorff"):
        compare_mtex_reference(solve_convex_habit(planes), perturbed)
```

- [ ] **Step 4: Implement parity without triangle-order assumptions**

```python
# src/kikuchi_lab/habit/parity.py
@dataclass(frozen=True)
class MTEXParityReport:
    passed: bool
    mtex_version: str
    python_vertex_count: int
    mtex_vertex_count: int
    python_face_count: int
    mtex_face_count: int
    visible_family_labels: tuple[str, ...]
    vertex_hausdorff: float
    relative_volume_difference: float
    maximum_face_normal_angle_rad: float
    tolerances: Mapping[str, float]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def compare_mtex_reference(
    polygon: LabeledPolygonMesh, ledger_path: str | Path
) -> MTEXParityReport:
    ledger = _load_and_validate_ledger(ledger_path)
    python_vertices = _unit_extent(polygon.vertices)
    mtex_vertices = _unit_extent(np.asarray(ledger["vertices"], dtype=float))
    vertex_hausdorff = max(
        directed_hausdorff(python_vertices, mtex_vertices)[0],
        directed_hausdorff(mtex_vertices, python_vertices)[0],
    )
    python_volume = _polygon_volume_with_vertices(polygon, python_vertices)
    mtex_volume = _ledger_polygon_volume(ledger, vertices=mtex_vertices)
    volume_difference = abs(python_volume - mtex_volume) / max(python_volume, mtex_volume)
    normal_angle, labels = _match_labeled_face_normals(polygon, ledger)
    failures = _parity_failures(
        polygon, ledger, labels, vertex_hausdorff, volume_difference, normal_angle
    )
    if failures:
        raise ValueError("MTEX parity failed: " + ", ".join(failures))
    return MTEXParityReport(
        passed=True,
        mtex_version=str(ledger["mtex"]["version"]),
        python_vertex_count=len(python_vertices),
        mtex_vertex_count=len(mtex_vertices),
        python_face_count=len(polygon.faces),
        mtex_face_count=len(ledger["faces"]),
        visible_family_labels=tuple(sorted(labels)),
        vertex_hausdorff=float(vertex_hausdorff),
        relative_volume_difference=float(volume_difference),
        maximum_face_normal_angle_rad=float(normal_angle),
        tolerances=dict(PARITY_TOLERANCES),
    )
```

Both sides must already use the explicit `X||a*, Z||c` frame. Match face normals within each label using `scipy.optimize.linear_sum_assignment(1 - clip(dot, -1, 1))`; do not use triangle order, vertex order, or a fitted free rotation to hide a frame error.
`_unit_extent` must center at the axis-aligned bounding-box midpoint and divide
by the greatest axis-aligned extent. Both volume calculations must triangulate
their own polygon cycles against those normalized vertices; never compare the
raw MTEX unit-diameter volume against the Python support-distance volume.

- [ ] **Step 5: Add optional parity output to workflow and CLI**

Add `mtex_reference: str | Path | None = None` to `build_habit`. When supplied, compare before publication, write `mtex-parity.json`, include it in the inventory, and return its path. Add `--mtex-reference` to `habit build`. A parity failure must abort the atomic bundle rather than publish a mesh with a failed reference report.

- [ ] **Step 6: Run parity, regenerate-reference, and complete regression gates**

Run: `uv run pytest tests/integration/test_mtex_habit_parity.py -q`

Expected: committed-ledger parity passes within all four reviewed contracts.

Add `mtex: requires MATLAB and MTEX 6.1.1` to `pytest.ini`, and add this marked regeneration test:

```python
@pytest.mark.mtex
def test_mtex_reference_regeneration_matches_committed_geometry(tmp_path: Path):
    mtex_root = os.environ.get("KIKUCHI_MTEX_ROOT")
    matlab_bin = os.environ.get("MATLAB_BIN")
    if not mtex_root or not matlab_bin:
        pytest.skip("KIKUCHI_MTEX_ROOT and MATLAB_BIN are required")
    generated = tmp_path / "quartz-mtex.json"
    command = (
        "addpath('scripts'); export_mtex_habit_reference("
        "'reference/habits/quartz-mtex-request.json',"
        f"'{generated.as_posix()}')"
    )
    subprocess.run(
        [matlab_bin, "-batch", command],
        cwd=ROOT,
        env={**os.environ, "KIKUCHI_MTEX_ROOT": mtex_root},
        check=True,
    )
    assert _scientific_geometry_fields(generated) == _scientific_geometry_fields(
        ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    )
```

Run:

```bash
KIKUCHI_MTEX_ROOT=/Users/Z/Documents/MATLAB/mtex-6.1.1 \
MATLAB_BIN=/Applications/MATLAB_R2025b.app/bin/matlab \
uv run pytest -m mtex tests/integration/test_mtex_habit_parity.py -q
```

Expected: regeneration succeeds and the temporary ledger is canonically equivalent to the committed scientific geometry fields.

Run: `uv run pytest -m "not gpu and not slow" -q`

Expected: complete fast suite passes.

Run: `uv run ruff check .`

Expected: no lint violations.

- [ ] **Step 7: Build the acceptance bundle and inspect it in the slicer**

```bash
uv run kikuchi-lab habit build \
  --recipe recipes/habits/quartz-mtex-example.yml \
  --mtex-reference reference/habits/quartz-mtex-6.1.1.json \
  --output local/habits/quartz-acceptance
```

Expected: the bundle adds `mtex-parity.json`; the STL is one watertight
`60.0 mm` solid. Open it in the FlashForge AD5X-oriented slicer workflow and
record orientation/support observations without editing the STL in the new
`docs/acceptance/crystal-habit-mesh.md`. Link the bundle ID, validation report,
parity report, and preview while explicitly stating that the original
exceptional-forsterite milestone is unchanged.

- [ ] **Step 8: Close tasks only against recorded evidence and commit**

Check each task's acceptance boxes only when its tests and artifacts exist. Mark `KIKU-F004` done only when every feature criterion is checked. Do not change the status or criteria of `KIKU-F001` through `KIKU-F003`.

```bash
uv run python scripts/validate_work_items.py
git add scripts/export_mtex_habit_reference.m reference/habits \
  src/kikuchi_lab/habit src/kikuchi_lab/cli/main.py pytest.ini \
  tests/integration/test_mtex_habit_parity.py docs/acceptance \
  docs/work/KIKU-F004.md docs/work/KIKU-T0{25,26,27,28,29,30}.md
git commit -m "feat: prove quartz habit mesh against MTEX"
```

Expected: tracker validation passes, final commit succeeds, and `git status --short` is empty.
