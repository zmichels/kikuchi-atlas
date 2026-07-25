# Pyrope Atlas Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the 298.15 K COD 9000435 Mg3Al2Si3O12 pyrope structure into the Kikuchi Atlas with the same nine registered product roles as calcite and orthoenstatite.

**Architecture:** Preserve the original COD CIF and create one deterministic simulation CIF whose Mg, Si, and O Uiso values are trace-derived from the reported anisotropic tensors. Reuse the existing source verification, direct-reflector, kinematical, near-depth, animation, printable-globe, Atlas registry, release-audit, and repo-native tracking contracts without adding engine behavior.

**Tech Stack:** Python 3.12, PyCifRW, diffpy.structure, diffsims, kikuchipy, NumPy, trimesh, ffmpeg, pytest, YAML.

## Global Constraints

- Do not remove, rename, or replace any existing phase or product.
- Preserve the original COD 9000435 bytes with SHA-256 `90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932`.
- Preserve formula `Mg3Al2Si3O12`, space group 230 `I a -3 d`, 298.15 K, 11.456 angstrom cubic cell, implicit full occupancies, and site multiplicities `[24, 16, 24, 96]`.
- Retain Al Uiso `0.00507`; derive Mg, Si, and O Uiso as `(U11 + U22 + U33) / 3`, yielding `0.011836666666666667`, `0.0036133333333333334`, and `0.00596` square angstrom.
- Preserve the source CIF's scientific-community attribution-use notice and original Meagher citation.
- Publish no Atlas product entry until its media, preview, bundle, provenance, and recipe paths exist.
- Describe the phase as one pure Mg garnet endmember reference, not all garnets, natural pyrope solid solutions, a pressure series, or indexing/orientation validation.
- Preserve unrelated dirty-worktree changes; stage or commit only pyrope-scoped files if the user later requests integration.

---

### Task 1: Promote the original and derivative pyrope source with a failing test

**Files:**
- Create: `tests/adapters/test_pyrope_source.py`
- Create: `phases/pyrope/COD-9000435-original.cif`
- Create: `phases/pyrope/COD-9000435-isotropic-u.cif`
- Create: `phases/pyrope/source.yml`

**Interfaces:**
- Consumes: `load_structure_record(path)` and `verify_structure(record)`.
- Produces: a verified derivative `StructureRecord` whose `simulation_setting` binds the original CIF SHA-256 and Uiso derivation.

- [x] **Step 1: Write the failing source test**

```python
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.kinematical.kikuchipy_adapter import _phase_from_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/pyrope/source.yml"
ORIGINAL = ROOT / "phases/pyrope/COD-9000435-original.cif"
ORIGINAL_SHA256 = "90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pyrope_derivative_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-9000435-isotropic-U"
    assert record.formula == "Mg3Al2Si3O12"
    assert record.space_group_number == 230
    assert record.setting == "I a -3 d"
    assert record.simulation_setting["temperature_k"] == 298.15
    assert record.simulation_setting["target_site_multiplicities"] == [24, 16, 24, 96]
    assert record.simulation_setting["source_setting"] == "I a -3 d"
    assert record.simulation_setting["target_setting"] == "I a -3 d"
    assert record.simulation_setting["target_lattice_from_source"] == ["a", "b", "c"]
    assert record.simulation_setting["target_fractional_from_source"] == ["x", "y", "z"]
    assert record.simulation_setting["derived_from_sha256"] == ORIGINAL_SHA256
    assert record.simulation_setting["u_iso_derivation"] == (
        "U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal cubic axes"
    )
    assert verified.site_u_iso_angstrom_sq == pytest.approx(
        (0.011836666666666667, 0.00507, 0.0036133333333333334, 0.00596)
    )
    assert verified.missing_thermal_factor_labels == ()
    assert verified.occupancy_source == "implicit CIF default 1.0"
    assert _sha256(ORIGINAL) == ORIGINAL_SHA256
    assert len(_phase_from_record(record).structure) == 160
```

- [x] **Step 2: Run the test and confirm RED**

Run:

```bash
uv run pytest -q tests/adapters/test_pyrope_source.py
```

Expected: fail with `FileNotFoundError` because `phases/pyrope/source.yml` does not exist.

- [x] **Step 3: Add the original and deterministic derivative CIFs**

Retrieve the original from `https://www.crystallography.net/cod/9000435.cif` and reject it unless its SHA-256 is the pinned digest above. Create the derivative by retaining the original header, publication fields, cell, symmetry loop, coordinates, and related-entry loop; add a derivative comment binding the original SHA-256; remove the anisotropic loop; and replace the atom loop with:

```cif
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_U_iso_or_equiv
Mg 0.12500 0.00000 0.25000 0.011836666666666667
Al 0.00000 0.00000 0.00000 0.00507
Si 0.00000 0.25000 0.37500 0.0036133333333333334
O  0.03280 0.05030 0.65340 0.00596
```

The derivative data block must be `data_9000435_isotropic_u`. Its source record must use:

```yaml
schema_version: 1
identifier: COD-9000435-isotropic-U
cif: COD-9000435-isotropic-u.cif
uri: https://www.crystallography.net/cod/9000435.cif
page_uri: https://www.crystallography.net/cod/9000435.html
license: COD attribution-use notice
phase:
  name: pyrope
  formula: Mg3Al2Si3O12
  space_group_number: 230
  setting: "I a -3 d"
  lattice_angstrom: [11.456, 11.456, 11.456, 90.0, 90.0, 90.0]
simulation_setting:
  temperature_k: 298.15
  source_setting: "I a -3 d"
  target_setting: "I a -3 d"
  target_lattice_from_source: [a, b, c]
  target_fractional_from_source: [x, y, z]
  target_site_multiplicities: [24, 16, 24, 96]
  derived_from_identifier: COD-9000435
  derived_from_sha256: 90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932
  u_iso_derivation: U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal cubic axes
  derivative_unchanged_from_original: [coordinates, occupancies, cell_values, symmetry_operations]
```

Add the derivative SHA-256, Meagher citation, all four sites, the standard `B_iso = 8 * pi^2 * U_iso` policy with `missing: reject`, and the source-specific attribution text.

- [x] **Step 4: Run the source test and confirm GREEN**

Run:

```bash
uv run pytest -q tests/adapters/test_pyrope_source.py
```

Expected: `1 passed`.

---

### Task 2: Add parity recipes with a failing recipe contract

**Files:**
- Modify: `tests/unit/test_atlas_extension_parity_recipes.py`
- Create: `recipes/reflectors/pyrope-catalog.yml`
- Create: `recipes/reflectors/pyrope-art-bands.yml`
- Create: `recipes/kinematical/pyrope-001-atlas-parity-master.yml`
- Create: `recipes/presentation/pyrope-near-depth-atlas-parity.yml`

**Interfaces:**
- Consumes: `phases/pyrope/source.yml`.
- Produces: recipe paths accepted by the direct catalog, parity, kinematical, and near-depth builders.

- [x] **Step 1: Add pyrope to the parameterized parity recipe test**

Add this pair to `PARITY_RECIPES`:

```python
(
    ROOT / "recipes/kinematical/pyrope-001-atlas-parity-master.yml",
    ROOT / "recipes/presentation/pyrope-near-depth-atlas-parity.yml",
),
```

- [x] **Step 2: Run the test and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_extension_parity_recipes.py
```

Expected: fail because the pyrope recipes do not exist.

- [x] **Step 3: Add the four recipes**

Use these exact direct-art settings:

```yaml
# recipes/reflectors/pyrope-art-bands.yml
schema_version: 1
name: pyrope-direct-art-reflectors
source_record: ../../phases/pyrope/source.yml
energy_kev: 20.0
reflections:
  min_dspacing_angstrom: 0.7
  scattering_params: xtables
  candidate_relative_factor: 0.03
art_weight:
  exponent: 2.0
  eligibility_min_weight: 0.08
```

```yaml
# recipes/reflectors/pyrope-catalog.yml
schema_version: 1
source_record: phases/pyrope/source.yml
energy_kev: 20.0
min_dspacing_angstrom: 0.7
scattering_params: xtables
source_master_relative_factor: 0.03
selection_relative_factor: 0.18
weight_exponent: 2.0
eligibility_min_weight: 0.10
tie_policy: keep_equal_weights_together
cohort_count: 4
```

Create `pyrope-001-atlas-parity-master.yml` with the exact detector, orientation, reflection, master, tone, figure-size, promoted-style, and balanced/quiet values from the approved 20 keV parity contract:

```yaml
schema_version: 1
name: pyrope-001-atlas-parity-master
source_record: ../../phases/pyrope/source.yml
energy_kev: 20.0
orientation: {euler_bunge_deg: [0.0, 0.0, 0.0], frame: crystal_to_sample, zone_axis_uvw: [0, 0, 1]}
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
reflections: {min_dspacing_angstrom: 0.7, scattering_params: xtables, master_relative_factor: 0.03}
master: {half_size: 512, hemisphere: both, scaling: square}
tone: {percentiles: [0.5, 99.85], asinh_scale: 7.0}
figure_size_px: 2400
promoted_style: quiet
styles:
  - {name: balanced, overlay_relative_factor: 0.14, line_alpha: 0.54, line_width_pt: 0.36}
  - {name: quiet, overlay_relative_factor: 0.22, line_alpha: 0.62, line_width_pt: 0.42}
```

Load that recipe to obtain its content-derived `recipe_id`, then bind the exact emitted ID in `pyrope-near-depth-atlas-parity.yml` with overlap factor `0.22`, exponent `2.0`, normalization percentile `99.5`, optical-depth gain `0.38`, luminance ceiling `0.985`, disabled center, boundary factor `0.50`, width `0.38`, alpha `0.50`, casing width `0.98`, casing alpha `0.36`, figure size `2400`, and background `#101519`.

- [x] **Step 4: Confirm recipe GREEN**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_extension_parity_recipes.py
```

Expected: all parameterized parity recipes pass.

---

### Task 3: Build scientific intermediates and direct templates

**Files:**
- Create locally: `local/atlas-expansion/pyrope/**`

**Interfaces:**
- Consumes: the verified source and four recipes.
- Produces: immutable direct catalog, parity report, kinematical master, near-depth bundle, reflector catalog, and four orientation template bundles.

- [x] **Step 1: Build the direct catalog and bounded parity smoke**

Run:

```bash
uv run kikuchi-lab build-direct-art-catalog \
  --recipe recipes/reflectors/pyrope-art-bands.yml \
  --output local/atlas-expansion/pyrope/direct-catalog

uv run kikuchi-lab validate-reflector-parity \
  --recipe recipes/reflectors/pyrope-art-bands.yml \
  --output local/atlas-expansion/pyrope/parity \
  --timeout-seconds 90
```

Require exact HKL, d-spacing, normal, strength, Bragg-angle, weight, and provenance parity plus one 65-by-65 smoke master.

- [x] **Step 2: Build the kinematical and near-depth bundles**

Run:

```bash
uv run kikuchi-lab render-kinematical \
  --recipe recipes/kinematical/pyrope-001-atlas-parity-master.yml \
  --output local/atlas-expansion/pyrope/kinematical

uv run kikuchi-lab render-kinematical-depth \
  --recipe recipes/presentation/pyrope-near-depth-atlas-parity.yml \
  --output local/atlas-expansion/pyrope/near-depth
```

Record the emitted run IDs, canonical master product ID, array SHA-256, and file SHA-256 for the relief recipe and acceptance document.

- [x] **Step 3: Build the four orientation templates**

Resolve and pass the single emitted direct-art catalog JSON:

```bash
direct_runs=(local/atlas-expansion/pyrope/direct-catalog/direct-art-catalog-run-*)
(( ${#direct_runs} == 1 ))
uv run python scripts/render_phase_art_templates.py \
  --phase pyrope \
  --catalog "${direct_runs[1]}/art-band-catalog.json" \
  --output local/atlas-expansion/pyrope/templates
```

Require the array cardinality check to pass; do not create or guess an
identifier. Require standard, azimuthal-60, tilt-plus-20, and oblique-high
bundles.

- [x] **Step 4: Build the four-cohort reflector catalog**

Run:

```bash
uv run kikuchi-lab reflectors build \
  --recipe recipes/reflectors/pyrope-catalog.yml \
  --output local/atlas-expansion/pyrope/reflector-catalog
```

If the `0.10` threshold does not yield four nonempty tied cohorts, change only `eligibility_min_weight`, rerun the recipe test, and record the pyrope-specific rationale.

---

### Task 4: Build animations and printable globes test-first

**Files:**
- Modify: `tests/unit/test_direct_reflector_rotation.py`
- Modify: `scripts/render_direct_reflector_rotation.py`
- Create: `recipes/globes/pyrope-reflector-ridges.yml`
- Create: `recipes/relief/pyrope-atlas-parity-kinematical-intensity.yml`

**Interfaces:**
- Consumes: the exact standard template bundle, reflector catalog, canonical master, and near-depth bundle.
- Produces: two validated MP4 products and two validated STL products.

- [x] **Step 1: Add the failing direct-rotation mapping test**

Add:

```python
def test_pyrope_rotation_source_points_to_published_standard_template() -> None:
    script_globals = runpy.run_path(str(ROOT / "scripts/render_direct_reflector_rotation.py"))
    source = ROOT / script_globals["PHASE_SOURCES"]["pyrope"]
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    assert source.is_dir()
    assert manifest["run_identity"]["phase_slug"] == "pyrope"
    assert manifest["run_identity"]["treatment"] == "standard"
```

Add `import json` to the test module before this test.

- [x] **Step 2: Confirm RED, add the exact mapping, and confirm GREEN**

Run:

```bash
uv run pytest -q tests/unit/test_direct_reflector_rotation.py
```

Expected RED: `KeyError: 'pyrope'`.

Resolve the standard bundle with:

```bash
standard_bundle=
for candidate in local/atlas-expansion/pyrope/templates/pyrope-hemisphere-standard-run-*; do
  [[ "$(jq -r '.run_identity.treatment' "$candidate/manifest.json")" == standard ]] && standard_bundle=$candidate
done
[[ -n "$standard_bundle" && -f "$standard_bundle/manifest.json" ]]
printf '%s\n' "$standard_bundle"
```

Add `"pyrope": Path("the printed repository-relative path")` to
`PHASE_SOURCES`. The literal must be the exact path printed above. Rerun the
test and require all tests in the file to pass.

- [x] **Step 3: Create the two globe recipes**

Create `pyrope-reflector-ridges.yml` with an 80 mm diameter, 3 mm maximum relief, subdivision 7 icosphere, raised-outward direction, `source_structure_id: COD-9000435-isotropic-U`, 20 keV, the reflector-catalog eligibility threshold, tied cohorts, the established four tier heights/widths, and `filament_fdm`.

Create `pyrope-atlas-parity-kinematical-intensity.yml` with the exact emitted canonical product ID and array/file hashes, 80 mm diameter, 1.2 mm maximum relief, subdivision 7 icosphere, 1/99 percentiles, gamma 1, bright-outward mapping, 0.8 mm spherical-Gaussian FWHM, 3 sigma cutoff, STL export, and filament-FDM context.

- [x] **Step 4: Render the two rotations**

Run:

```bash
kinematical_runs=(local/atlas-expansion/pyrope/kinematical/kinematical-run-*)
near_depth_runs=(local/atlas-expansion/pyrope/near-depth/near-depth-run-*)
(( ${#kinematical_runs} == 1 && ${#near_depth_runs} == 1 ))
uv run python scripts/render_direct_reflector_rotation.py \
  --phase pyrope --axis x \
  --output local/atlas-expansion/pyrope/direct-rotation \
  --workers 4

uv run python scripts/render_retained_near_depth_rotation.py \
  --phase-slug pyrope --phase-label Pyrope \
  --kinematical-run "${kinematical_runs[1]}" \
  --near-depth-run "${near_depth_runs[1]}" \
  --output local/atlas-expansion/pyrope/depth-rotation \
  --workers 4
```

Use the emitted run directories from Task 3. Require 144 frames, 1024 px, 12 fps, 12 seconds, and valid H.264 viewing copies.

- [x] **Step 5: Build both globes**

Run:

```bash
reflector_catalog_runs=(local/atlas-expansion/pyrope/reflector-catalog/reflector-catalog-build-*)
kinematical_runs=(local/atlas-expansion/pyrope/kinematical/kinematical-run-*)
(( ${#reflector_catalog_runs} == 1 && ${#kinematical_runs} == 1 ))
uv run kikuchi-lab reflector-globe build \
  --catalog "${reflector_catalog_runs[1]}/reflector-catalog.json" \
  --recipe recipes/globes/pyrope-reflector-ridges.yml \
  --output local/atlas-expansion/pyrope/reflector-globe

uv run kikuchi-lab relief globe build \
  --master-pattern "${kinematical_runs[1]}/products/canonical-kinematical-master.npz" \
  --recipe recipes/relief/pyrope-atlas-parity-kinematical-intensity.yml \
  --output local/atlas-expansion/pyrope/relief
```

Use only actual emitted run directories. Require both mesh-validation files to report `passed`, `watertight`, and `winding_consistent` as true; preserve all FDM warnings.

---

### Task 5: Publish pyrope with failing Atlas registry tests

**Files:**
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Modify: `docs/atlas/PHASE_REGISTRY.yml`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json`
- Regenerate: `docs/atlas/STRUCTURAL_SOURCE_ATTRIBUTION.md`

**Interfaces:**
- Consumes: verified local artifact paths from Tasks 3 and 4.
- Produces: a twelve-phase Atlas with 122 available products and 12 structural-source audit records.

- [x] **Step 1: Update expected counts and coverage, then confirm RED**

In `test_atlas.py`, add `pyrope` to the exact phase set and source-backed loop, assert family `garnet`, add `pyrope-direct-standard` to the hero set, rename the exact-coverage test to twelve phases, and change phase/product/type-card/product-card counts to 12/122.

In `test_atlas_release_metadata.py`, add `pyrope`, change source counts to 12, keep the CC0 count at 9, and rename the builder inventory test to twelve records.

Run:

```bash
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_release_metadata.py
```

Expected: fail because pyrope is not in the registries or generated source audit.

- [x] **Step 2: Add the phase and nine product records**

Add this phase:

```yaml
- slug: pyrope
  display_name: Pyrope (298.15 K Mg endmember)
  family: garnet
  formula: Mg3Al2Si3O12
  crystal_system: cubic
  source_status: tracked-source
  source_record: phases/pyrope/source.yml
  candidate_reference:
  scope_note: One 298.15 K Ia-3d pure Mg pyrope refinement with transparent Ueq derivation; not a universal garnet or natural solid-solution reference.
```

Register exactly nine products using actual existing paths:

1. `pyrope-direct-standard` as hero.
2. `pyrope-direct-azimuthal-60`.
3. `pyrope-direct-tilt-plus-20`.
4. `pyrope-direct-oblique-high`.
5. `pyrope-x-axis-rotation`.
6. `pyrope-reflector-ridge-globe`.
7. `pyrope-atlas-kinematical-master`.
8. `pyrope-atlas-retained-depth-x-axis`.
9. `pyrope-atlas-kinematical-intensity-relief`.

Match the existing family, tier, entrypoint, orientation, and claim-boundary captions for each product role. Do not register a path before checking its media, preview, bundle, provenance, and recipe files exist.

- [x] **Step 3: Regenerate release metadata and confirm GREEN**

Run:

```bash
uv run python scripts/build_release_metadata.py
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_release_metadata.py
```

Expected: all tests pass with 12 phases, 122 products, 12 sources, and 9 CC0-labelled source records.

---

### Task 6: Record acceptance and verify the complete pyrope slice

**Files:**
- Create: `docs/acceptance/pyrope-atlas-parity.md`
- Modify: `docs/atlas/REQUESTED_PHASE_EXPANSION.md`
- Modify: `docs/work/KIKU-F031.md`
- Modify: `docs/work/KIKU-T081.md`
- Create: `docs/work/KIKU-T084.md`

**Interfaces:**
- Consumes: exact source, run IDs, checksums, mesh validations, Atlas build, and tests.
- Produces: durable acceptance evidence and a validated done task while `KIKU-F031` remains active.

- [x] **Step 1: Verify manifest inventories and both meshes**

For every manifest under `local/atlas-expansion/pyrope`, verify each declared file exists and matches its recorded byte count and SHA-256. Verify both rotation exports against their recorded SHA-256 values. Require both mesh validations to pass with watertight and winding-consistent geometry, while copying FDM warnings into the acceptance note.

- [x] **Step 2: Write acceptance and tracker records**

Document the original and derivative hashes, Uiso derivation, source citation, exact build/run/product IDs, reflector counts, parity result, animation profiles, mesh results, FDM advisories, Atlas counts, and nonclaims in `pyrope-atlas-parity.md`.

Create `KIKU-T084` as a done child of `KIKU-F031` only after every acceptance criterion is satisfied. Add `KIKU-T084` symmetrically to the feature, add pyrope evidence to `KIKU-T081`, move pyrope from the candidate table to existing coverage, and leave the remaining source-intake task and feature active.

- [x] **Step 3: Run the final focused verification gate**

Run:

```bash
uv run python scripts/validate_work_items.py
uv run pytest -q \
  tests/adapters/test_pyrope_source.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_release_metadata.py \
  tests/unit/test_atlas_extension_parity_recipes.py \
  tests/unit/test_direct_reflector_rotation.py \
  tests/unit/test_retained_near_depth_rotation.py
uv run python scripts/build_atlas.py --output local/atlas-expansion/site
git diff --check
```

Expected: tracker validation passes; focused tests pass; Atlas reports 12 phases and 122 products; `git diff --check` is silent.

- [x] **Step 4: Record repository-wide non-pyrope test status**

Run the full suite once:

```bash
uv run pytest -q
```

Do not change unrelated product-catalog or reflector-catalog tests as part of pyrope. If the two previously observed unrelated failures remain, report them separately from the green pyrope acceptance gate with their exact test names and current pass/skip totals.
