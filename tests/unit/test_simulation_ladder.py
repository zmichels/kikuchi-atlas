from pathlib import Path

from kikuchi_lab.sources.ebsdsim_adapter import load_simulation_recipe


ROOT = Path(__file__).parents[2]


def test_resolution_501_rung_changes_only_resolution_and_observability():
    proof = load_simulation_recipe(ROOT / "recipes/proof/forsterite-simulation.yml")
    rung = load_simulation_recipe(
        ROOT / "recipes/benchmarks/forsterite-resolution-501.yml"
    )

    differences = {
        name: (getattr(proof, name), getattr(rung, name))
        for name in proof.__dataclass_fields__
        if getattr(proof, name) != getattr(rung, name)
    }

    assert differences == {"halfw": (128, 250), "verbosity": (0, 2)}
    assert int(rung.voltage_kv / rung.energy_binwidth_kev) == 1
