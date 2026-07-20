# Ice-Ih Tattoo Hemisphere Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the edge-clipped primary Ice-Ih tattoo with a provenance-bearing, fully visible 132 mm stereographic hemisphere boundary containing the unchanged 11 crystallographic paths.

**Architecture:** Add a separate immutable projection-boundary contract so the enclosing circle can never be mistaken for a reflector. The strict tattoo recipe owns the exact boundary policy; the geometry builder uniformly maps selected traces into its inner edge; SVG, PDF, PNG, diagnostic, and bundle layers render and ledger the same boundary after the 11 paths. The existing rimless retained bundle remains immutable audit evidence while a new deterministic run becomes the visual candidate.

**Tech Stack:** Python 3.12, NumPy, dataclasses, PyYAML, deterministic SVG serialization, Matplotlib PDF, Pillow PNG, pytest, Ruff, repo-native work tracking.

## Global Constraints

- Preserve the Ice-Ih catalog ID, active crystal-to-sample Bunge `(17, 31, 43)` orientation, selected member order, `4.0 degree` nonredundancy, and `4 / 4 / 3` path allocation.
- The artboard is exactly `145.0 mm` square.
- The boundary has exact outer diameter `132.0 mm`, width `2.2 mm`, center `(72.5, 72.5) mm`, black ink `#000000`, role `stereographic_hemisphere_boundary`, and claim `noncrystallographic_projection_primitive`.
- The 11 path widths remain `4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0, 0.8 mm` in order.
- The boundary is not a twelfth reflector: it is serialized separately and excluded from catalog/member/path counts and selection scoring.
- Path centerlines terminate at the boundary inner edge; all nonendpoint samples remain inside it; paths render first and the boundary renders last.
- The complete outer boundary remains on-page with `6.5 mm` clear margin on every side.
- Preserve the hard `1.5 mm` noncrossing edge-gap and `2.0 mm` unrelated-endpoint-clearance rules between crystallographic paths.
- Primary output remains black ink plus untouched skin/white only: no blur, fake shading, graticule, halo, node, doubled edge, detector rectangle, or graywash.
- PDF remains `145.0 mm` square; both PNGs remain `1713 x 1713` at `300 dpi`; all bytes remain deterministic and timestamp-free.
- Preflight must reject inconsistent boundary evidence before output mutation; publication remains atomic and no-replace.
- Do not delete, overwrite, edit, or relabel `local/ice-tattoo-primary-proof/ice-tattoo-run-d158193b08f3668e`.
- Do not touch the protected dirty MTEX, T023/T024, `pyproject.toml`, `pytest.ini`, spherical initializer, or spherical MTEX test files.

## File map

| File | Responsibility |
| --- | --- |
| `src/kikuchi_lab/art_products/contracts.py` | Immutable `TattooBoundary` evidence and geometry ownership |
| `src/kikuchi_lab/art_products/tattoo_recipe.py` | Exact tracked projection-boundary policy |
| `recipes/art/ice-ih-tattoo.yml` | Provenance-bearing 132/2.2 mm primary boundary choice |
| `src/kikuchi_lab/art_products/tattoo_vector.py` | Full-disc geometry, containment validation, SVG/PDF/PNG rendering |
| `src/kikuchi_lab/art_products/tattoo_bundle.py` | Boundary-aware preflight, diagnostic, run identity, and atomic publication |
| `tests/unit/test_art_product_contracts.py` | Boundary immutability and identity tests |
| `tests/unit/test_tattoo_recipe.py` | Strict recipe schema tests |
| `tests/unit/test_tattoo_vector.py` | Full-disc construction and containment tests |
| `tests/scientific/test_tattoo_clearance.py` | Unchanged path-to-path scientific clearance semantics |
| `tests/unit/test_tattoo_render.py` | Exact circle primitive, z-order, dimensions, and raster visibility |
| `tests/unit/test_tattoo_bundle.py` | Boundary-forgery and no-mutation publication tests |
| `tests/integration/test_ice_tattoo.py` | Bounded real-Ice selection/geometry proof |
| `docs/acceptance/ice-ih-tattoo-primary.md` | Supersession and retained candidate evidence |
| `docs/work/KIKU-T029.md` | Primary tattoo work-item state and acceptance gate |

---

### Task 1: Add the projection-boundary and recipe contracts

**Files:**
- Modify: `src/kikuchi_lab/art_products/contracts.py:254-359`
- Modify: `src/kikuchi_lab/art_products/__init__.py`
- Modify: `src/kikuchi_lab/art_products/tattoo_recipe.py:18-292`
- Modify: `recipes/art/ice-ih-tattoo.yml`
- Modify: `tests/unit/test_art_product_contracts.py:180-270`
- Modify: `tests/unit/test_tattoo_recipe.py:1-170`

**Interfaces:**
- Consumes: `stable_id(prefix: str, payload: object) -> str` and existing strict recipe helpers.
- Produces: `TattooBoundary`, `TattooBoundary.to_dict()`, `TattooBoundary.boundary_id`, and `TattooRecipe.projection_boundary`.

- [ ] **Step 1: Write failing boundary-contract tests**

Add tests that construct the wished-for contract and prove that its scientific classification and dimensions participate in identity:

```python
def _boundary(**changes: object) -> TattooBoundary:
    values = {
        "schema_version": 1,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "center_mm": (72.5, 72.5),
        "outer_diameter_mm": 132.0,
        "width_mm": 2.2,
        "ink": "#000000",
    }
    values.update(changes)
    return TattooBoundary(**values)


def test_projection_boundary_is_frozen_separate_evidence() -> None:
    boundary = _boundary()
    assert boundary.to_dict()["scientific_claim"] == (
        "noncrystallographic_projection_primitive"
    )
    assert boundary.to_dict()["center_mm"] == [72.5, 72.5]
    assert boundary.boundary_id.startswith("tattoo-boundary-")
    with pytest.raises(FrozenInstanceError):
        boundary.width_mm = 3.0


def test_projection_boundary_identity_includes_every_physical_field() -> None:
    original = _boundary()
    for field, value in (
        ("center_mm", [72.4, 72.5]),
        ("outer_diameter_mm", 131.9),
        ("width_mm", 2.1),
        ("scientific_claim", "forged-reflector"),
    ):
        changed = original.identity_dict()
        changed[field] = value
        assert stable_id("tattoo-boundary", changed) != original.boundary_id
```

- [ ] **Step 2: Run the contract tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_art_product_contracts.py -q
```

Expected: collection fails because `TattooBoundary` is not exported.

- [ ] **Step 3: Add failing strict-recipe tests**

Replace the fixture's `include_rim: false` with the exact mapping and test every fixed field:

```python
"projection_boundary": {
    "enabled": True,
    "role": "stereographic_hemisphere_boundary",
    "scientific_claim": "noncrystallographic_projection_primitive",
    "outer_diameter_mm": 132.0,
    "stroke_width_mm": 2.2,
    "ink": "#000000",
},
```

Assert:

```python
def test_tracked_recipe_has_exact_complete_hemisphere_boundary() -> None:
    recipe = load_tattoo_recipe(RECIPE)
    assert dict(recipe.projection_boundary) == {
        "enabled": True,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "outer_diameter_mm": 132.0,
        "stroke_width_mm": 2.2,
        "ink": "#000000",
    }
    assert "include_rim" not in recipe.to_dict()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("enabled", False),
        ("outer_diameter_mm", 131.9),
        ("stroke_width_mm", 2.1),
        ("role", "reflector"),
        ("scientific_claim", "crystallographic_reflector"),
        ("ink", "#111111"),
    ),
)
def test_recipe_rejects_nonapproved_boundary(field: str, value: object) -> None:
    payload = _payload()
    payload["projection_boundary"][field] = value
    with pytest.raises(ValueError, match="projection_boundary"):
        _load(payload)
```

- [ ] **Step 4: Run recipe tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_tattoo_recipe.py -q
```

Expected: failures report an unexpected `projection_boundary` field and missing `include_rim`.

- [ ] **Step 5: Implement the immutable boundary and exact recipe mapping**

Add the contract to `contracts.py` and export it:

```python
@dataclass(frozen=True, eq=False)
class TattooBoundary:
    schema_version: int
    role: str
    scientific_claim: str
    center_mm: tuple[float, float]
    outer_diameter_mm: float
    width_mm: float
    ink: str
    boundary_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_1(self.schema_version)
        if self.role != "stereographic_hemisphere_boundary":
            raise ValueError("boundary role must be stereographic_hemisphere_boundary")
        if self.scientific_claim != "noncrystallographic_projection_primitive":
            raise ValueError(
                "boundary scientific_claim must be "
                "noncrystallographic_projection_primitive"
            )
        center = tuple(float(value) for value in self.center_mm)
        if center != (72.5, 72.5):
            raise ValueError("boundary center_mm must be exactly (72.5, 72.5)")
        outer = _require_positive_finite(
            self.outer_diameter_mm, "outer_diameter_mm"
        )
        width = _require_positive_finite(self.width_mm, "width_mm")
        if outer != 132.0 or width != 2.2:
            raise ValueError("boundary dimensions must be exactly 132.0 and 2.2 mm")
        if self.ink != "#000000":
            raise ValueError("boundary ink must be #000000")
        object.__setattr__(self, "center_mm", center)
        object.__setattr__(self, "outer_diameter_mm", outer)
        object.__setattr__(self, "width_mm", width)
        object.__setattr__(
            self, "boundary_id", stable_id("tattoo-boundary", self.identity_dict())
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "scientific_claim": self.scientific_claim,
            "center_mm": list(self.center_mm),
            "outer_diameter_mm": self.outer_diameter_mm,
            "width_mm": self.width_mm,
            "ink": self.ink,
        }

    def to_dict(self) -> dict[str, object]:
        return {"boundary_id": self.boundary_id, **self.identity_dict()}
```

In `tattoo_recipe.py`, replace `include_rim` with `projection_boundary`, validate it against this exact constant, and serialize a copied immutable mapping:

```python
_BOUNDARY_POLICY = {
    "enabled": True,
    "role": "stereographic_hemisphere_boundary",
    "scientific_claim": "noncrystallographic_projection_primitive",
    "outer_diameter_mm": 132.0,
    "stroke_width_mm": 2.2,
    "ink": "#000000",
}


def _exact_boundary_policy(value: object) -> MappingProxyType[str, object]:
    source = _mapping(value, set(_BOUNDARY_POLICY), "projection_boundary")
    if dict(source) != _BOUNDARY_POLICY:
        raise ValueError("tattoo recipe projection_boundary must match approved policy")
    return MappingProxyType(dict(_BOUNDARY_POLICY))
```

Make the tracked YAML use the same six fields exactly.

- [ ] **Step 6: Verify Task 1 GREEN**

Run:

```bash
uv run pytest tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_recipe.py tests/scientific/test_tattoo_selection.py -q
uv run ruff check src/kikuchi_lab/art_products/contracts.py src/kikuchi_lab/art_products/__init__.py src/kikuchi_lab/art_products/tattoo_recipe.py tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_recipe.py
git diff --check -- src/kikuchi_lab/art_products recipes/art tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_recipe.py
```

Expected: all focused tests pass, Ruff reports `All checks passed!`, and `git diff --check` exits zero.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/kikuchi_lab/art_products/contracts.py src/kikuchi_lab/art_products/__init__.py src/kikuchi_lab/art_products/tattoo_recipe.py recipes/art/ice-ih-tattoo.yml tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_recipe.py
git commit -m "feat: define Ice tattoo hemisphere boundary"
```

---

### Task 2: Build and validate the bounded vector geometry

**Files:**
- Modify: `src/kikuchi_lab/art_products/contracts.py:305-352`
- Modify: `src/kikuchi_lab/art_products/tattoo_vector.py:352-518`
- Modify: `tests/unit/test_art_product_contracts.py:222-270`
- Modify: `tests/unit/test_tattoo_vector.py`
- Modify: `tests/scientific/test_tattoo_clearance.py`
- Modify: `tests/unit/test_tattoo_render.py:25-48`
- Modify: `tests/unit/test_tattoo_bundle.py:90-110,285-310`

**Interfaces:**
- Consumes: `TattooBoundary`, `TattooRecipe.projection_boundary`, and `TattooSelection.selected_paths`.
- Produces: `TattooGeometry.boundary`, `build_tattoo_geometry(...) -> TattooGeometry`, and boundary-aware `validate_tattoo_geometry(...)` / `primary_svg_bytes(...)`.

- [ ] **Step 1: Write failing geometry tests before changing production geometry**

Add exact full-disc assertions to `test_tattoo_vector.py`:

```python
def test_geometry_contains_complete_boundary_and_unchanged_path_hierarchy() -> None:
    selection = _selection()
    geometry = vector.build_tattoo_geometry(selection, load_tattoo_recipe(RECIPE))

    assert geometry.boundary.to_dict() == {
        "boundary_id": geometry.boundary.boundary_id,
        "schema_version": 1,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "center_mm": [72.5, 72.5],
        "outer_diameter_mm": 132.0,
        "width_mm": 2.2,
        "ink": "#000000",
    }
    assert len(geometry.paths) == 11
    assert [path.member_id for path in geometry.paths] == [
        path.member_id for path in selection.selected_paths
    ]
    assert [path.tier for path in geometry.paths] == [
        "dominant", "dominant", "dominant", "dominant",
        "secondary", "secondary", "secondary", "secondary",
        "fine", "fine", "fine",
    ]


def test_every_trace_is_contained_and_terminates_on_inner_limb() -> None:
    geometry = vector.build_tattoo_geometry(_selection(), load_tattoo_recipe(RECIPE))
    center = np.asarray(geometry.boundary.center_mm)
    inner_radius = (
        geometry.boundary.outer_diameter_mm / 2.0
        - geometry.boundary.width_mm
    )
    for path in geometry.paths:
        radii = np.linalg.norm(path.points_mm - center, axis=1)
        assert radii[0] == pytest.approx(inner_radius, abs=1e-8)
        assert radii[-1] == pytest.approx(inner_radius, abs=1e-8)
        assert np.all(radii <= inner_radius + 1e-8)
```

Add a geometry-identity assertion to `test_art_product_contracts.py`:

```python
def test_geometry_identity_includes_separate_projection_boundary() -> None:
    boundary = _boundary()
    original = _geometry(_path(), boundary=boundary)
    original_id = boundary.boundary_id
    object.__setattr__(boundary, "boundary_id", "tattoo-boundary-forged")
    try:
        changed = replace(original, boundary=boundary)
        assert changed.geometry_id != original.geometry_id
        assert len(changed.paths) == 1
    finally:
        object.__setattr__(boundary, "boundary_id", original_id)
```

- [ ] **Step 2: Run focused geometry tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_vector.py -q
```

Expected: failures report that `TattooGeometry` has no `boundary` and the builder returns edge-to-edge coordinates.

- [ ] **Step 3: Add the boundary to `TattooGeometry` and build exact contained paths**

Add `boundary: TattooBoundary` before `paths`, require its type, and include `"boundary": self.boundary.to_dict()` in `TattooGeometry.to_dict()`.

Replace the physical scaling block in `build_tattoo_geometry` with:

```python
policy = recipe.projection_boundary
boundary = TattooBoundary(
    schema_version=1,
    role=str(policy["role"]),
    scientific_claim=str(policy["scientific_claim"]),
    center_mm=(recipe.artboard_size_mm / 2.0,) * 2,
    outer_diameter_mm=float(policy["outer_diameter_mm"]),
    width_mm=float(policy["stroke_width_mm"]),
    ink=str(policy["ink"]),
)
inner_radius_mm = boundary.outer_diameter_mm / 2.0 - boundary.width_mm
scale = inner_radius_mm / recipe.crop_radius
center = np.asarray(boundary.center_mm, dtype=_ARRAY_DTYPE)
```

Continue clipping at normalized `recipe.crop_radius`, then apply this uniform scale. Pass `boundary=boundary` to `TattooGeometry`.

Extend `validate_tattoo_geometry` with exact containment checks:

```python
if not isinstance(geometry.boundary, TattooBoundary):
    raise ValueError("primary tattoo geometry requires one projection boundary")
outer_radius = geometry.boundary.outer_diameter_mm / 2.0
inner_radius = outer_radius - geometry.boundary.width_mm
center = np.asarray(geometry.boundary.center_mm, dtype=_ARRAY_DTYPE)
if outer_radius + center[0] != 138.5 or center[0] - outer_radius != 6.5:
    raise ValueError("projection boundary must retain an exact 6.5 mm page margin")
for path in geometry.paths:
    radii = np.linalg.norm(path.points_mm - center, axis=1)
    if not np.all(radii <= inner_radius + 1e-8):
        raise ValueError("crystallographic path escapes the boundary inner edge")
    if not np.allclose(radii[[0, -1]], inner_radius, rtol=0.0, atol=1e-8):
        raise ValueError("crystallographic path endpoints must meet the inner limb")
```

Update every test-only `TattooGeometry(...)` fixture in the listed files to pass `_boundary()` or the builder-produced boundary. Do not relax strict production validation for fixture convenience.

- [ ] **Step 4: Verify geometry GREEN and unchanged clearances**

Run:

```bash
uv run pytest tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py -q
```

Expected: all pass; the 1.49 mm and 1.99 mm negative clearance cases remain red-to-green regressions under the unchanged 1.5/2.0 mm thresholds.

- [ ] **Step 5: Write a failing SVG structure test**

Add to `test_tattoo_render.py`:

```python
def test_primary_svg_has_11_paths_then_one_complete_projection_boundary() -> None:
    geometry = _geometry()
    root = ElementTree.fromstring(primary_svg_bytes(geometry))
    children = list(root)
    assert [child.tag.rsplit("}", 1)[-1] for child in children] == [
        *("path" for _ in range(11)),
        "circle",
    ]
    circle = children[-1]
    assert circle.attrib == {
        "cx": "72.500000",
        "cy": "72.500000",
        "fill": "none",
        "id": geometry.boundary.boundary_id,
        "r": "64.900000",
        "stroke": "#000000",
        "stroke-width": "2.200000",
    }
```

- [ ] **Step 6: Run the SVG test and verify RED**

Run:

```bash
uv run pytest tests/unit/test_tattoo_render.py::test_primary_svg_has_11_paths_then_one_complete_projection_boundary -q
```

Expected: the child list contains only 11 paths.

- [ ] **Step 7: Serialize the boundary last**

After the existing path loop in `primary_svg_bytes`, append:

```python
center_x, center_y = geometry.boundary.center_mm
centerline_radius = (
    geometry.boundary.outer_diameter_mm - geometry.boundary.width_mm
) / 2.0
lines.append(
    f'  <circle cx="{center_x:.6f}" cy="{center_y:.6f}" fill="none" '
    f'id="{geometry.boundary.boundary_id}" r="{centerline_radius:.6f}" '
    f'stroke="{geometry.boundary.ink}" '
    f'stroke-width="{geometry.boundary.width_mm:.6f}"/>'
)
```

- [ ] **Step 8: Verify Task 2 GREEN**

Run:

```bash
uv run pytest tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_recipe.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py tests/unit/test_tattoo_render.py::test_primary_svg_has_11_paths_then_one_complete_projection_boundary -q
uv run ruff check src/kikuchi_lab/art_products/contracts.py src/kikuchi_lab/art_products/tattoo_vector.py tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py tests/unit/test_tattoo_render.py
git diff --check -- src/kikuchi_lab/art_products tests/unit tests/scientific/test_tattoo_clearance.py
```

Expected: all focused tests pass and static checks are clean.

- [ ] **Step 9: Commit Task 2**

```bash
git add src/kikuchi_lab/art_products/contracts.py src/kikuchi_lab/art_products/tattoo_vector.py tests/unit/test_art_product_contracts.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py
git commit -m "feat: bound Ice tattoo paths within hemisphere"
```

---

### Task 3: Render and publish the complete boundary deterministically

**Files:**
- Modify: `src/kikuchi_lab/art_products/tattoo_vector.py:521-596`
- Modify: `src/kikuchi_lab/art_products/tattoo_bundle.py:130-403`
- Modify: `tests/unit/test_tattoo_render.py:61-137`
- Modify: `tests/unit/test_tattoo_bundle.py`

**Interfaces:**
- Consumes: validated `TattooGeometry.boundary` and canonical `primary_svg_bytes(...)`.
- Produces: boundary-identical PDF/PNG bytes, boundary-aware diagnostic/run identity, and strict preflight.

- [ ] **Step 1: Write failing raster and PDF visibility tests**

Add a helper that converts millimeters to pixels and assert the entire limb is visible against both backgrounds:

```python
def _px(mm: float) -> int:
    return round(mm * 1713 / 145.0)


@pytest.mark.parametrize(
    ("name", "background"),
    (("mockup.png", (216, 181, 154)), ("stencil.png", (255, 255, 255))),
)
def test_primary_png_shows_complete_132_mm_boundary_with_clear_margin(
    name: str, background: tuple[int, int, int]
) -> None:
    payload = render_primary_tattoo(_geometry())[name]
    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
        center = _px(72.5)
        assert image.getpixel((center, _px(6.5))) == (0, 0, 0)
        assert image.getpixel((center, _px(5.0))) == background
        assert image.getpixel((center, _px(138.5))) == (0, 0, 0)
        assert image.getpixel((_px(5.0), center)) == background
        assert image.getpixel((_px(140.0), center)) == background
```

Retain the existing PDF MediaBox and stable-metadata assertions; canonical
render-byte reconstruction in the bundle test provides the PDF geometry parity
gate without parsing Matplotlib's internal drawing stream.

- [ ] **Step 2: Run render tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_tattoo_render.py -q
```

Expected: SVG structure passes from Task 2, while the PDF/PNG boundary visibility assertions fail.

- [ ] **Step 3: Draw the same boundary after paths in PDF and PNG**

Import `Circle` from `matplotlib.patches`. After adding all `Line2D` paths, add:

```python
axis.add_patch(
    Circle(
        geometry.boundary.center_mm,
        radius=(
            geometry.boundary.outer_diameter_mm - geometry.boundary.width_mm
        ) / 2.0,
        fill=False,
        edgecolor=geometry.boundary.ink,
        linewidth=(
            geometry.boundary.width_mm
            * _POINTS_PER_INCH
            / _MILLIMETERS_PER_INCH
        ),
    )
)
```

After all Pillow path drawing, draw the boundary last with the exact outer-edge
bounding box `(center - 66.0 mm, center + 66.0 mm)` and
`width_px = round(2.2 * scale)`. Pillow draws the outline inward, so this keeps
the outside at 132.0 mm and the inside at the same 63.8 mm radius used for path
endpoint contact. Use `ImageDraw.ellipse(..., outline="#000000",
width=width_px)` and no antialiasing or post-filter.

- [ ] **Step 4: Verify render GREEN and determinism**

Run:

```bash
uv run pytest tests/unit/test_tattoo_render.py -q
```

Expected: all render tests pass twice with byte-identical SVG/PDF/PNG hashes, exact page/DPI metadata, and only black plus the required background.

- [ ] **Step 5: Write failing bundle preflight tests**

Add tests proving boundary provenance is in the snapshots and forged boundary evidence fails before output creation:

```python
def test_bundle_ledgers_projection_boundary_separately(bundle_inputs, tmp_path) -> None:
    result = write_tattoo_bundle(tmp_path, **bundle_inputs)
    geometry = json.loads((result.path / "path-geometry.json").read_text())
    diagnostic = json.loads(
        (result.path / "stroke-gap-diagnostic.json").read_text()
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    boundary = geometry["content"]["boundary"]
    assert boundary["scientific_claim"] == (
        "noncrystallographic_projection_primitive"
    )
    assert len(geometry["content"]["paths"]) == 11
    assert diagnostic["boundary_id"] == boundary["boundary_id"]
    assert diagnostic["validation"]["complete_hemisphere_boundary"] == "passed"
    assert manifest["run_identity"]["boundary_id"] == boundary["boundary_id"]


def test_forged_boundary_fails_before_output_mutation(bundle_inputs, tmp_path) -> None:
    geometry = bundle_inputs["geometry"]
    object.__setattr__(geometry.boundary, "boundary_id", "tattoo-boundary-forged")
    output = tmp_path / "forged-boundary"
    try:
        with pytest.raises(ValueError, match="boundary_id"):
            write_tattoo_bundle(output, **bundle_inputs)
    finally:
        object.__setattr__(
            geometry.boundary,
            "boundary_id",
            stable_id("tattoo-boundary", geometry.boundary.identity_dict()),
        )
    assert not output.exists()
```

Extend the SVG validator test to require exactly 11 path elements followed by exactly one circle and reject a circle placed first, a second circle, a nonblack circle, or a missing boundary.

- [ ] **Step 6: Run bundle tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_tattoo_bundle.py -q
```

Expected: missing `boundary_id` / `complete_hemisphere_boundary` ledger fields and the old SVG validator rejects or ignores the circle incorrectly.

- [ ] **Step 7: Make bundle validation and ledgers boundary-aware**

In `_validate_svg`, require root children in the exact order of 11 paths plus one circle; validate black ink, no fill, exact boundary ID, and no other primitives.

In `_validated_payload`, verify:

```python
if geometry.boundary.boundary_id != stable_id(
    "tattoo-boundary", geometry.boundary.identity_dict()
):
    raise ValueError("boundary_id does not match boundary content")
if geometry.boundary.to_dict() != expected_geometry.boundary.to_dict():
    raise ValueError("projection boundary does not match rebuilt geometry")
```

Add these exact ledger fields:

```python
diagnostic["boundary_id"] = geometry.boundary.boundary_id
diagnostic["boundary"] = geometry.boundary.to_dict()
diagnostic["validation"]["complete_hemisphere_boundary"] = "passed"
diagnostic["validation"]["boundary_endpoint_contact"] = "passed"
run_identity["boundary_id"] = geometry.boundary.boundary_id
```

Keep `band-selection-ledger.json` unchanged apart from the new recipe ID already implied by Task 1. It must not list the boundary among `selected_paths`.

- [ ] **Step 8: Verify Task 3 GREEN and relevant regressions**

Run:

```bash
uv run pytest tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py tests/unit/test_tattoo_vector.py tests/scientific/test_tattoo_clearance.py -q
uv run ruff check src/kikuchi_lab/art_products/tattoo_vector.py src/kikuchi_lab/art_products/tattoo_bundle.py tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py
git diff --check -- src/kikuchi_lab/art_products tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py
```

Expected: all focused tests pass and static checks are clean.

- [ ] **Step 9: Commit Task 3**

```bash
git add src/kikuchi_lab/art_products/tattoo_vector.py src/kikuchi_lab/art_products/tattoo_bundle.py tests/unit/test_tattoo_render.py tests/unit/test_tattoo_bundle.py
git commit -m "feat: render complete Ice tattoo hemisphere"
```

---

### Task 4: Publish and verify the new retained real-Ice candidate

**Files:**
- Modify: `tests/integration/test_ice_tattoo.py`
- Modify: `docs/acceptance/ice-ih-tattoo-primary.md`
- Modify: `docs/work/KIKU-T029.md`

**Interfaces:**
- Consumes: retained catalog `art-band-catalog-05f58424b717d5ad` and `render_ice_tattoo(...)`.
- Produces: one new no-replace local bundle, exact acceptance evidence, and an active visual-review gate.

- [ ] **Step 1: Strengthen the real-Ice integration gate before publication**

Require the known selected-member order to remain unchanged:

```python
EXPECTED_MEMBERS = (
    "art-band-member-239b7cb5e485d442",
    "art-band-member-d38532aafcf1ed7f",
    "art-band-member-3cb4167967631dcc",
    "art-band-member-0a414c19f6ab8845",
    "art-band-member-b4647bcd2cbca9f6",
    "art-band-member-b67c65e3bc542c16",
    "art-band-member-263af8004ec3e279",
    "art-band-member-ef3609aba836233b",
    "art-band-member-4fdb2612d72a02c1",
    "art-band-member-2413565c4ba2c58d",
    "art-band-member-c38e4b2859f9646d",
)
```

After loading the published geometry and selection ledger, assert:

```python
assert tuple(path["member_id"] for path in selection["selected_paths"]) == (
    EXPECTED_MEMBERS
)
assert len(geometry["content"]["paths"]) == 11
assert geometry["content"]["boundary"]["outer_diameter_mm"] == 132.0
assert geometry["content"]["boundary"]["width_mm"] == 2.2
assert diagnostic["validation"]["complete_hemisphere_boundary"] == "passed"
```

- [ ] **Step 2: Run the bounded real-Ice integration and full verification**

Run:

```bash
uv run pytest tests/integration/test_ice_tattoo.py -q
uv run pytest -q
uv run ruff check .
uv run python scripts/validate_work_items.py
git diff --check
```

Expected: the focused and full suites pass; one existing expected skip remains; Ruff and tracker validation are clean.

- [ ] **Step 3: Publish exactly one retained candidate beside the audit bundle**

Confirm the catalog bundle exists and run once:

```bash
test -f local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json
uv run kikuchi-lab render-ice-tattoo \
  --catalog local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json \
  --recipe recipes/art/ice-ih-tattoo.yml \
  --output local/ice-tattoo-primary-proof \
  --treatment primary
```

Expected: a new `ice-tattoo-run-*` child appears; the existing `ice-tattoo-run-d158193b08f3668e` directory remains byte-for-byte untouched.

- [ ] **Step 4: Inspect and record retained evidence**

Open the new mockup and stencil at original resolution. Verify with JSON/SVG probes:

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from xml.etree import ElementTree

root = Path("local/ice-tattoo-primary-proof")
old = "ice-tattoo-run-d158193b08f3668e"
candidates = [
    path for path in root.glob("ice-tattoo-run-*")
    if path.is_dir() and path.name != old
]
assert len(candidates) == 1
candidate = candidates[0]
geometry = json.loads((candidate / "path-geometry.json").read_text())
svg = ElementTree.parse(candidate / "ice-ih-tattoo-primary.svg").getroot()
children = list(svg)
assert len(geometry["content"]["paths"]) == 11
assert geometry["content"]["boundary"]["outer_diameter_mm"] == 132.0
assert [child.tag.rsplit("}", 1)[-1] for child in children] == [
    *("path" for _ in range(11)), "circle"
]
print(candidate)
PY
```

Record the exact new run ID, recipe ID, unchanged catalog/orientation/member IDs, new geometry/boundary IDs, manifest SHA-256, dimensions, artifact hashes, commands, tests, and local paths in `docs/acceptance/ice-ih-tattoo-primary.md`. Label the rimless run as superseded audit evidence rather than deleting its table.

Update `docs/work/KIKU-T029.md` to link the boundary spec and this plan, replace “open silhouette” with “complete stereographic hemisphere boundary,” add checked machine criteria for the separate noncrystallographic boundary and full-disc outputs, and leave the user visual-acceptance checkbox unchecked with `status: active`.

- [ ] **Step 5: Commit Task 4 evidence**

```bash
git add tests/integration/test_ice_tattoo.py docs/acceptance/ice-ih-tattoo-primary.md docs/work/KIKU-T029.md
git commit -m "feat: publish bounded Ice tattoo proof"
```

---

### Task 5: Human visual acceptance gate

**Files:**
- Modify after explicit acceptance: `docs/acceptance/ice-ih-tattoo-primary.md`
- Modify after explicit acceptance: `docs/work/KIKU-T029.md`

**Interfaces:**
- Consumes: the new retained bounded run ID, geometry ID, boundary ID, manifest SHA-256, mockup, stencil, SVG, and PDF.
- Produces: an auditable acceptance record; only then may KIKU-T031 graywash work begin.

- [ ] **Step 1: Present the complete candidate**

Show the full native-resolution mockup and stencil plus links to SVG/PDF. State explicitly that the circle is a noncrystallographic stereographic boundary and the 11 interior paths retain the approved Ice-Ih member order.

Ask the user to assess the entire visible circle, sphere-like reading, 2.2 mm limb weight, band-to-boundary contacts, ribbon hierarchy, and dense crossing hubs.

- [ ] **Step 2: Stop for explicit visual acceptance**

Do not infer acceptance from the design-spec approval. Continue only after the user explicitly accepts the regenerated bounded images.

- [ ] **Step 3: Record acceptance and close KIKU-T029**

Append the exact user acceptance quote, date, run ID, geometry ID, boundary ID, and manifest SHA-256 to `docs/acceptance/ice-ih-tattoo-primary.md`. Change `presentation_status` to `accepted`. Check the final acceptance criterion and set `status: done` in `docs/work/KIKU-T029.md`.

- [ ] **Step 4: Commit only the acceptance record**

```bash
git add docs/acceptance/ice-ih-tattoo-primary.md docs/work/KIKU-T029.md
git commit -m "docs: accept bounded Ice tattoo geometry"
```

Do not start graywash in this task. Resume the relief-globe plan or start the separately tracked KIKU-T031 implementation only after this acceptance commit.

## Final verification checklist

- [ ] `TattooBoundary` is frozen, deterministic, separate from the 11 `TattooPath` records, and explicitly noncrystallographic.
- [ ] The tracked recipe owns exact 132.0/2.2 mm boundary policy and contains no legacy rimless flag.
- [ ] The catalog, orientation, selected member order, 4-degree rule, 4/4/3 tiers, and path widths are unchanged.
- [ ] Every path endpoint meets the inner limb and no path or stroke escapes the 132 mm outer boundary.
- [ ] SVG child order is exactly 11 paths then one circle; PDF/PNG draw the same boundary last.
- [ ] The entire boundary is visible with 6.5 mm page margin in SVG/PDF/mockup/stencil.
- [ ] No blur, shading, graticule, nodes, halo, doubled edges, detector rectangle, or graywash appears.
- [ ] Bundle preflight rejects missing, forged, reordered, or inconsistent boundary evidence before mutation.
- [ ] The old rimless retained bundle remains untouched and a new deterministic bundle is recorded.
- [ ] Focused tests, full suite, Ruff, tracker validation, and `git diff --check` pass.
- [ ] KIKU-T029 remains active until the regenerated images receive explicit human acceptance.
