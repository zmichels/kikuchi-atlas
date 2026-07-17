from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.model.recipes import Orientation


ROOT = Path(__file__).parents[2]
TRACKED_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"


def test_series_recipe_is_phase_general_and_orientation_is_data() -> None:
    from kikuchi_lab.art_products.hemisphere_recipe import (
        load_hemisphere_series_recipe,
    )

    recipe = load_hemisphere_series_recipe(TRACKED_RECIPE)

    assert recipe.phase_order == (
        "ice-ih",
        "forsterite",
        "quartz",
        "zircon",
        "titanite",
    )
    assert recipe.orientation.euler_bunge_deg == (17.0, 31.0, 43.0)
    assert recipe.orientation.frame == "crystal_to_sample"
    assert recipe.treatments["standard"].arc_width_scale == 1.0
    assert recipe.treatments["wide"].arc_width_scale == 1.15
    assert tuple(recipe.reflector_recipes) == recipe.phase_order


def test_orientation_changes_series_not_reflector_recipe_identity() -> None:
    from kikuchi_lab.art_products.hemisphere_recipe import (
        load_hemisphere_series_recipe,
    )

    recipe = load_hemisphere_series_recipe(TRACKED_RECIPE)
    changed = replace(
        recipe,
        orientation=Orientation((1.0, 2.0, 3.0), "crystal_to_sample"),
    )

    assert changed.series_id != recipe.series_id
    assert changed.reflector_recipes == recipe.reflector_recipes


def test_composition_exposes_shared_selection_and_render_policy() -> None:
    from kikuchi_lab.art_products.hemisphere_recipe import (
        load_hemisphere_series_recipe,
    )

    recipe = load_hemisphere_series_recipe(TRACKED_RECIPE)
    composition = recipe.composition_for("quartz")

    assert composition.phase_slug == "quartz"
    assert composition.orientation == recipe.orientation
    assert composition.path_allocation == {
        "dominant": 4,
        "secondary": 4,
        "fine": 3,
    }
    assert composition.stroke_widths_mm["dominant"] == (4.8, 4.2, 3.6, 3.1)
    assert composition.projection_boundary["outer_diameter_mm"] == 132.0
    assert composition.include_nodes is False
    assert composition.spatial_filter == "none"
    assert composition.recipe_id.startswith("hemisphere-composition-")


def test_series_recipe_rejects_phase_specific_override_fields(tmp_path: Path) -> None:
    from kikuchi_lab.art_products.hemisphere_recipe import (
        load_hemisphere_series_recipe,
    )

    payload = yaml.safe_load(TRACKED_RECIPE.read_text(encoding="utf-8"))
    payload["phase_overrides"] = {"quartz": {"orientation": [1, 2, 3]}}
    path = tmp_path / "series.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="fields differ from the schema"):
        load_hemisphere_series_recipe(path)


@pytest.mark.parametrize(
    ("treatment", "scale"),
    [("standard", 1.01), ("wide", 1.2)],
)
def test_series_recipe_rejects_treatment_scale_drift(
    tmp_path: Path,
    treatment: str,
    scale: float,
) -> None:
    from kikuchi_lab.art_products.hemisphere_recipe import (
        load_hemisphere_series_recipe,
    )

    payload = yaml.safe_load(TRACKED_RECIPE.read_text(encoding="utf-8"))
    payload["treatments"][treatment]["arc_width_scale"] = scale
    path = tmp_path / "series.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="arc_width_scale"):
        load_hemisphere_series_recipe(path)
