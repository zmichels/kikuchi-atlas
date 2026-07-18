from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.reflector_globe.recipes import load_reflector_ridge_recipe


ROOT = Path(__file__).parents[2]


def test_ice_ridge_recipe_has_four_raised_physical_tiers() -> None:
    recipe = load_reflector_ridge_recipe(ROOT / "recipes/globes/ice-ih-reflector-ridges.yml")

    assert recipe.geometry.base_diameter_mm == 80.0
    assert recipe.geometry.maximum_relief_mm == 3.0
    assert recipe.geometry.direction == "raised_outward"
    assert tuple(recipe.tiers) == (1, 2, 3, 4)
    assert recipe.tiers[4].height_mm == 3.0
    assert recipe.selection.eligibility_min_weight == 0.08
    assert recipe.selection.tie_policy == "keep_equal_weights_together"
    assert recipe.recipe_id.startswith("reflector-ridge-recipe-")


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("direction: groove_inward", "raised_outward"),
        ("maximum_relief_mm: 0", "positive"),
        ("height_mm: 3.1", "maximum_relief_mm"),
        ("edge_fillet_fraction: 0", "edge_fillet_fraction"),
        ("cohort_count: 3", "cohort_count"),
    ],
)
def test_loader_rejects_nonphysical_or_noncanonical_recipe(
    tmp_path: Path, text: str, match: str
) -> None:
    source = (ROOT / "recipes/globes/ice-ih-reflector-ridges.yml").read_text(encoding="utf-8")
    field, value = text.split(": ", 1)
    path = tmp_path / "invalid.yml"
    path.write_text(source.replace(f"{field}: ", f"{field}: {value} # ", 1), encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        load_reflector_ridge_recipe(path)


def test_loader_rejects_unknown_keys(tmp_path: Path) -> None:
    source = (ROOT / "recipes/globes/ice-ih-reflector-ridges.yml").read_text(encoding="utf-8")
    path = tmp_path / "invalid.yml"
    path.write_text(source + "unexpected: true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown keys"):
        load_reflector_ridge_recipe(path)
