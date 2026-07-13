from pathlib import Path

from kikuchi_lab.diagnostics.simulation_work import estimate_simulation_work
from kikuchi_lab.sources.ebsdsim_adapter import load_simulation_recipe
from kikuchi_lab.sources.structure import load_structure_record, materialize_simulation_cif


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"


def test_estimate_simulation_work_exposes_finite_forsterite_bounds(tmp_path):
    source = load_structure_record(SOURCE)
    recipe = load_simulation_recipe(ROOT / "recipes/proof/forsterite-simulation.yml")
    simulation_cif = materialize_simulation_cif(source, tmp_path / "forsterite.simulation.cif")

    estimate = estimate_simulation_work(simulation_cif, recipe)

    assert estimate.to_dict() == {
        "grid_size": 257,
        "n_k": 17003,
        "n_reflections": 2361,
        "chunks_per_bin": 2126,
        "maximum_energy_bins": 1,
        "minimum_bins_before_relative_stop": 1,
        "smith_rank": 8,
        "work_proxy_per_bin": 321152664,
        "maximum_work_proxy": 321152664,
        "checkpoint_policy": "atomic-complete-run",
        "resumable_within_run": False,
    }


def test_production_estimate_makes_twenty_bin_upper_bound_explicit(tmp_path):
    source = load_structure_record(SOURCE)
    recipe = load_simulation_recipe(ROOT / "recipes/production/forsterite-simulation.yml")
    simulation_cif = materialize_simulation_cif(source, tmp_path / "forsterite.simulation.cif")

    estimate = estimate_simulation_work(simulation_cif, recipe)

    assert estimate.n_k == 63701
    assert estimate.n_reflections == 9773
    assert estimate.chunks_per_bin == 7963
    assert estimate.maximum_energy_bins == 20
    assert estimate.minimum_bins_before_relative_stop == 2
    assert estimate.maximum_work_proxy == estimate.work_proxy_per_bin * 20
    assert not estimate.resumable_within_run
