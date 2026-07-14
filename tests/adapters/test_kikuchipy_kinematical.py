from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _enumerate_reflectors,
    _phase_from_record,
    _reflection_catalog,
    _select_reflectors,
    simulate_kinematical_arrays,
)
from kikuchi_lab.projection.kikuchipy_adapter import (
    _to_kikuchipy_detector,
    _to_kikuchipy_rotation,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"


@pytest.fixture(scope="module")
def small_simulation():
    record = load_structure_record(SOURCE)
    recipe = replace(load_kinematical_recipe(RECIPE), half_size=32)
    simulation, context = simulate_kinematical_arrays(record, recipe)
    return recipe, simulation, context


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


def test_adapter_arrays_match_direct_kikuchipy_public_calls(small_simulation) -> None:
    recipe, simulation, context = small_simulation

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

    np.testing.assert_array_equal(
        simulation.master_stereographic.intensity, direct_stereo.data
    )
    np.testing.assert_array_equal(
        simulation.master_lambert.intensity, direct_lambert.data
    )
    np.testing.assert_array_equal(
        simulation.detector.intensity, np.asarray(direct_detector.data).squeeze()
    )


def test_adapter_context_keeps_upstream_products_private_and_complete(
    small_simulation,
) -> None:
    _, simulation, context = small_simulation

    assert set(context.overlay_simulators) == {"balanced", "quiet"}
    assert context.master_signal.data.shape == (2, 65, 65)
    assert context.lambert_signal.data.shape == (2, 65, 65)
    assert np.asarray(context.detector_signal.data).squeeze().shape == (1536, 2048)
    assert context.detector_geometry.detector.shape == (1536, 2048)
    assert set(simulation.reflector_catalog) == {"master", "overlays"}
