from pathlib import Path

import numpy as np

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _enumerate_reflectors,
    _phase_from_record,
    _reflection_catalog,
    _select_reflectors,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"


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
    reflectors = _enumerate_reflectors(
        _phase_from_record(load_structure_record(SOURCE)), recipe
    )
    selected = _select_reflectors(
        reflectors, recipe.master_relative_factor, recipe.energy_kev
    )
    catalog = _reflection_catalog(
        selected, recipe, threshold=recipe.master_relative_factor
    )
    assert catalog["units"] == {"dspacing": "angstrom", "theta": "radian"}
    assert catalog["retained_count"] == selected.size
    assert all(
        set(row)
        == {"hkl", "dspacing_angstrom", "structure_factor_abs", "theta_radian"}
        for row in catalog["reflections"]
    )
