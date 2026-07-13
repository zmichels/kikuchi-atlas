# Exceptional Forsterite Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task by task. Every
> production behavior follows `superpowers:test-driven-development`.

**Goal:** Produce a reproducible, scientifically traceable proof-to-final
pipeline for one exceptional forsterite EBSD pattern, using ebsdsim for the
dynamical master pattern and kikuchipy for detector projection.

**Architecture:** External simulator and projection objects remain behind
adapters. Frozen project-owned recipes and products form the public contract.
Each run writes a content-addressed artifact bundle containing source evidence,
raw products, explicit processing stages, diagnostics, and decision records.

**Tech Stack:** Python 3.12, uv, NumPy, ebsdsim 0.1.8, kikuchipy 0.13.0,
orix, scikit-image, tifffile, PyYAML, pytest, Ruff.

**Global Constraints:** Keep the repository local; do not configure a remote.
Large simulations and rendered products belong under ignored `local/`. Use the
COD 9000319 room-temperature forsterite structure as the initial cited source.
Never silently substitute a surrogate for the authoritative GPU recipe. Use an
arm64 uv-managed Python 3.12 runtime on Apple Silicon; reject a Rosetta/x86_64
runtime in the doctor. Store orientations as active crystal-to-sample Bunge
Euler angles in degrees. The kikuchipy adapter must explicitly invert that
active rotation to the passive sample-to-crystal Bunge rotation consumed by
its projection kernel. Record detector PC as dimensionless fractions with
an explicit vendor convention, and record tilt, azimuth, twist, pixel size,
binning, and sample tilt separately. Tests marked `gpu` or `slow` are separate
from the fast default gate.

---

## Delivery map

| Task | Production responsibility | Primary evidence |
|---|---|---|
| 1 | Repository, environment, tracker, CLI shell | import and tracker validation |
| 2 | Stable recipes, provenance, canonical products | contract unit tests |
| 3 | Forsterite source and ebsdsim adapter | source validation and tiny GPU smoke |
| 4 | Kikuchipy detector projection | adapter and geometry tests |
| 5 | Explicit processing graph | numerical/image invariant tests |
| 6 | Diagnostics and artifact bundles | round-trip and high-bit-depth tests |
| 7 | Symmetry-distinct candidate-set contract | crystallographic reduction tests |
| 8 | Proof rendering and contact sheet | deterministic proof integration |
| 9 | Human orientation-selection record | schema/CLI validation and user gate |
| 10 | Final rendering and reproduction | bundle comparison integration |
| 11 | Real GPU production and visual acceptance | coordinator/user evidence gate |
| 12 | Incubator records and milestone closure | tracker and broad-review evidence |

## Task 1: Bootstrap the package, tracker, and environment gate

**Files:**

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/kikuchi_lab/__init__.py`
- Create: `src/kikuchi_lab/cli/__init__.py`
- Create: `src/kikuchi_lab/cli/main.py`
- Create: `tests/unit/test_cli.py`
- Create: `pytest.ini`
- Create: `docs/work/index.md`
- Create: `docs/work/KIKU-E001.md`
- Create: `docs/work/KIKU-F001.md`
- Create: `docs/work/KIKU-T001.md` through `docs/work/KIKU-T012.md`
- Copy with attribution: `scripts/validate_work_items.py`
- Copy with attribution: `scripts/work_status.py`
- Copy with attribution: `scripts/new_work_item.py`
- Modify: `.gitignore`

### Step 1: Write the failing CLI test

```python
# tests/unit/test_cli.py
from kikuchi_lab.cli.main import main


def test_version_command_reports_package_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "kikuchi-lab 0.1.0"
```

Run:

```bash
uv run --python 3.12 pytest tests/unit/test_cli.py -q
```

Expected: FAIL because `kikuchi_lab` does not exist.

### Step 2: Add the minimal package and pinned environment

Use a Hatchling `src/` package. Pin `ebsdsim==0.1.8` and
`kikuchipy==0.13.0`; bound the remaining direct dependencies by compatible
minor or major ranges. Expose:

```toml
[project.scripts]
kikuchi-lab = "kikuchi_lab.cli.main:entrypoint"
```

Implement `main(argv: list[str] | None = None) -> int` with `argparse`, a
`version` subcommand, and an `entrypoint()` wrapper that raises `SystemExit`.
Install uv's native runtime before syncing; do not allow uv to select the
existing `/usr/local` x86_64 Python under Rosetta:

Run:

```bash
uv python install 3.12
UV_PYTHON_PREFERENCE=only-managed uv sync --python 3.12
uv run python -c 'import platform; assert platform.machine() == "arm64"'
uv run pytest tests/unit/test_cli.py -q
uv run ruff check src tests
```

Expected: PASS.

### Step 3: Create and validate repo-native work items

Use prefix `KIKU`, symmetric parent/child links, and exact task mapping:

- `KIKU-E001` -> `KIKU-F001`
- `KIKU-F001` -> `KIKU-T001` through `KIKU-T012`
- mark only `KIKU-T001` complete at the end of this task;
- put task-specific acceptance criteria and evidence paths in every item;
- record parked directions only in incubator task 8, not active acceptance.

Copy the three tracker helpers from the repo-native-work-tracking skill into
`scripts/`, retaining their attribution headers. Then run:

```bash
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
```

Expected: validation passes; status shows one epic, one feature, and twelve
tasks with only `KIKU-T001` complete.

### Step 4: Commit

```bash
git add pyproject.toml uv.lock pytest.ini README.md src tests docs/work scripts .gitignore
git commit -m "build: bootstrap kikuchi lab package"
```

## Task 2: Define stable recipes, provenance, and canonical products

**Files:**

- Create: `src/kikuchi_lab/model/__init__.py`
- Create: `src/kikuchi_lab/model/identity.py`
- Create: `src/kikuchi_lab/model/provenance.py`
- Create: `src/kikuchi_lab/model/recipes.py`
- Create: `src/kikuchi_lab/model/products.py`
- Create: `src/kikuchi_lab/model/persistence.py`
- Create: `tests/unit/test_identity.py`
- Create: `tests/unit/test_recipes.py`
- Create: `tests/unit/test_products.py`
- Create: `tests/unit/test_persistence.py`
- Modify: `docs/work/KIKU-T002.md`

### Step 1: Write failing identity and immutability tests

```python
def test_recipe_identity_is_key_order_independent():
    left = stable_id("recipe", {"b": 2, "a": 1})
    right = stable_id("recipe", {"a": 1, "b": 2})
    assert left == right


def test_master_pattern_owns_a_read_only_float32_array():
    source = np.arange(18, dtype=np.float64).reshape(2, 3, 3)
    product = MasterPatternProduct.from_array(source, metadata=valid_metadata())
    source[:] = -1
    assert product.intensity.dtype == np.float32
    assert product.intensity.flags.writeable is False
    assert product.intensity[0, 0, 0] == 0
```

Also test rejection of NaN/Inf, non-`(2, y, x)` hemisphere arrays, absent
units/frame fields, inconsistent energy metadata, and mutation of frozen recipe
objects.

Run:

```bash
uv run pytest tests/unit/test_identity.py tests/unit/test_recipes.py tests/unit/test_products.py tests/unit/test_persistence.py -q
```

Expected: FAIL on missing modules.

### Step 2: Implement canonical serialization and frozen contracts

Implement `canonical_json()` with sorted keys, compact separators, UTF-8, and
rejection of non-finite floats. Implement `stable_id(kind, payload)` as
`<kind>-<first 16 lowercase hex chars of SHA-256>`.

Use frozen dataclasses for:

```python
SourceRecord(uri, sha256, license, citation)
PhaseRecord(name, formula, space_group_number, setting, lattice_angstrom)
SimulationRecipe(voltage_kv, halfw, dmin_nm, energy_binwidth_kev,
                 n_trajectories, sigma_deg, omega_deg, rank, chunk_size,
                 marginal_coverage, relative_image_stop, mc_backend,
                 bethe_c_strong, bethe_c_weak, bethe_c_cutoff,
                 dbdiff_sg_cutoff, mc_auto_stop, mc_relative_tol,
                 mc_min_trajectories, mc_max_trajectories, exact_slow_cpu)
Orientation(euler_bunge_deg, frame="crystal_to_sample")
DetectorRecipe(shape, pcx, pcy, pcz, pc_convention, sample_tilt_deg,
               detector_tilt_deg, detector_azimuth_deg, detector_twist_deg,
               pixel_size_um, binning, supersampling)
ProcessingStage(name, parameters)
ProcessingRecipe(stages)
```

`MasterPatternProduct` owns a copied read-only float32 array with shape
`(2, y, x)` ordered `[north, south]`. `DetectorPatternProduct` owns a copied
read-only 2-D float32 array and references both master and projection recipe
IDs. Metadata objects must serialize to plain JSON without NumPy scalar types.
Validate PC components as convention-dependent dimensionless fractions. Define
supersampling as multiplying detector rows/columns and dividing effective pixel
size by the same factor while keeping PC, tilts, azimuth, twist, binning, and
physical detector extent invariant.

Add `save_master_product()` and `load_master_product()` using a versioned NPZ
containing `intensity` and canonical UTF-8 `meta_json`. Product identity is
computed from canonical metadata plus the SHA-256 of C-contiguous float32 array
bytes, never from ZIP container bytes or local path. Test exact array, metadata,
read-only flag, checksum, and product-ID round trip; reject unknown schema
versions and corrupted array hashes.

Run the focused suite and then:

```bash
uv run pytest tests/unit -q
```

Expected: PASS.

### Step 3: Commit

Update `KIKU-T002` to complete with test evidence, validate tracker, then:

```bash
git add src/kikuchi_lab/model tests/unit docs/work
git commit -m "feat: add canonical kikuchi data contracts"
```

## Task 3: Validate forsterite and isolate ebsdsim

**Files:**

- Create: `phases/forsterite/COD-9000319.cif`
- Create: `phases/forsterite/source.yml`
- Create: `reference/catalog/crystallography-open-database.yml`
- Create: `recipes/proof/forsterite-simulation.yml`
- Create: `src/kikuchi_lab/sources/__init__.py`
- Create: `src/kikuchi_lab/sources/structure.py`
- Create: `src/kikuchi_lab/sources/ebsdsim_adapter.py`
- Create: `src/kikuchi_lab/doctor.py`
- Create: `tests/adapters/test_forsterite_source.py`
- Create: `tests/adapters/test_ebsdsim_adapter.py`
- Create: `tests/integration/test_ebsdsim_gpu.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `docs/work/KIKU-T003.md`

### Step 1: Acquire and record the room-temperature structure

Download `https://www.crystallography.net/cod/9000319.cif` once, retain the CIF
verbatim, and record its SHA-256, COD page, source publication, retrieval date,
license/copying policy, formula, space group 62, and expected cell parameters
in `source.yml`. The tracked file becomes the deterministic build input; normal
runs do not redownload it.

### Step 2: Write failing source validation tests

```python
def test_forsterite_source_matches_catalog():
    record = load_structure_record("phases/forsterite/source.yml")
    verified = verify_structure(record)
    assert verified.sha256_matches
    assert verified.parsed_formula == "Mg2SiO4"
    assert verified.parsed_space_group_number == 62
    assert verified.parsed_lattice_angstrom == pytest.approx(record.lattice_angstrom)
    assert verified.site_occupancies == pytest.approx(record.site_occupancies)
    assert verified.thermal_factor_policy == record.thermal_factor_policy


def test_ebsdsim_conversion_keeps_both_hemispheres(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)
    product = load_ebsdsim_npz(fixture, source=source_record())
    assert product.intensity.shape == (2, 9, 9)
    assert product.metadata["hemisphere_order"] == ["north", "south"]
```

Build the NPZ fixture by directly instantiating ebsdsim's public
`MasterPattern` with deterministic tiny fundamental-sector arrays and calling
its public `save()` method. Do not call either simulation entry point: both
surrogate and GPU Monte Carlo paths still require a WebGPU adapter. Add
negative tests for checksum mismatch, wrong phase metadata, absent hemisphere
semantics, and invalid arrays.

Parse the tracked CIF rather than trusting duplicated YAML. Compare formula,
space group, lattice parameters, sites, occupancies, and displacement-factor
presence/units against the catalog. The catalog must state the policy for any
missing thermal factors because ebsdsim defaults materially affect intensity.

Run:

```bash
uv run pytest tests/adapters/test_forsterite_source.py tests/adapters/test_ebsdsim_adapter.py -q
```

Expected: FAIL on missing implementation.

### Step 3: Implement the adapter and doctor

`generate_master_pattern()` must call only the public API:

```python
mp = ebsdsim.master_pattern_from_cif(
    cif_path,
    voltage_kv=recipe.voltage_kv,
    halfw=recipe.halfw,
    dmin=recipe.dmin_nm,
    energy_binwidth_keV=recipe.energy_binwidth_kev,
    n_trajectories=recipe.n_trajectories,
    sigma_deg=recipe.sigma_deg,
    omega_deg=recipe.omega_deg,
    rank=recipe.rank,
    chunk_size=recipe.chunk_size,
    marginal_coverage=recipe.marginal_coverage,
    relative_image_stop=recipe.relative_image_stop,
    mc_backend=recipe.mc_backend,
    bethe_c_strong=recipe.bethe_c_strong,
    bethe_c_weak=recipe.bethe_c_weak,
    bethe_c_cutoff=recipe.bethe_c_cutoff,
    dbdiff_sg_cutoff=recipe.dbdiff_sg_cutoff,
    mc_auto_stop=recipe.mc_auto_stop,
    mc_relative_tol=recipe.mc_relative_tol,
    mc_min_trajectories=recipe.mc_min_trajectories,
    mc_max_trajectories=recipe.mc_max_trajectories,
    exact_slow_cpu=recipe.exact_slow_cpu,
)
saved_path = mp.save(output_npz)
```

Then load the saved artifact with `ebsdsim.mploader.load_master_pattern()` and
`reconstruct_integrated()` to construct the canonical north/south product.
Record ebsdsim version, NPZ checksum, elapsed time, resolved simulation
metadata, and whether the requested backend was honored.
Compare ebsdsim's resolved `metadata["cell"]` formula/site content, space group,
lattice parameters, occupancies, and thermal factors to the validated source
record; fail on unexplained defaults or unit mismatches.

Add `kikuchi-lab doctor --json` reporting Python 3.12, package versions,
platform, Metal/macOS information, WebGPU adapter readiness, and output-root
writability. An unavailable GPU is a structured failed check, not an import
crash.

Add the production entry point:

```bash
kikuchi-lab simulate-master \
  --structure phases/forsterite/COD-9000319.cif \
  --source phases/forsterite/source.yml \
  --recipe recipes/proof/forsterite-simulation.yml \
  --output local/master-patterns
```

It writes the untouched ebsdsim NPZ plus the project-owned canonical product
using `save_master_product()`, validates both, and links their distinct
checksums/IDs in a small manifest. The command returns neither success nor a
canonical path until all artifacts validate.

Run:

```bash
uv run pytest tests/adapters -q
uv run kikuchi-lab doctor --json
```

Expected: adapter tests pass; doctor exits nonzero only when a required check
fails and emits valid JSON either way.

### Step 4: Add the tiny GPU integration gate

Mark the test `@pytest.mark.gpu` and `@pytest.mark.slow`. Use forsterite,
`halfw=8`, `energy_binwidth_kev=20`, `n_trajectories=4096`, `rank=4`, and
`chunk_size=8`, with `mc_auto_stop=False` so the requested 4096 trajectories
remain a bounded smoke test. Assert a saved NPZ, a finite `(2, 17, 17)` canonical product,
nonzero dynamic range, correct source ID, and requested backend provenance.

Run:

```bash
uv run pytest -m "gpu and slow" tests/integration/test_ebsdsim_gpu.py -q
```

Expected on the local M2: PASS. If it fails, diagnose the environment; do not
change the milestone recipe to `surrogate` without a decision record.

### Step 5: Commit

Update `KIKU-T003`, then:

```bash
git add phases reference src tests docs/work
git commit -m "feat: add traceable forsterite simulation source"
```

## Task 4: Implement the kikuchipy projection boundary

**Files:**

- Create: `src/kikuchi_lab/projection/__init__.py`
- Create: `src/kikuchi_lab/projection/kikuchipy_adapter.py`
- Create: `tests/adapters/test_kikuchipy_projection.py`
- Create: `tests/scientific/test_projection_invariants.py`
- Modify: `docs/work/KIKU-T004.md`

### Step 1: Write failing adapter and frame tests

Use the canonical integrated north/south product produced from the small
ebsdsim fixture. Test that one orientation and detector recipe produce a finite
float32 detector pattern at the *supersampled* shape, with orientation,
detector, energy, frame, PC convention, source NPZ checksum, and master ID
preserved. Add tests that reject unknown frames or PC conventions.

```python
def test_projection_preserves_public_geometry(canonical_master):
    out = project_with_kikuchipy(
        master=canonical_master,
        orientation=Orientation((0.0, 0.0, 0.0)),
        detector=DetectorRecipe(
            shape=(96, 128), pcx=0.5, pcy=0.5, pcz=0.6,
            pc_convention="bruker", sample_tilt_deg=70.0,
            detector_tilt_deg=0.0, detector_azimuth_deg=0.0,
            detector_twist_deg=0.0, pixel_size_um=70.0,
            binning=1, supersampling=2,
        ),
        energy_kev=20.0,
    )
    assert out.intensity.shape == (192, 256)
    assert out.metadata["orientation_frame"] == "crystal_to_sample"
    assert out.metadata["supersampling"] == 2
```

Add a behavioral orientation test, not only a metadata assertion: transform a
known crystal direction using a simple 90-degree active
crystal-to-EDAX-TSL-sample rotation and assert the expected RD/TD/ND direction.
This catches accidental use of orix's default passive `lab2crystal` convention.
Add a detector test proving supersampling halves effective pixel size while
preserving physical extent, PC, tilts, azimuth, twist, and binning.
Add a projection-level regression asserting that the adapter-supplied
quaternion equals kikuchipy's standard passive
`Rotation.from_euler(eulers, degrees=True, direction="lab2crystal")` result for
the same Bunge angles, and that the resulting image matches that direct call.

Run:

```bash
uv run pytest tests/adapters/test_kikuchipy_projection.py tests/scientific/test_projection_invariants.py -q
```

Expected: FAIL.

### Step 2: Implement only the public kikuchipy seam

Construct an in-memory `kikuchipy.signals.EBSDMasterPattern` from the canonical
integrated `(north, south, y, x)` array, `projection="lambert"`,
`hemisphere="both"`, and an orix `Phase` built from canonical phase metadata.
Do **not** reload the ebsdsim NPZ in this adapter: kikuchipy's ebsdsim reader
selects per-energy-bin slices when available, while the canonical product is
the Monte-Carlo-weighted integrated master pattern.

Construct the canonical active rotation with
`Rotation.from_euler(orientation.euler_bunge_deg, degrees=True,
direction="crystal2lab")`, then explicitly invert it before passing it to
`get_patterns()`. Construct
`EBSDDetector` with explicit `convention`, `pc`, `tilt`, `azimuthal`, `twist`,
`sample_tilt`, `px_size`, and `binning` at the supersampled shape. Call:

```python
signal = master_signal.get_patterns(
    rotation,
    detector,
    energy=energy_kev,
    dtype_out="float32",
    compute=True,
    show_progressbar=False,
)
intensity = np.asarray(signal.data, dtype=np.float32)
```

The projection adapter returns the supersampled image; Task 5 owns and records
downsampling. Assert that kikuchipy's float32 path preserves raw range (within
floating tolerance) and does not rescale to integer display bounds.

No kikuchipy or orix object may appear in the returned product.

Run focused and fast suites:

```bash
uv run pytest tests/adapters/test_kikuchipy_projection.py tests/scientific/test_projection_invariants.py -q
uv run pytest -m "not slow and not gpu" -q
```

Expected: PASS.

### Step 3: Commit

Update `KIKU-T004`, then commit:

```bash
git add src/kikuchi_lab/projection tests docs/work
git commit -m "feat: add source-neutral detector projection"
```

## Task 5: Build the explicit acquisition and gallery processing graph

**Files:**

- Create: `src/kikuchi_lab/processing/__init__.py`
- Create: `src/kikuchi_lab/processing/graph.py`
- Create: `src/kikuchi_lab/processing/stages.py`
- Create: `src/kikuchi_lab/processing/presets.py`
- Create: `tests/unit/test_processing_stages.py`
- Create: `tests/scientific/test_processing_invariants.py`
- Create: `recipes/proof/scientific-clean.yml`
- Create: `recipes/gallery/gallery-crisp.yml`
- Modify: `docs/work/KIKU-T005.md`

### Step 1: Write failing stage tests

Test the stages individually on deterministic synthetic band patterns:

- `background_divide(sigma_px, epsilon)` stays finite and positive;
- `robust_normalize(low_percentile, high_percentile)` maps its stated window;
- `local_contrast(clip_limit, kernel_size)` remains float32;
- `multiscale_detail(scales_px, gains)` has zero response to a constant image;
- `unsharp(radius_px, amount, threshold)` does not clip internally;
- `tone_map(black, white, gamma)` is monotonic;
- `downsample(shape)` preserves the requested shape and avoids aliasing;
- every stage returns a new read-only array and a serializable stage record.

```python
def test_graph_keeps_scientific_and_gallery_sources_identical():
    scientific = run_graph(projected, scientific_recipe)
    gallery = run_graph(projected, gallery_recipe)
    assert scientific.source_projection_id == gallery.source_projection_id
    assert scientific.product_id != gallery.product_id
```

Run:

```bash
uv run pytest tests/unit/test_processing_stages.py tests/scientific/test_processing_invariants.py -q
```

Expected: FAIL.

### Step 2: Implement the minimal named graph

Use scikit-image/NumPy primitives behind small project functions. The
scientific-clean preset ends after restrained tone mapping; gallery-crisp may
add multiscale detail and restrained sharpening. Return every intermediate in
an ordered `ProcessingResult`, with parameters and input/output IDs. Never
mutate or overwrite the detector projection.

Add structured warnings for clipping fraction above 0.1%, non-monotonic tone,
and high-frequency gain above a documented initial ceiling. Warnings are
evidence; they do not silently modify parameters.

Run:

```bash
uv run pytest tests/unit/test_processing_stages.py tests/scientific/test_processing_invariants.py -q
uv run pytest -m "not slow and not gpu" -q
```

Expected: PASS.

### Step 3: Commit

Update `KIKU-T005`, then:

```bash
git add src/kikuchi_lab/processing tests recipes docs/work
git commit -m "feat: add inspectable kikuchi processing graph"
```

## Task 6: Write diagnostic and artifact bundles

**Files:**

- Create: `src/kikuchi_lab/diagnostics/__init__.py`
- Create: `src/kikuchi_lab/diagnostics/image_metrics.py`
- Create: `src/kikuchi_lab/artifacts/__init__.py`
- Create: `src/kikuchi_lab/artifacts/bundle.py`
- Create: `src/kikuchi_lab/artifacts/images.py`
- Create: `tests/unit/test_diagnostics.py`
- Create: `tests/unit/test_artifact_bundle.py`
- Create: `docs/decisions/0001-artifact-identity-and-bundle-layout.md`
- Modify: `docs/work/KIKU-T006.md`

### Step 1: Write failing metric and export tests

Test robust percentiles, clipping fractions, gradient distribution, and
low/mid/high radial-frequency energy on known arrays. Test that a bundle write
contains:

```text
manifest.json
provenance/source.json
provenance/environment.json
provenance/software.json
provenance/hardware.json
recipes/{simulation,projection,scientific-clean,gallery-crisp}.json
metadata/master-pattern.json
metadata/orientation-candidates.json
products/projected.npy
products/acquisition-corrected.npy
products/stages/*.tif
products/{scientific-clean,gallery-crisp}.tif
products/{scientific-clean,gallery-crisp}.png
products/preview.png
diagnostics/metrics.json
diagnostics/warnings.json
diagnostics/timings.json
diagnostics/resources.json
decisions/orientation.json
decisions/links.json
```

Assert TIFF and PNG are grayscale uint16, preview is uint8, JSON is canonical,
manifest checksums match bytes on disk, and writing into an existing completed
bundle fails rather than mixing runs. Every uint16 export records the source
float product ID plus quantization scale, offset, black/white points, and
clipping fractions. The named acquisition-corrected product is the output of
the background model/correction before aesthetic local contrast or detail.

Run:

```bash
uv run pytest tests/unit/test_diagnostics.py tests/unit/test_artifact_bundle.py -q
```

Expected: FAIL.

### Step 2: Implement atomic, content-addressed bundles

Write to `<run-id>.partial`, fsync/close, then rename to `<run-id>`. Compute the
run ID from source, recipe, and software identities, not wall-clock time. Store
timestamps as provenance only. Quantize to uint16 only at export boundaries;
retain float32 `.npy` for scientific products and stages.

The manifest inventories every bundle file except itself; its own checksum is
reported externally by the CLI. Refuse to overwrite a completed bundle. A
stale `.partial` directory may be removed only with explicit `--resume-clean`
and must first be renamed to a timestamped `.abandoned` evidence directory.
For reproduction comparisons, exclude only timestamps, elapsed/resource
measurements, absolute local paths, and the resulting manifest checksum; list
those exclusions in the manifest schema rather than in test code alone.

Run:

```bash
uv run pytest tests/unit/test_diagnostics.py tests/unit/test_artifact_bundle.py -q
uv run pytest -m "not slow and not gpu" -q
```

Expected: PASS.

### Step 3: Commit

Update `KIKU-T006`, then:

```bash
git add src/kikuchi_lab/diagnostics src/kikuchi_lab/artifacts tests docs
git commit -m "feat: add diagnostic artifact bundles"
```

## Task 7: Define a symmetry-distinct forsterite candidate set

**Files:**

- Create: `src/kikuchi_lab/orientations/__init__.py`
- Create: `src/kikuchi_lab/orientations/candidates.py`
- Create: `recipes/proof/forsterite-candidates.yml`
- Create: `tests/scientific/test_orientation_candidates.py`
- Create: `docs/decisions/0002-forsterite-proof-candidate-set.md`
- Modify: `docs/work/KIKU-T007.md`

### Step 1: Write the failing crystallographic test

Load 9-12 explicit Bunge crystal-to-sample candidates and the forsterite `mmm`
point group. Reduce each orientation by crystal symmetry and assert no pair is
equivalent within 0.01 degrees. Assert deterministic IDs/order, finite angles,
one stated reference-frame convention, and a documented zone-axis/compositional
intent for each candidate.

Run `uv run pytest tests/scientific/test_orientation_candidates.py -q`.
Expected: FAIL on missing candidate module.

### Step 2: Implement and document the bounded set

Use orix symmetry operators only inside this helper; return project
`Orientation` values. Record the reduction algorithm, tolerance, candidate
generation rationale, and non-goal of exhaustive orientation sampling in
decision 0002. Run the focused and fast suites. Expected: PASS.

### Step 3: Commit

Complete `KIKU-T007`, validate links, and commit with
`feat: add symmetry-distinct forsterite candidates`.

## Task 8: Render the deterministic proof comparison

**Files:**

- Create: `src/kikuchi_lab/workflows/__init__.py`
- Create: `src/kikuchi_lab/workflows/proof.py`
- Create: `src/kikuchi_lab/artifacts/contact_sheet.py`
- Create: `recipes/proof/forsterite-proof.yml`
- Create: `tests/integration/test_proof_workflow.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `docs/work/KIKU-T008.md`

### Step 1: Write the failing proof test

Inject a canonical master product so the test never invokes WebGPU. Assert one
projection per Task 7 candidate, one fixed detector/processing comparison
contract, deterministic candidate order, comparable metrics, readable ID/Euler
labels on the contact sheet, and an explicit `awaiting-human-selection` run
state. Assert the workflow does not choose a winner.

Run `uv run pytest tests/integration/test_proof_workflow.py -q`.
Expected: FAIL.

### Step 2: Implement proof orchestration

Add `kikuchi-lab proof --recipe recipes/proof/forsterite-proof.yml
--master-product local/master-patterns/forsterite-proof/product.npz --output
local/runs`.
It writes the bundle, contact sheet, per-candidate images/metrics, and candidate
metadata, then exits successfully with the awaiting-selection state. Run the
focused and fast suites. Expected: PASS.

### Step 3: Commit

Complete `KIKU-T008` and commit with `feat: add deterministic proof rendering`.

## Task 9: Validate and record the human orientation choice

**Files:**

- Create: `src/kikuchi_lab/orientations/selection.py`
- Create: `tests/unit/test_orientation_selection.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `docs/work/KIKU-T009.md`

### Step 1: Write the failing selection tests

Test that a selection must reference an existing proof run and candidate ID,
include a nonblank human rationale and author field, preserve the exact
orientation/geometry/metric references, and refuse replacement without
creating a new superseding artifact with a reason. The selection is a separate
immutable, content-addressed decision bundle under `local/decisions/`; it
references the sealed proof bundle ID, external manifest checksum, candidate,
and metrics checksums. Assert it never changes the proof bundle, its manifest,
images, metrics, or state. A status query may derive
`orientation-selected` from the separate reference without persisting it into
the proof bundle.

Run `uv run pytest tests/unit/test_orientation_selection.py -q`.
Expected: FAIL.

### Step 2: Implement the schema and CLI

Add `kikuchi-lab select-orientation --run local/runs/forsterite-proof
--candidate fo-01 --author Z --rationale "balanced central zone axis and edge
coverage" --output local/decisions`. Keep diagnostics advisory; no score may
populate this record automatically. A changed choice creates a new selection
artifact with `--supersedes <selection-id> --supersede-reason <reason>`; it
never overwrites either artifact. Run focused and fast suites. Expected: PASS.

### Step 3: Coordinator/user gate and commit

The coordinating agent opens the real proof contact sheet and presents it to
the user. Record the agreed candidate with concrete notes on zone-axis
placement, band coverage, edge balance, and retained fine detail. Then complete
`KIKU-T009` and commit `feat: record explicit orientation selection`.

## Task 10: Implement final rendering and recipe reproduction

**Files:**

- Create: `src/kikuchi_lab/workflows/final.py`
- Create: `recipes/gallery/forsterite-final.yml`
- Create: `tests/integration/test_final_workflow.py`
- Create: `tests/integration/test_recipe_reproduction.py`
- Modify: `src/kikuchi_lab/cli/main.py`
- Modify: `docs/work/KIKU-T010.md`

### Step 1: Write the failing final-workflow test

Using a small canonical projection and valid selection, assert the bundle
contains raw, acquisition-corrected, scientific-clean, and gallery-crisp float
products, all high-bit-depth exports, diagnostics, warnings, decisions, and a
validated manifest. Assert both styled products reference one immutable source
projection.

Run `uv run pytest tests/integration/test_final_workflow.py -q`.
Expected: FAIL.

### Step 2: Implement the final command

Add `kikuchi-lab render-final --recipe
recipes/gallery/forsterite-final.yml --selection
local/decisions/forsterite-selection/selection.json --output
local/runs`. It must refuse an awaiting-selection proof run and must validate
the completed bundle before returning success. Run the focused test. Expected:
PASS.

### Step 3: Write the failing reproduction test

Render the same small source/selection/recipe twice into separate temporary
roots. Assert identical IDs, float arrays, uint16 bytes, and manifest inventory
after excluding only the schema-declared nondeterministic fields from Task 6.
Also test the documented tolerance comparison for platform-dependent GPU source
arrays without weakening deterministic CPU processing checks.

Run `uv run pytest tests/integration/test_recipe_reproduction.py -q`.
Expected: FAIL until comparison/reproduction support exists; then implement the
minimum support and rerun all fast tests.

### Step 4: Commit

Complete `KIKU-T010` and commit `feat: add reproducible final rendering`.

## Task 11: Run the real M2 production pass and visual acceptance

**Files:**

- Create: `docs/acceptance/forsterite-milestone.md`
- Modify: `recipes/gallery/forsterite-final.yml`
- Modify: `docs/work/KIKU-T011.md`

This is a coordinator-led evidence task, not a delegated implementation task.

### Step 1: Run automated and GPU gates

```bash
uv run ruff check src tests
uv run pytest -m "not slow and not gpu" -q
uv run pytest -m "gpu and slow" -q
```

Expected: all pass under arm64 Python on the local M2.

### Step 2: Generate proof and final products

Use the Task 3 production master pattern and Task 9 selection. The initial
target is a supersampled detector projection with final long edge at least 2048
px. Increase `halfw`, supersampling, or trajectories only when proof diagnostics
identify that limit; record each change in the recipe and run decision ledger.

Runtime amendment (2026-07-13): follow
[ADR 0004](../../decisions/0004-bounded-observable-simulation-ladder.md).
Begin with the one-bin resolution-only 501 rung, retain a durable chunk journal,
and promote only one expensive simulation control after review. Do not launch
the twenty-bin production target implicitly; it requires explicit multi-bin
approval and remains non-resumable with ebsdsim 0.1.8.

### Step 3: Review with the user

Present the raw projection, acquisition-corrected product, all stage
intermediates, scientific-clean image, gallery-crisp image, and contact sheet at
100% and fit-to-window. Record pass/fail and notes for believable EBSD form,
smooth band interiors, crisp edges without etched halos, retained zone-axis
detail, absence of clipping/ringing/tiling/resampling artifacts, compelling
composition, meaningful scientific/gallery distinction, and successful recipe
reproduction.

If a criterion fails, run one bounded source-resolution or processing
experiment at a time, preserve before/after evidence, and update the recipe
only through a linked decision. Complete `KIKU-T011` only after user acceptance,
then commit `docs: record forsterite visual acceptance`.

## Task 12: Park future work, close the feature, and review the branch

**Files:**

- Create: `docs/incubator/README.md`
- Create: `docs/incubator/matched-kinematical-dynamical.md`
- Create: `docs/incubator/orientation-gallery.md`
- Create: `docs/incubator/phase-general-simulation.md`
- Create: `docs/incubator/ebsd-map-orientations.md`
- Create: `docs/incubator/detector-acquisition-model.md`
- Create: `docs/incubator/print-geometry.md`
- Create: `docs/incubator/pattern-processing-contracts.md`
- Create: `docs/incubator/ebsdx-integration.md`
- Create: `docs/incubator/sht-spherical-harmonic.md`
- Create: `docs/incubator/emsoft-cross-validation.md`
- Create: `docs/incubator/independent-engine.md`
- Create: `docs/incubator/decision-state-diagnostics.md`
- Modify: `docs/work/KIKU-T012.md`
- Modify: `docs/work/KIKU-F001.md`

### Step 1: Write and validate incubator records

Each record includes motivation, current evidence, dependencies, unresolved
questions, linked decisions/experiments, one concise promotion trigger, and
explicit present non-goals. These records do not expand milestone acceptance.

### Step 2: Run closure gates

```bash
uv run ruff check src tests
uv run pytest -m "not slow and not gpu" -q
uv run pytest -m "gpu and slow" -q
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
```

Complete `KIKU-T012`, then `KIKU-F001`, only when Tasks 1-11 and their evidence
pass. Keep `KIKU-E001` active for later companion work.

### Step 3: Broad review and final commit

Request a fresh broad specification/code/evidence review. Fix important
findings and rerun gates. Commit `feat: deliver exceptional forsterite pattern
milestone`. Do not push. Hand off the local bundle path, preview, tests, GPU
evidence, tracker state, branch, and commit IDs.

## Plan self-review checklist

- Every approved milestone acceptance criterion maps to Tasks 1-12.
- The durable ebsdsim NPZ remains intact; both hemispheres enter our canonical
  product before projection.
- Upstream types do not cross project-owned adapter boundaries.
- Proof, selection, and final rendering are separate reproducible operations.
- Scientific-clean and gallery-crisp products share one immutable projection.
- All code tasks begin with a focused failing test and name the expected
  failure.
- GPU/slow gates are isolated from fast contract tests.
- Large products remain ignored under `local/`; tracked evidence stays small.
- Parked directions have promotion gates but are not active milestone scope.
- No step configures a remote or pushes the repository.
