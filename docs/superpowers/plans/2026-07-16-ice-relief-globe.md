# Ice Ih Relief Globe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the accepted shared Ice Ih band catalog into deterministic reference and fine watertight relief spheres with five readable radial tiers, a 7 mm capped relief span, binary STL fabrication files, and a rotatable GLB inspection model.

**Architecture:** This plan consumes the `ArtBandCatalog` contract from the companion plan and never reads a rendered image. A strict globe recipe maps catalog cohorts onto a canonical crystal-frame sphere, applies a pointwise geometric shoulder only at band boundaries, and assigns the maximum occupied tier. A topology module creates welded latitude rings and pole fans; a mesh module applies the radial field. Independent validation and standard-library serializers publish STL/GLB plus fixed diagnostic views atomically.

**Tech Stack:** Python 3.12, NumPy, Matplotlib, Pillow, standard-library `struct` and `json` for binary STL/GLB 2.0, pytest, Ruff, repo-native tracker and bundle helpers.

## Global Constraints

- This plan starts only after Task 3 of `2026-07-16-ice-art-catalog-and-tattoo.md` publishes `ArtBandCatalog` and one real Ice catalog bundle.
- Work in `/Users/Z/Documents/kikuchi/.worktrees/spherical-intensity` on `codex/spherical-intensity-implementation`.
- Preserve all protected pre-existing dirty MTEX/T023 files. Do not edit or stage `pyproject.toml`, `pytest.ini`, `src/kikuchi_lab/spherical_intensity/__init__.py`, or existing untracked MTEX work.
- Use test-driven development and commit each independently green increment.
- The geometry is canonical crystal-frame. Viewer pose metadata cannot change field or mesh identity.
- Coordinates are millimeters. Radii are exactly `[68.00, 69.75, 71.50, 73.25, 75.00]` mm; maximum diameter is 150 mm.
- Intersections use maximum tier, never addition. All final radii stay in `[68,75]` mm.
- Default shoulder is 1.5 mm geodesic distance on the 75 mm sphere; allowed recipe range is `[0.8,2.0]`. No blur, convolution, Gaussian, resampled texture, or fine grayscale displacement.
- The first sphere has no flat, hole, opening, pedestal, integrated stand, cradle, or support.
- Required topologies: `170 x 170` -> 28,902 vertices/57,800 triangles; `340 x 340` -> 115,602 vertices/231,200 triangles.
- Binary STL is the fabrication output; GLB 2.0 is a rotatable fine-mesh inspection derivative. Add no mesh dependency.
- Large stages log a finite work summary, stage start/finish, elapsed time, and candidate-pair counts. Fine validation checks a monotonic deadline every 4,096 AABB candidate pairs so a stalled or runaway scan fails visibly instead of appearing locked up.
- Complete hard validation before output-root mutation; use unique partial, fsync, manifest-last, atomic no-replace publication.

## File Responsibility Map

| File | Responsibility |
| --- | --- |
| `art_products/globe_recipe.py` | Strict dimensions, tiers, topology profiles |
| `art_products/globe_field.py` | Band support, max tier, shoulder radii |
| `art_products/sphere_mesh.py` | Welded topology and radial displacement |
| `art_products/mesh_validation.py` | Manifold, winding, scale, connectivity, intersections |
| `art_products/mesh_io.py` | Deterministic binary STL and GLB 2.0 |
| `art_products/globe_render.py` | Fixed grayscale and tier diagnostics |
| `art_products/globe_bundle.py` | Preflight and atomic publication |
| `workflows/ice_globe.py` | Catalog-consuming reference/fine workflow |
| `cli/main.py` | `render-ice-relief-globe` |

---

## Task 1: Lock the globe recipe and radial field

**Files:**

- Create: `src/kikuchi_lab/art_products/globe_recipe.py`
- Create: `src/kikuchi_lab/art_products/globe_field.py`
- Create: `recipes/art/ice-ih-relief-globe.yml`
- Test: `tests/unit/test_globe_recipe.py`
- Test: `tests/scientific/test_globe_field.py`

- [ ] **Step 1: Write RED recipe tests**

Require schema 1, canonical crystal frame, mm units, 150 mm diameter, 68 mm background, offsets `[0,1.75,3.5,5.25,7]`, 1.5 mm shoulder, max overlap, no spatial filter, exact reference/fine profile counts, and every flat/opening/pedestal/cradle flag false. Reject changed diameter, uneven tiers, shoulder outside `[0.8,2.0]`, cohort count other than four, additive overlap, noncanonical frame, or enabled feature.

- [ ] **Step 2: Write RED field tests**

Use synthetic orthogonal bands with cohorts 1-4. Assert background and four exact tier radii, overlap at 75 mm, two cohort-4 overlaps still at 75 mm, antipodal equality, all five occupied, and nonunit input rejection. Check shoulder inside edge, midpoint, outside edge against the stated smoothstep formula.

- [ ] **Step 3: Run RED**

```bash
uv run pytest tests/unit/test_globe_recipe.py tests/scientific/test_globe_field.py -q
```

- [ ] **Step 4: Implement recipe and field contracts**

Create frozen `GlobeProfile`, `GlobeRecipe`, and `GlobeReliefField`. Public `evaluate_globe_relief(catalog, directions, recipe)` validates unit directions and four nonempty eligible cohorts.

For each band, compute signed outer distance:

```text
d_mm = 75 * (asin(abs(dot(direction, normal))) - theta_radian)
```

Inside the band, use the cohort radius. For `0 < d_mm < shoulder_width_mm`, interpolate from the next-lower radius to cohort radius with `u = 1-d_mm/shoulder_width_mm` and `u*u*(3-2*u)`. This pointwise formula is geometric, not filtering. Take maximum candidate radius; for tied diagnostics choose lexicographically smallest member ID. Store continuous radius separately from the strongest fully occupied discrete tier.

The tracked YAML contains exactly the approved dimensions, profiles, policies, and absent features; its relative catalog recipe is `ice-ih-band-catalog.yml`.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/test_globe_recipe.py tests/scientific/test_globe_field.py -q
uv run ruff check src/kikuchi_lab/art_products/globe_recipe.py src/kikuchi_lab/art_products/globe_field.py
git add src/kikuchi_lab/art_products/globe_recipe.py src/kikuchi_lab/art_products/globe_field.py recipes/art/ice-ih-relief-globe.yml tests/unit/test_globe_recipe.py tests/scientific/test_globe_field.py
git commit -m "feat: map Ice art bands to globe relief"
```

---

## Task 2: Generate exact welded sphere topologies

**Files:**

- Create: `src/kikuchi_lab/art_products/sphere_mesh.py`
- Test: `tests/unit/test_sphere_topology.py`
- Test: `tests/scientific/test_sphere_topology.py`

- [ ] **Step 1: Write RED topology tests**

For both profiles assert exact vertex/triangle counts. Require one north and south pole, no duplicate seam vertices, unit norms within `5e-13`, every undirected edge incidence exactly two, no duplicate face triples, positive outward face orientation, one component, and Euler characteristic two.

Also test a small `8 x 6` topology to make face ownership legible and prove every longitude wraps to zero without a duplicated longitude endpoint.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_sphere_topology.py tests/scientific/test_sphere_topology.py -q
```

- [ ] **Step 3: Implement topology and displacement**

Create frozen `SphereTopology` with directions/faces and `TriangleMesh` with vertices/faces/topology/field identity plus derived `mesh_id`. Vertex order is north pole; interior rings north-to-south with longitudes zero through `count-1`; south pole. Ring colatitude is `pi*(ring+1)/(interior_count+1)`. Face order is north fan, two outward triangles per ring quad, south fan. Flip a constructed face once if its normal points inward.

`displace_sphere(topology, field)` requires exact direction byte equality and returns `directions * radius[:,None]`. Mesh identity includes fixed little-endian vertex/face hashes, topology name, and field ID.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_sphere_topology.py tests/scientific/test_sphere_topology.py -q
uv run ruff check src/kikuchi_lab/art_products/sphere_mesh.py
git add src/kikuchi_lab/art_products/sphere_mesh.py tests/unit/test_sphere_topology.py tests/scientific/test_sphere_topology.py
git commit -m "feat: build welded relief sphere topology"
```

---

## Task 3: Validate closed geometry and self-intersections

**Files:**

- Create: `src/kikuchi_lab/art_products/mesh_validation.py`
- Test: `tests/unit/test_mesh_validation.py`
- Test: `tests/scientific/test_mesh_intersections.py`

- [ ] **Step 1: Write RED corruption tests**

From a valid small sphere separately remove a face, reverse a face, duplicate a face, create zero area, append a disconnected tetrahedron, move a vertex above 75 or below 68 mm, and construct two intersecting nonadjacent faces. Each case returns a specific hard-failure code. A valid reference report has one component, zero boundary/nonmanifold/duplicate/degenerate/reversed/intersection counts, all five tiers, and 68-75 mm bounds.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_mesh_validation.py tests/scientific/test_mesh_intersections.py -q
```

- [ ] **Step 3: Implement hard validation**

Create `MeshValidationReport` with topology counts, edge counts, components, orientation/degeneracy/duplicate/intersection counts, radius/diameter extrema, tier occupancy, warnings, and hard failures.

Validation order:

1. finite dtypes, shapes, and face index range;
2. sorted undirected-edge incidence;
3. face connectivity through shared edges;
4. duplicate sorted face triples;
5. float64 area and outward-dot winding;
6. exact expected topology counts and radial/field provenance;
7. radius bounds, 150 mm antipodal diameter, and five-tier occupancy;
8. self-intersections via deterministic median-split triangle AABB tree, followed by float64 Moller triangle tests. Exclude faces sharing a vertex and deduplicate ordered face pairs.

Run the AABB scan on reference mesh in the ordinary suite and on fine mesh during the real acceptance run. The scanner accepts `check_deadline: Callable[[], None]`, increments visited-node/candidate-pair/exact-pair counters monotonically, and calls the deadline every 4,096 candidate pairs. Field provenance is mandatory but does not replace intersection testing.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_mesh_validation.py tests/scientific/test_mesh_intersections.py -q
uv run ruff check src/kikuchi_lab/art_products/mesh_validation.py
git add src/kikuchi_lab/art_products/mesh_validation.py tests/unit/test_mesh_validation.py tests/scientific/test_mesh_intersections.py
git commit -m "feat: validate closed Ice relief meshes"
```

---

## Task 4: Serialize deterministic STL and GLB

**Files:**

- Create: `src/kikuchi_lab/art_products/mesh_io.py`
- Test: `tests/unit/test_mesh_io.py`

- [ ] **Step 1: Write RED byte tests**

For tetrahedron and small sphere, binary STL length is `84 + 50*face_count`; header is fixed/padded 80-byte ASCII; count is little-endian uint32; records are little-endian float32; attribute bytes are zero; repeat hashes match. Reparse positions and bounds.

For GLB require magic `glTF`, version 2, correct total length, 4-byte JSON/BIN padding, one scene/node/mesh primitive, POSITION and uint32 index accessors with exact counts/min/max, fixed generator, and valid buffer-view offsets. Repeat hashes match.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_mesh_io.py -q
```

- [ ] **Step 3: Implement standard-library serializers**

`binary_stl_bytes(mesh)` recomputes outward unit normals in float64 and packs explicit little-endian float32 records. `glb_bytes(mesh, name)` packs tightly aligned float32 positions and uint32 indices, sorted compact JSON, no timestamp, JSON spaces/BIN zeros for padding, and `asset.extras.units="millimeter"`. Recipe/ledger remain unit authority because both formats are geometrically unitless.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_mesh_io.py -q
uv run ruff check src/kikuchi_lab/art_products/mesh_io.py
git add src/kikuchi_lab/art_products/mesh_io.py tests/unit/test_mesh_io.py
git commit -m "feat: serialize Ice globe mesh formats"
```

---

## Task 5: Render fixed review figures

**Files:**

- Create: `src/kikuchi_lab/art_products/globe_render.py`
- Test: `tests/unit/test_globe_render.py`

- [ ] **Step 1: Write RED render tests**

Require exact pixel dimensions, deterministic hashes, opaque background, different front/rear content, and exactly five in-sphere tier colors in diagnostics. Input field/mesh hashes remain unchanged.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_globe_render.py -q
```

Expected: missing renderer failure.

- [ ] **Step 3: Implement geometry-only views**

Use `Poly3DCollection` with fixed orthographic front `(20,-65)` and rear `(-20,115)` cameras. Grayscale shading uses face normals only. Diagnostic palette is `#101519`, `#3b4650`, `#707d86`, `#aab3b8`, `#f2f4f5`. Disable axes, perspective, automatic limits, and data-dependent lighting. Re-save PNG through Pillow without metadata. Never feed a rendered result back to the mesh.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_globe_render.py -q
uv run ruff check src/kikuchi_lab/art_products/globe_render.py tests/unit/test_globe_render.py
git add src/kikuchi_lab/art_products/globe_render.py tests/unit/test_globe_render.py
git commit -m "feat: render Ice globe review figures"
```

---

## Task 6: Publish reference and fine globe artifacts

**Files:**

- Create: `src/kikuchi_lab/art_products/globe_bundle.py`
- Create: `src/kikuchi_lab/workflows/ice_globe.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`, `src/kikuchi_lab/cli/main.py`
- Test: `tests/unit/test_globe_bundle.py`, `tests/integration/test_ice_globe.py`, `tests/unit/test_cli.py`

- [ ] **Step 1: Write RED bundle tests**

Require reference STL, fine STL, fine GLB, front/rear/tier PNGs, globe recipe, shared catalog, geometry ledger, validation report, and manifest. Before mutation reject forged catalog ID, noncanonical frame, count mismatch, field/catalog mismatch, open/reversed/intersecting mesh, missing tier, radius violation, additive overlap, STL/GLB mismatch, or figure-ledger mismatch. Test completed/partial collisions and CLI `render-ice-relief-globe --catalog /tmp/ice-art-catalog/art-band-catalog.json --recipe recipes/art/ice-ih-relief-globe.yml --output /tmp/ice-relief-globe`.

- [ ] **Step 2: Run RED**

```bash
uv run pytest tests/unit/test_globe_bundle.py tests/integration/test_ice_globe.py tests/unit/test_cli.py -q
```

- [ ] **Step 3: Implement workflow and atomic publisher**

Implement `render_ice_relief_globe(*, catalog_path, recipe_path, output_root) -> IceGlobeResult`. Revalidate catalog; print the finite topology/face bounds; build and validate reference first; then build fine; evaluate the same catalog/recipe on each; displace/validate with stage deadlines; serialize both STLs and fine GLB; render fine diagnostics; preflight every identity/hash; publish atomically. Stage progress goes to stderr and never enters identities.

Ledger catalog/recipe/field/mesh IDs, dimensions, radii, cohort occupancy, shoulder formula, max-overlap rule, profile counts, mm coordinates, science-art/presentation-only claims, and absent features. Validation JSON has separate reference/fine reports and noncanonical fabrication warnings.

CLI prints run/path/catalog/reference mesh/fine mesh/manifest fields as sorted JSON.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_globe_bundle.py tests/integration/test_ice_globe.py tests/unit/test_cli.py -q
uv run ruff check src/kikuchi_lab/art_products src/kikuchi_lab/workflows/ice_globe.py src/kikuchi_lab/cli/main.py
git add src/kikuchi_lab/art_products/globe_bundle.py src/kikuchi_lab/workflows/ice_globe.py src/kikuchi_lab/workflows/__init__.py src/kikuchi_lab/cli/main.py tests/unit/test_globe_bundle.py tests/integration/test_ice_globe.py tests/unit/test_cli.py
git commit -m "feat: publish Ice relief globe bundle"
```

---

## Task 7: Run real Ice reference/fine proof and acceptance gate

**Files:**

- Create: `docs/acceptance/ice-ih-relief-globe.md`
- Modify: `docs/work/KIKU-T030.md`
- Optional create: `docs/incubator/ice-globe-cradle.md`

- [ ] **Step 1: Build reference first**

Call the internal reference profile builder before allocating fine topology. Validate and inspect front/rear/tier views. Record elapsed time and peak memory as observations, not identities.

- [ ] **Step 2: Run the complete command once**

```bash
CATALOG_JSON="$(find local/ice-art-catalog -mindepth 2 -maxdepth 2 -name art-band-catalog.json -print)"
test "$(printf '%s\n' "$CATALOG_JSON" | sed '/^$/d' | wc -l | tr -d ' ')" = 1
uv run kikuchi-lab render-ice-relief-globe --catalog "$CATALOG_JSON" --recipe recipes/art/ice-ih-relief-globe.yml --output local/ice-relief-globe
```

After collision, inspect the existing complete/partial bundle or choose an explicit new root; never rerun blindly.

- [ ] **Step 3: Record evidence**

Acceptance records catalog/recipe/field/reference/fine/run/manifest IDs; exact topology and edge counts; STL/GLB sizes and hashes; parsed GLB accessor counts; radius/diameter/tier results; self-intersection results for both meshes; absent flat/opening/pedestal/cradle; preview paths/hashes; commands/software; and fabrication warnings. A cradle note, if desired, remains a separate parked idea and cannot alter canonical geometry.

- [ ] **Step 4: Full verification and candidate commit**

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/validate_work_items.py
git diff --check
git add docs/acceptance/ice-ih-relief-globe.md docs/work/KIKU-T030.md
git commit -m "docs: record Ice relief globe candidate"
```

Keep T030 active with visual review open. Show front, rear, tier diagnostic, and GLB location to the user. After explicit acceptance of readable levels, broad plateaus, coherent bands, and no spikes/lumps, record approval, mark T030 done, and commit `docs: accept Ice relief globe`.

---

## Completion Checklist

- [ ] Globe consumes the exact verified shared catalog ID.
- [ ] Radial field is canonical-frame, maximum-tier, capped, and filter-free.
- [ ] Tier radii are exactly 68.00, 69.75, 71.50, 73.25, 75.00 mm.
- [ ] Reference/fine counts match 28,902/57,800 and 115,602/231,200.
- [ ] Both meshes are finite, connected, closed, outward, nondegenerate, unique, and non-self-intersecting.
- [ ] STL and GLB reproduce validated counts and bounds deterministically.
- [ ] Bundle has all mesh, view, recipe, catalog, ledger, validation, and manifest artifacts.
- [ ] First sphere has no flat, hole, stand, or cradle.
- [ ] Full pytest, Ruff, tracker, and diff checks pass without touching protected dirty files.
