from __future__ import annotations

from pathlib import Path

from kikuchi_lab.workflows.ice_kinematical import simulate_ice_kinematical


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"


def test_ice_kinematical_source_product_has_recipe_and_source_identity() -> None:
    simulation = simulate_ice_kinematical(RECIPE)
    metadata = simulation.master_stereographic.metadata

    assert metadata["source_id"].startswith("source-")
    assert metadata["recipe_id"].startswith("kinematical-recipe-")
    assert metadata["source_id"] in metadata["provenance_links"]
    assert metadata["recipe_id"] in metadata["provenance_links"]
