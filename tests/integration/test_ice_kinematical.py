from __future__ import annotations

from pathlib import Path

import pytest

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


def test_ice_kinematical_rejects_a_non_ice_source_even_with_ice_reflector_recipe(
    tmp_path: Path,
) -> None:
    altered = tmp_path / "kinematical.yml"
    altered.write_text(
        RECIPE.read_text(encoding="utf-8").replace(
            "source_record: ../../phases/ice-ih/source.yml",
            f"source_record: {ROOT / 'phases/forsterite/source.yml'}",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tracked Ice source"):
        simulate_ice_kinematical(altered)
