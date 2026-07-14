# Kikuchipy Kinematical Reference Products Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reproducible forsterite kinematical bundle whose promoted quiet etched-master balances exact band traces with a wide grayscale master-pattern range, alongside stereographic, spherical, Lambert, and detector reference products.

**Architecture:** Keep kikuchipy and diffsims as the crystallographic and projection engines. A private adapter session may hold upstream objects during one run, but only immutable arrays, plain reflection records, coordinate ledgers, deterministic figure bytes, and hashes cross the public project boundary. Build this standalone bundle before changing the accepted dynamical final bundle; the evidence-guided dynamical hybrid requires a separate plan after the native-scale visual gate.

**Tech Stack:** Python 3.12; kikuchipy 0.13.0; diffsims 0.7.0; orix 0.14.x; diffpy.structure 3.3.x; NumPy 2.x; Matplotlib 3.11.x for deterministic projected and fixed spherical figures; Pillow/imageio for deterministic image output; pytest; Ruff; repo-native Markdown work tracking. PyVista remains an optional incubated dependency for the freely rotatable sphere.

## Global Constraints

- Never use Gaussian, box, median, bilateral, non-local-means, diffusion, low-pass, downsample-upscale, or any other blur-like cleanup in these products.
- The etched-master grayscale layer and exact-trace layer must come from the same phase, energy, reciprocal-lattice enumeration, hemisphere, and stereographic coordinate system.
- Tone expansion must be pointwise and monotonic; use the recorded percentile window plus inverse-hyperbolic-sine mapping, never a spatial filter.
- Keep `scientific-clean`, its dynamical projection, and the existing final-bundle schema unchanged in this slice.
- Use the tracked `COD-9000319` structure and the existing explicit Pbnm-to-Pnma transformation `(a,b,c)->(b,c,a)` and `(x,y,z)->(y,z,x)`.
- Record crystal, sample, detector, projection, hemisphere, origin, wrap, units, transform owner, and `[011]` spot-check semantics in every run ledger.
- Do not add Leaflet, MapLibre, D3, a browser map, or a terrestrial basemap.
- Do not use ImageGen in this slice. Generated atmosphere or material treatments may only become separately labeled `art-polished` derivatives of accepted deterministic figures.
- Stereographic geometry and detector traces remain in projection space; labels, rim width, and minimum stroke width are presentation-space properties.
- Use test-driven development and commit after every accepted task. Do not push a remote branch.

## Scope Boundary

This plan ends at the pure-kinematical visual decision gate. It does not build the `BandModel`, `gallery-focused`, or evidence-guided dynamical reconstruction described in the broader design. Those capabilities depend on whether the accepted etched-master and detector figures leave a real aesthetic or scientific gap, so they form a separate testable project slice.

It also does not build the parked interactive sphere or openable GLB/VTP model.
The fixed-camera spherical figure in this plan is immediate evidence for that
addition, while `docs/incubator/interactive-spherical-view.md` preserves the
freely rotatable viewing and exchange requirements without displacing the
fundamental projected-image goal.

## File Map

| Path | Responsibility |
| --- | --- |
| `src/kikuchi_lab/kinematical/contracts.py` | Immutable recipes, plain-data products, execution result, and identity rules. |
| `src/kikuchi_lab/kinematical/recipe.py` | Strict YAML loader with paths resolved relative to the recipe. |
| `src/kikuchi_lab/kinematical/kikuchipy_adapter.py` | Pnma phase conversion, diffsims reflection selection, kikuchipy master/detector simulation, and coordinate ledger. |
| `src/kikuchi_lab/kinematical/render.py` | Direct stereographic/spherical figures and no-blur etched-master rendering. |
| `src/kikuchi_lab/kinematical/bundle.py` | Standalone atomic bundle, inventory, manifest, and canonical run identity. |
| `src/kikuchi_lab/kinematical/__init__.py` | Export only project-owned public types and functions. |
| `src/kikuchi_lab/workflows/kinematical.py` | Load, verify, simulate, render, bundle, and report one run. |
| `src/kikuchi_lab/workflows/__init__.py` | Export the new workflow result and entry point. |
| `src/kikuchi_lab/cli/main.py` | Add `render-kinematical` without changing existing commands. |
| `recipes/kinematical/forsterite-etched-master.yml` | Selected `[011]` production recipe, promoted quiet style, and retained balanced diagnostic. |
| `tests/unit/test_kinematical_contracts.py` | Contract, immutability, identity, and recipe validation. |
| `tests/adapters/test_kikuchipy_kinematical.py` | Phase transform, reflector selection, direct-call parity, and coordinate checks. |
| `tests/unit/test_kinematical_render.py` | Pointwise tone mapping, circular mask, exact trace provenance, and deterministic SVG/PNG. |
| `tests/unit/test_kinematical_bundle.py` | Inventory, hashes, atomic writes, and run identity. |
| `tests/integration/test_kinematical_workflow.py` | End-to-end small run and existing-product isolation. |
| `tests/unit/test_cli.py` | CLI argument and error normalization tests. |
| `docs/acceptance/kinematical-forsterite.md` | Native-scale visual checklist and explicit next-slice decision. |

---

### Task 1: Kinematical Contracts and Forsterite Recipe (`KIKU-T013`)

**Files:**
- Create: `src/kikuchi_lab/kinematical/contracts.py`
- Create: `src/kikuchi_lab/kinematical/recipe.py`
- Create: `src/kikuchi_lab/kinematical/__init__.py`
- Create: `recipes/kinematical/forsterite-etched-master.yml`
- Create: `tests/unit/test_kinematical_contracts.py`
- Modify: `docs/work/KIKU-T013.md`

**Interfaces:**
- Consumes: existing `Orientation`, `DetectorRecipe`, `plain_data()`, `stable_id()`, and `canonical_json()`.
- Produces: `EtchedMasterStyle`, `KinematicalRecipe`, `KinematicalArrayProduct`, `KinematicalSimulation`, `KinematicalExecution`, and `load_kinematical_recipe(path)`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_forsterite_kinematical_recipe_fixes_two_etched_styles() -> None:
    recipe = load_kinematical_recipe(RECIPE)
    assert recipe.energy_kev == 20.0
    assert recipe.orientation.euler_bunge_deg == (45.0, 51.50414783, 0.0)
    assert recipe.zone_axis_uvw == (0, 1, 1)
    assert recipe.min_dspacing_angstrom == 0.7
    assert recipe.master_relative_factor == 0.03
    assert recipe.promoted_style == "quiet"
    assert recipe.hemisphere == "both"
    assert [(style.name, style.overlay_relative_factor) for style in recipe.styles] == [
        ("balanced", 0.14),
        ("quiet", 0.22),
    ]


def test_kinematical_array_product_owns_finite_float32_data() -> None:
    source = np.arange(25, dtype=np.float64).reshape(5, 5)
    product = KinematicalArrayProduct.from_array(
        "master-stereographic",
        source,
        metadata={"projection": "stereographic", "hemisphere": "upper"},
    )
    source[:] = -1
    assert product.intensity.dtype == np.float32
    assert not product.intensity.flags.writeable
    assert product.intensity[0, 0] == 0
    assert product.product_id.startswith("kinematical-")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `uv run pytest tests/unit/test_kinematical_contracts.py -q`

Expected: collection fails because `kikuchi_lab.kinematical` does not exist.

- [ ] **Step 3: Add immutable project-owned contracts**

Implement these exact public shapes in `contracts.py`; keep validation helpers private and serialize every mapping through `plain_data()` before hashing:

```python
def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


@dataclass(frozen=True)
class EtchedMasterStyle:
    name: str
    overlay_relative_factor: float
    line_alpha: float
    line_width_pt: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class KinematicalRecipe:
    schema_version: int
    name: str
    source_record: str
    energy_kev: float
    orientation: Orientation
    zone_axis_uvw: tuple[int, int, int]
    detector: DetectorRecipe
    min_dspacing_angstrom: float
    scattering_params: str
    master_relative_factor: float
    half_size: int
    hemisphere: str
    master_scaling: str
    tone_percentiles: tuple[float, float]
    tone_asinh_scale: float
    figure_size_px: int
    promoted_style: str
    styles: tuple[EtchedMasterStyle, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_record": self.source_record,
            "energy_kev": self.energy_kev,
            "orientation": self.orientation.to_dict(),
            "zone_axis_uvw": list(self.zone_axis_uvw),
            "detector": self.detector.to_dict(),
            "reflections": {
                "min_dspacing_angstrom": self.min_dspacing_angstrom,
                "scattering_params": self.scattering_params,
                "master_relative_factor": self.master_relative_factor,
            },
            "master": {
                "half_size": self.half_size,
                "hemisphere": self.hemisphere,
                "scaling": self.master_scaling,
            },
            "tone": {
                "percentiles": list(self.tone_percentiles),
                "asinh_scale": self.tone_asinh_scale,
            },
            "figure_size_px": self.figure_size_px,
            "promoted_style": self.promoted_style,
            "styles": [style.to_dict() for style in self.styles],
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


@dataclass(frozen=True, init=False, eq=False)
class KinematicalArrayProduct:
    label: str
    intensity: np.ndarray
    metadata: Mapping[str, object]
    array_sha256: str
    product_id: str

    @classmethod
    def from_array(
        cls, label: str, intensity: object, *, metadata: Mapping[str, object]
    ) -> "KinematicalArrayProduct":
        array = np.ascontiguousarray(np.asarray(intensity, dtype=np.float32))
        if array.ndim not in (2, 3) or not array.size or not np.isfinite(array).all():
            raise ValueError("kinematical intensity must be finite, non-empty, and 2D or 3D")
        owned = np.frombuffer(array.tobytes(order="C"), dtype=np.float32).reshape(array.shape)
        checksum = hashlib.sha256(owned.tobytes(order="C")).hexdigest()
        plain = plain_data(metadata)
        product = object.__new__(cls)
        object.__setattr__(product, "label", label)
        object.__setattr__(product, "intensity", owned)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "array_sha256", checksum)
        object.__setattr__(
            product,
            "product_id",
            stable_id("kinematical", {"label": label, "metadata": plain, "array_sha256": checksum}),
        )
        return product
```

Also define `KinematicalSimulation` with `master_stereographic`, `master_lambert`, `detector`, `reflector_catalog`, and `projection_ledger`; define `KinematicalExecution` with `simulation` and an immutable `figures: Mapping[str, bytes]`.

Add this exact product iterator so bundle code never rediscovers field names:

```python
def products(self) -> dict[str, KinematicalArrayProduct]:
    return {
        "master-stereographic": self.master_stereographic,
        "master-lambert": self.master_lambert,
        "detector": self.detector,
    }
```

- [ ] **Step 4: Add strict YAML loading and the production recipe**

Use exact fields, reject unknown top-level keys, require schema integer `1`,
allow only `upper`, `lower`, or `both`, require `square`, require named styles
in stable order, require `promoted_style` to name exactly one style, and
construct the existing public recipe types. The production YAML must contain:

```yaml
schema_version: 1
name: forsterite-011-etched-master
source_record: ../../phases/forsterite/source.yml
energy_kev: 20.0
orientation:
  euler_bunge_deg: [45.0, 51.50414783, 0.0]
  frame: crystal_to_sample
  zone_axis_uvw: [0, 1, 1]
detector:
  shape: [1536, 2048]
  pcx: 0.50
  pcy: 0.72
  pcz: 0.60
  pc_convention: tsl
  sample_tilt_deg: 70.0
  detector_tilt_deg: 0.0
  detector_azimuth_deg: 0.0
  detector_twist_deg: 0.0
  pixel_size_um: 5.859375
  binning: 1
  supersampling: 1
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  master_relative_factor: 0.03
master:
  half_size: 1024
  hemisphere: both
  scaling: square
tone:
  percentiles: [0.5, 99.85]
  asinh_scale: 7.0
figure_size_px: 2400
promoted_style: quiet
styles:
  - {name: balanced, overlay_relative_factor: 0.14, line_alpha: 0.54, line_width_pt: 0.36}
  - {name: quiet, overlay_relative_factor: 0.22, line_alpha: 0.62, line_width_pt: 0.42}
```

- [ ] **Step 5: Run contract tests and the fast suite**

Run: `uv run pytest tests/unit/test_kinematical_contracts.py -q && uv run pytest -m "not slow and not gpu" -q`

Expected: all tests pass; the existing suite count increases only by the new contract cases.

- [ ] **Step 6: Accept the tracker item and commit**

Set `KIKU-T013` to `done`, check its three acceptance criteria, and add the recipe and contract-test paths to `evidence`.

```bash
git add src/kikuchi_lab/kinematical recipes/kinematical tests/unit/test_kinematical_contracts.py docs/work/KIKU-T013.md
git commit -m "feat: define kinematical recipes and products"
```

---

### Task 2: Pnma Phase and Reflection Adapter (`KIKU-T014`)

**Files:**
- Create: `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`
- Create: `tests/adapters/test_kikuchipy_kinematical.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `docs/work/KIKU-T014.md`

**Interfaces:**
- Consumes: `StructureRecord`, `KinematicalRecipe`, and tracked source transformation metadata.
- Produces privately: `_phase_from_record(record) -> Phase`, `_enumerate_reflectors(phase, recipe) -> ReciprocalLatticeVector`, `_select_reflectors(reflectors, relative_factor, energy_kev) -> ReciprocalLatticeVector`, and `_reflection_catalog(reflectors, recipe, threshold) -> dict[str, object]`.

- [ ] **Step 1: Write failing phase and reflector tests**

```python
def test_phase_adapter_applies_verified_pbnm_to_pnma_basis() -> None:
    phase = _phase_from_record(load_structure_record(SOURCE))
    assert phase.space_group.number == 62
    assert phase.space_group.short_name.replace(" ", "") == "Pnma"
    np.testing.assert_allclose(
        phase.structure.lattice.cell_parms(),
        [10.207, 5.980, 4.756, 90.0, 90.0, 90.0],
    )
    np.testing.assert_allclose(phase.structure[1].xyz, [0.27740, 0.25000, 0.99150])


def test_reflection_catalog_records_selection_physics() -> None:
    recipe = load_kinematical_recipe(RECIPE)
    reflectors = _enumerate_reflectors(_phase_from_record(load_structure_record(SOURCE)), recipe)
    selected = _select_reflectors(reflectors, recipe.master_relative_factor, recipe.energy_kev)
    catalog = _reflection_catalog(selected, recipe, threshold=recipe.master_relative_factor)
    assert catalog["units"] == {"dspacing": "angstrom", "theta": "radian"}
    assert catalog["retained_count"] == selected.size
    assert all(set(row) == {"hkl", "dspacing_angstrom", "structure_factor_abs", "theta_radian"} for row in catalog["reflections"])
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/adapters/test_kikuchipy_kinematical.py -q`

Expected: import failure for the new adapter functions.

- [ ] **Step 3: Declare the direct diffsims dependency**

Add `"diffsims==0.7.0"` beside `diffpy-structure` and
`"matplotlib>=3.11,<3.12"` beside `kikuchipy` in `pyproject.toml`, then run
`uv lock`. This makes both public APIs called directly explicit project
dependencies rather than relying on kikuchipy's transitive declarations.

- [ ] **Step 4: Implement the verified phase conversion**

```python
def _phase_from_record(record: StructureRecord) -> Phase:
    verify_structure(record)
    if record.simulation_setting["target_lattice_from_source"] != ["b", "c", "a"]:
        raise ValueError("unsupported kinematical lattice transform")
    if record.simulation_setting["target_fractional_from_source"] != ["y", "z", "x"]:
        raise ValueError("unsupported kinematical coordinate transform")
    a, b, c, alpha, beta, gamma = record.lattice_angstrom
    lattice = Lattice(b, c, a, beta, gamma, alpha)
    atoms = [
        Atom(
            site.element,
            xyz=(site.fract[1], site.fract[2], site.fract[0]),
            label=site.label,
            occupancy=site.occupancy,
            Uisoequiv=site.u_iso_angstrom_sq,
        )
        for site in record.sites
    ]
    return Phase(
        name=record.name,
        space_group=record.space_group_number,
        structure=Structure(atoms=atoms, lattice=lattice, title=record.name),
    )
```

- [ ] **Step 5: Implement the official public reflection pipeline**

```python
def _enumerate_reflectors(
    phase: Phase, recipe: KinematicalRecipe
) -> ReciprocalLatticeVector:
    reflectors = ReciprocalLatticeVector.from_min_dspacing(
        phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    reflectors = reflectors[reflectors.allowed]
    reflectors = reflectors.unique(use_symmetry=True).symmetrise()
    reflectors.sanitise_phase()
    reflectors.calculate_structure_factor(scattering_params=recipe.scattering_params)
    return reflectors


def _select_reflectors(
    reflectors: ReciprocalLatticeVector,
    relative_factor: float,
    energy_kev: float,
) -> ReciprocalLatticeVector:
    amplitudes = np.abs(reflectors.structure_factor)
    selected = reflectors[amplitudes >= relative_factor * float(amplitudes.max())]
    selected.calculate_theta(energy_kev * 1_000.0)
    return selected
```

Serialize each selected row in stable upstream order with integer `hkl`, `dspacing`, `abs(structure_factor)`, and `theta`. Record enumerated, allowed, symmetrised, and retained counts plus package versions and threshold policy.

- [ ] **Step 6: Run adapter and regression tests**

Run: `uv run pytest tests/adapters/test_kikuchipy_kinematical.py tests/adapters/test_forsterite_source.py -q && uv run ruff check src tests`

Expected: all pass with no Ruff findings.

- [ ] **Step 7: Accept and commit**

Set `KIKU-T014` to `done`, check its criteria, and add the adapter test to evidence.

```bash
git add pyproject.toml uv.lock src/kikuchi_lab/kinematical/kikuchipy_adapter.py tests/adapters/test_kikuchipy_kinematical.py docs/work/KIKU-T014.md
git commit -m "feat: adapt tracked phases to kikuchipy reflections"
```

---

### Task 3: Master, Detector, and Coordinate-Ledger Products (`KIKU-T015`)

**Files:**
- Modify: `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`
- Modify: `src/kikuchi_lab/kinematical/contracts.py`
- Modify: `tests/adapters/test_kikuchipy_kinematical.py`
- Create: `tests/scientific/test_kinematical_projection_ledger.py`
- Modify: `docs/work/KIKU-T015.md`

**Interfaces:**
- Consumes: private selected reflectors, existing `_to_kikuchipy_rotation()`, existing `_to_kikuchipy_detector()`, and the recipe.
- Produces internally: `_KikuchipyContext`.
- Produces publicly: `simulate_kinematical_arrays(record, recipe) -> tuple[KinematicalSimulation, _KikuchipyContext]` where the context remains private to the package and is never serialized or exported from `kinematical.__init__`.

- [ ] **Step 1: Write direct-call parity and ledger tests**

```python
def test_adapter_arrays_match_direct_kikuchipy_public_calls() -> None:
    record = load_structure_record(SOURCE)
    recipe = replace(load_kinematical_recipe(RECIPE), half_size=32)
    simulation, context = simulate_kinematical_arrays(record, recipe)
    direct_stereo = context.master_simulator.calculate_master_pattern(
        half_size=32, hemisphere="both", scaling="square"
    )
    direct_lambert = direct_stereo.as_lambert(show_progressbar=False)
    direct_detector = direct_lambert.get_patterns(
        _to_kikuchipy_rotation(recipe.orientation),
        _to_kikuchipy_detector(recipe.detector),
        energy=recipe.energy_kev,
        dtype_out="float32",
        compute=True,
        show_progressbar=False,
    )
    np.testing.assert_array_equal(simulation.master_stereographic.intensity, direct_stereo.data)
    np.testing.assert_array_equal(simulation.master_lambert.intensity, direct_lambert.data)
    np.testing.assert_array_equal(simulation.detector.intensity, np.asarray(direct_detector.data).squeeze())


def test_projection_ledger_centers_selected_metric_aware_011_axis() -> None:
    recipe = load_kinematical_recipe(RECIPE)
    simulation, _ = simulate_kinematical_arrays(
        load_structure_record(SOURCE), replace(recipe, half_size=32)
    )
    check = simulation.projection_ledger["known_axis_check"]
    assert check["zone_axis_uvw"] == [0, 1, 1]
    assert check["expected_sample_direction"] == [0.0, 0.0, 1.0]
    assert check["misalignment_deg"] < 1e-6
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/adapters/test_kikuchipy_kinematical.py tests/scientific/test_kinematical_projection_ledger.py -q`

Expected: failures because simulation and ledger construction do not exist.

- [ ] **Step 3: Build one private upstream context and three owned arrays**

The context contains the master and per-style simulators, stereographic and Lambert signals, detector signal, and `on_detector()` geometry. Construct the public arrays as follows:

```python
master_signal = master_simulator.calculate_master_pattern(
    half_size=recipe.half_size,
    hemisphere=recipe.hemisphere,
    scaling=recipe.master_scaling,
)
lambert_signal = master_signal.as_lambert(show_progressbar=False)
detector_signal = lambert_signal.get_patterns(
    _to_kikuchipy_rotation(recipe.orientation),
    _to_kikuchipy_detector(recipe.detector),
    energy=recipe.energy_kev,
    dtype_out="float32",
    compute=True,
    show_progressbar=False,
)
detector_array = np.asarray(detector_signal.data, dtype=np.float32).squeeze()
```

Use `KinematicalArrayProduct.from_array()` for all three arrays. Metadata must record source ID and checksum, recipe ID, generator names and pinned versions, energy, threshold, projection, hemisphere, intensity meaning, orientation, detector, and provenance links.

- [ ] **Step 4: Build the source/method/coordinate ledger**

Use the existing metric-aware direct-lattice check: multiply `[u,v,w]` by standard-Pnma `[a,b,c]`, normalize, apply the active crystal-to-sample rotation, and compare with sample ND. Serialize this exact top-level shape:

```python
ledger = {
    "schema_version": 1,
    "source_method": {
        "phase_source_id": record.source_record.source_id,
        "reflection_engine": {"name": "diffsims", "version": version("diffsims")},
        "projection_engine": {"name": "kikuchipy", "version": version("kikuchipy")},
    },
    "frames": {
        "crystal": "standard-Pnma direct and reciprocal Cartesian frames",
        "orientation": recipe.orientation.to_dict(),
        "sample": "EDAX-TSL [RD, TD, ND]",
        "detector": "kikuchipy EBSDDetector with explicit PC convention",
        "handedness": "right-handed",
    },
    "projections": {
        "stereographic": {
            "hemisphere": "both",
            "hemisphere_order": ["upper", "lower"],
            "origin": "projection center",
            "row_axis": "Y ascending -1 to +1",
            "column_axis": "X ascending -1 to +1",
            "grid_formula": "coordinate[k] = -1 + 2*k/(N-1)",
            "valid_domain": "X^2 + Y^2 <= 1",
            "wrap": "none",
        },
        "lambert": {"hemisphere": "both", "hemisphere_order": ["upper", "lower"], "origin": "square center", "wrap": "none"},
        "detector": {"projection": "gnomonic", "pc_convention": recipe.detector.pc_convention},
    },
    "known_axis_check": known_axis_check,
    "presentation_space": ["labels", "minimum stroke width", "rim stroke"],
}
```

- [ ] **Step 5: Run scientific parity and frame tests**

Run: `uv run pytest tests/adapters/test_kikuchipy_kinematical.py tests/scientific/test_kinematical_projection_ledger.py -q`

Expected: exact array parity and `<1e-6` degree `[011]` alignment pass.

- [ ] **Step 6: Accept and commit**

Set `KIKU-T015` to `done`, check its criteria, and add both test files to evidence.

```bash
git add src/kikuchi_lab/kinematical tests/adapters/test_kikuchipy_kinematical.py tests/scientific/test_kinematical_projection_ledger.py docs/work/KIKU-T015.md
git commit -m "feat: generate kinematical projection products"
```

---

### Task 4: Etched Master and Projection Figures (`KIKU-T016`)

**Files:**
- Create: `src/kikuchi_lab/kinematical/render.py`
- Create: `tests/unit/test_kinematical_render.py`
- Modify: `src/kikuchi_lab/kinematical/kikuchipy_adapter.py`
- Modify: `src/kikuchi_lab/kinematical/__init__.py`
- Modify: `docs/work/KIKU-T016.md`

**Interfaces:**
- Consumes: private `_KikuchipyContext`, public simulation arrays, recipe styles, and ledger.
- Produces: `render_kinematical_figures(context, simulation, recipe) -> Mapping[str, bytes]` with keys `kinematical-stereographic-bands.svg`, `kinematical-spherical-bands.png`, `kinematical-detector-overlay.png`, `etched-master-balanced.png`, `etched-master-quiet.png`, and `reflector-selection.png`; `execute_kinematical(record, recipe) -> KinematicalExecution`.

- [ ] **Step 1: Write no-blur tone and render tests**

```python
def test_asinh_tone_map_is_pointwise_monotonic_and_does_not_move_pixels() -> None:
    image = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]], dtype=np.float32)
    toned = asinh_tone_map(image, percentiles=(0.0, 100.0), scale=7.0)
    assert toned.shape == image.shape
    assert np.all(np.diff(toned.ravel()) > 0)
    assert toned[0, 0] == pytest.approx(0.035)
    assert toned[-1, -1] == pytest.approx(0.935)


def test_etched_master_keeps_master_and_overlay_selection_separate() -> None:
    execution = small_kinematical_execution()
    assert load_kinematical_recipe(RECIPE).promoted_style == "quiet"
    assert set(execution.figures) == {
        "kinematical-stereographic-bands.svg",
        "kinematical-spherical-bands.png",
        "kinematical-detector-overlay.png",
        "etched-master-balanced.png",
        "etched-master-quiet.png",
        "reflector-selection.png",
    }
    assert execution.simulation.reflector_catalog["master"]["relative_factor"] == 0.03
    assert execution.simulation.reflector_catalog["overlays"]["balanced"]["relative_factor"] == 0.14
    assert execution.simulation.reflector_catalog["overlays"]["quiet"]["relative_factor"] == 0.22
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_kinematical_render.py -q`

Expected: missing renderer functions.

- [ ] **Step 3: Implement the pointwise grayscale field**

```python
def asinh_tone_map(
    image: np.ndarray, *, percentiles: tuple[float, float], scale: float
) -> np.ndarray:
    values = np.asarray(image, dtype=np.float64)
    low, high = (float(value) for value in np.percentile(values, percentiles))
    if not high > low:
        raise ValueError("tone percentile window must have positive width")
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    mapped = np.arcsinh(scale * normalized) / np.arcsinh(scale)
    return np.asarray(0.035 + 0.90 * mapped, dtype=np.float32)


def circular_stereographic_field(image: np.ndarray) -> np.ma.MaskedArray:
    coordinates = np.linspace(-1.0, 1.0, image.shape[0])
    yy, xx = np.meshgrid(coordinates, coordinates, indexing="ij")
    return np.ma.array(image, mask=(xx * xx + yy * yy) > 1.0)
```

Do not import `scipy.ndimage`, `skimage.filters`, or any smoothing routine in this module.
For the etched disk, select `simulation.master_stereographic.intensity[0]`
from the recorded `[upper, lower]` master array before applying these two
functions; retain both hemispheres unchanged in the scientific product.

- [ ] **Step 4: Render exact traces over the co-registered master**

For each style, call that style's already-selected simulator with these exact
arguments, then insert the circular master with `extent=(-1,1,-1,1)`,
`origin="lower"`, `interpolation="nearest"`, and lower z-order:

```python
figure = context.overlay_simulators[style.name].plot(
    projection="stereographic",
    mode="lines",
    hemisphere="upper",
    scaling="linear",
    return_figure=True,
    backend="matplotlib",
    color=(0.94, 0.97, 1.0, style.line_alpha),
    linewidth=style.line_width_pt,
)
```

Draw a one-point rim in presentation space, remove axes, fix the canvas to
`figure_size_px`, and save PNG with fixed metadata. Do not raster-detect edges
from the master.

- [ ] **Step 5: Render the direct stereographic, spherical, detector, and threshold figures**

Use `KikuchiPatternSimulator.plot()` directly for the stereographic SVG. Set
`matplotlib.rc_context({"svg.hashsalt": recipe.recipe_id})` and save with
`metadata={"Date": None}`. For spherical bands, use kikuchipy's supported
`projection="spherical", backend="matplotlib"` path with a fixed Matplotlib 3D
camera, dark background, and fixed canvas; record camera and renderer versions
in the ledger. This avoids adding PyVista to the canonical first slice. For the
detector overlay, use `context.detector_geometry.plot()` with a fixed figure
size. The reflector-selection panel uses nearest-neighbor thumbnail sampling
and external labels; no product array is resized or replaced.

- [ ] **Step 6: Join simulation and rendering without leaking upstream objects**

```python
def execute_kinematical(
    record: StructureRecord, recipe: KinematicalRecipe
) -> KinematicalExecution:
    simulation, context = simulate_kinematical_arrays(record, recipe)
    figures = render_kinematical_figures(context, simulation, recipe)
    return KinematicalExecution(simulation=simulation, figures=figures)
```

- [ ] **Step 7: Run render tests and inspect real development figures**

Run: `uv run pytest tests/unit/test_kinematical_render.py -q`

Then run the renderer with `half_size=256`, detector shape `(384, 512)`, and `figure_size_px=1200`, writing only to `local/visual-reviews/kinematical-development/`.

Expected: all tests pass and the directory contains six inspectable figures. Open both etched masters at native scale before proceeding.

- [ ] **Step 8: Accept and commit**

Set `KIKU-T016` to `done`, check its criteria, and add the development figure inventory and render test to evidence. Do not commit `local/` artifacts.

```bash
git add src/kikuchi_lab/kinematical tests/unit/test_kinematical_render.py docs/work/KIKU-T016.md
git commit -m "feat: render etched kinematical masters"
```

---

### Task 5: Standalone Atomic Bundle and Reproduction (`KIKU-T017`)

**Files:**
- Create: `src/kikuchi_lab/kinematical/bundle.py`
- Create: `tests/unit/test_kinematical_bundle.py`
- Create: `src/kikuchi_lab/workflows/kinematical.py`
- Create: `tests/integration/test_kinematical_workflow.py`
- Modify: `src/kikuchi_lab/workflows/__init__.py`
- Modify: `docs/work/KIKU-T017.md`

**Interfaces:**
- Consumes: `KinematicalExecution`, recipe, verified `StructureRecord`, and existing image/identity helpers.
- Produces: `KinematicalBundleResult(run_id, path, manifest_sha256)`, `KinematicalRunResult`, `write_kinematical_bundle(output_root, execution, recipe, source)`, and `render_kinematical(recipe_path, output_root)`.

- [ ] **Step 1: Write failing inventory and workflow tests**

```python
EXPECTED = {
    "provenance/source.json",
    "recipes/kinematical.json",
    "models/reflection-catalog.json",
    "diagnostics/projection-ledger.json",
    "products/kinematical-master-stereographic.npy",
    "products/kinematical-master-stereographic.png",
    "products/kinematical-master-lambert.npy",
    "products/kinematical-master-lambert.png",
    "products/kinematical-detector.npy",
    "products/kinematical-detector.png",
    "figures/kinematical-stereographic-bands.svg",
    "figures/kinematical-spherical-bands.png",
    "figures/kinematical-detector-overlay.png",
    "figures/etched-master-balanced.png",
    "figures/etched-master-quiet.png",
    "figures/reflector-selection.png",
}


def test_kinematical_bundle_has_canonical_inventory_and_hashes(tmp_path: Path) -> None:
    result = write_kinematical_bundle(
        tmp_path,
        fixture_execution(),
        fixture_recipe(),
        fixture_source(),
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert set(manifest["files"]) == EXPECTED
    assert {str(path.relative_to(result.path)) for path in result.path.rglob("*") if path.is_file()} == EXPECTED | {"manifest.json"}
    for relative, record in manifest["files"].items():
        assert record["sha256"] == sha256(result.path / relative)


def test_render_kinematical_does_not_touch_existing_final_bundle_code(tmp_path: Path) -> None:
    result = render_kinematical(
        recipe_path=small_recipe(tmp_path), output_root=tmp_path / "runs"
    )
    assert result.path.name == result.run_id
    assert (result.path / "figures/etched-master-quiet.png").is_file()
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_kinematical_bundle.py tests/integration/test_kinematical_workflow.py -q`

Expected: missing bundle and workflow modules.

- [ ] **Step 3: Implement canonical bundle identity and atomic writing**

The run identity contains only stable scientific inputs:

```python
run_identity = {
    "schema_version": 1,
    "recipe_id": recipe.recipe_id,
    "source_id": source.source_record.source_id,
    "source_sha256": source.sha256,
    "products": {
        label: {
            "product_id": product.product_id,
            "array_sha256": product.array_sha256,
        }
        for label, product in simulation.products().items()
    },
    "reflection_catalog_id": stable_id("reflection-catalog", simulation.reflector_catalog),
    "projection_ledger_id": stable_id("projection-ledger", simulation.projection_ledger),
}
run_id = stable_id("kinematical-run", run_identity)
```

Write to a sibling `.<run_id>.partial-<uuid>` directory, fsync files and directories, write `manifest.json` last, then rename atomically. Raise a specific error if the complete destination or a partial destination exists. Use `write_npy()` for 2D products; for a 3D hemisphere array write `np.save()` directly with `allow_pickle=False`. Quantize PNG display copies pointwise and record black/white points; never mutate float products.

For the two-hemisphere stereographic and Lambert PNGs, concatenate the
independently pointwise-mapped upper and lower arrays side by side in recorded
`[upper, lower]` order. Do not resample either hemisphere.

- [ ] **Step 4: Implement the workflow**

```python
def render_kinematical(
    *, recipe_path: str | Path, output_root: str | Path
) -> KinematicalRunResult:
    recipe_file = Path(recipe_path).resolve()
    recipe = load_kinematical_recipe(recipe_file)
    source_path = (recipe_file.parent / recipe.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    execution = execute_kinematical(source, recipe)
    bundle = write_kinematical_bundle(Path(output_root), execution, recipe, source)
    return KinematicalRunResult(
        run_id=bundle.run_id,
        path=bundle.path,
        recipe_id=recipe.recipe_id,
        master_reflector_count=int(
            execution.simulation.reflector_catalog["master"]["retained_count"]
        ),
        figure_names=tuple(sorted(execution.figures)),
    )
```

- [ ] **Step 5: Prove reproduction and existing-bundle isolation**

Run: `uv run pytest tests/unit/test_kinematical_bundle.py tests/integration/test_kinematical_workflow.py tests/unit/test_artifact_bundle.py tests/integration/test_final_workflow.py -q`

Expected: all pass; no expected inventory or schema changes are needed in existing final-bundle tests.

- [ ] **Step 6: Accept and commit**

Set `KIKU-T017` to `done`, check its criteria, and link the bundle and workflow tests as evidence.

```bash
git add src/kikuchi_lab/kinematical/bundle.py src/kikuchi_lab/workflows tests/unit/test_kinematical_bundle.py tests/integration/test_kinematical_workflow.py docs/work/KIKU-T017.md
git commit -m "feat: bundle reproducible kinematical runs"
```

---

### Task 6: CLI, Production Figures, and Visual Decision Gate (`KIKU-T018`)

**Files:**
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `tests/unit/test_cli.py`
- Create: `docs/acceptance/kinematical-forsterite.md`
- Modify: `docs/acceptance/forsterite-milestone.md`
- Modify: `docs/work/KIKU-T018.md`
- Modify after approval: `docs/work/KIKU-F002.md`

**Interfaces:**
- Consumes: `render_kinematical(recipe_path, output_root)`.
- Produces: CLI command `kikuchi-lab render-kinematical --recipe PATH --output PATH` and a JSON result with `run_id`, `path`, `recipe_id`, `master_reflector_count`, and `figures`.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_render_kinematical_cli_forwards_paths_and_prints_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed = {}

    def fake_render_kinematical(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            run_id="kinematical-run-0123456789abcdef",
            path=tmp_path / "kinematical-run-0123456789abcdef",
            recipe_id="recipe-0123456789abcdef",
            master_reflector_count=2546,
            figure_names=("etched-master-balanced.png", "etched-master-quiet.png"),
        )

    monkeypatch.setattr("kikuchi_lab.workflows.render_kinematical", fake_render_kinematical)
    status = main([
        "render-kinematical",
        "--recipe", "recipes/kinematical/forsterite-etched-master.yml",
        "--output", str(tmp_path / "runs"),
    ])
    assert status == 0
    assert observed["recipe_path"].endswith("forsterite-etched-master.yml")
    assert json.loads(capsys.readouterr().out)["master_reflector_count"] == 2546
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/unit/test_cli.py::test_render_kinematical_cli_forwards_paths_and_prints_inventory -q`

Expected: argparse rejects `render-kinematical`.

- [ ] **Step 3: Add the CLI command with normalized errors**

Add a subparser with required `--recipe` and `--output`. Catch `ValueError`, `OSError`, and kinematical bundle errors at the command boundary, write `kinematical render failed: <message>` to stderr without a traceback, and return `1`. On success print canonical JSON with the five result fields.

- [ ] **Step 4: Run the full production recipe and retain the bundle locally**

Run:

```bash
uv run kikuchi-lab render-kinematical \
  --recipe recipes/kinematical/forsterite-etched-master.yml \
  --output local/runs/kinematical
```

Expected: completion in bounded time; no indefinite process. The command prints one run ID and six figure names. If no new progress is visible for 60 seconds, inspect the process once and stop it rather than waiting blindly.

- [ ] **Step 5: Run all verification gates**

Run:

```bash
uv run pytest -m "not slow and not gpu" -q
uv run ruff check src tests
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
git diff --check
```

Expected: all tests pass, Ruff is clean, tracker validation succeeds, and no whitespace errors are reported.

- [ ] **Step 6: Conduct the user-facing native-scale review**

Present these exact bundle files at fit-to-window and 100 percent:

- `figures/etched-master-balanced.png`
- `figures/etched-master-quiet.png`
- `products/kinematical-master-stereographic.png`
- `products/kinematical-master-lambert.png`
- `products/kinematical-detector.png`
- `figures/kinematical-stereographic-bands.svg`
- `figures/kinematical-spherical-bands.png`
- `figures/reflector-selection.png`

Record the review in `docs/acceptance/kinematical-forsterite.md` with the
already-decided `quiet` promotion plus one explicit next-slice decision:
`pure-kinematical-refinement` or `plan-evidence-guided-hybrid`. Record
observations about grayscale hierarchy, trace density, node saturation, rim,
quiet regions, and whether the current quiet parameters need a recorded
adjustment. Keep the balanced candidate as a diagnostic regardless.

- [ ] **Step 7: Accept the task and feature only after the review**

Set `KIKU-T018` to `done` only after the decision is recorded and its three criteria are checked. Set `KIKU-F002` to `done` only when all six children and feature criteria are accepted. Add the retained run manifest and acceptance document to evidence.

- [ ] **Step 8: Commit the gate**

```bash
git add src/kikuchi_lab/cli/main.py tests/unit/test_cli.py docs/acceptance docs/work/KIKU-T018.md docs/work/KIKU-F002.md
git commit -m "feat: deliver forsterite kinematical reference bundle"
```

## Final Review Checklist

- [ ] Every scientific array and reflector record comes from the pinned public diffsims/kikuchipy pipeline.
- [ ] The etched master uses a dense master threshold and a separately recorded stronger trace threshold.
- [ ] `quiet` is the promoted style and `balanced` remains a retained density diagnostic.
- [ ] No blur-like operation, generated-image layer, or raster edge detector appears in the implementation or recipes.
- [ ] Projection and frame conventions are sufficient to explain the circular disk, spherical view, Lambert square, and detector pattern without chat history.
- [ ] The existing dynamical final bundle and `scientific-clean` tests remain unchanged and passing.
- [ ] The visual decision is recorded before any hybrid implementation plan is created.
- [ ] The fixed spherical figure is present, while interactive sphere/GLB/VTP work remains linked to its incubator record and does not replace projected products.
