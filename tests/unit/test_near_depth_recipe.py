from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kikuchi_lab.near_depth import (
    StrokeStyle,
    load_near_depth_recipe,
)


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes" / "presentation" / "ice-ih-near-depth-stepped.yml"


def test_ice_treatment_recipe_loads_exact_approved_parameters() -> None:
    recipe = load_near_depth_recipe(RECIPE)

    assert recipe.source_kinematical_recipe == (
        "../kinematical/ice-ih-oxygen-quiet-proof.yml"
    )
    assert recipe.expected_kinematical_recipe_id == "recipe-8aa79ffa759eb05b"
    assert recipe.overlap_relative_factor == 0.22
    assert recipe.weight_exponent == 2.0
    assert recipe.normalization_percentile == 99.5
    assert recipe.optical_depth_gain == 0.28
    assert recipe.luminance_ceiling == 0.985
    assert recipe.center == StrokeStyle(0.22, 0.42, 0.62, 0.82, 0.38)
    assert recipe.boundary == StrokeStyle(0.34, 0.38, 0.48, 0.82, 0.30)
    assert recipe.figure_size_px == 2400
    assert recipe.background_color == "#101519"
    assert recipe.recipe_id.startswith("recipe-")
    assert recipe.to_dict()["source_kinematical_recipe"] == (
        "../kinematical/ice-ih-oxygen-quiet-proof.yml"
    )


def test_treatment_recipe_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload["blur_radius"] = 1
    path = tmp_path / "invalid.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="fields differ"):
        load_near_depth_recipe(path)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("overlap", "relative_factor"), 0.0, "relative_factor"),
        (("overlap", "normalization_percentile"), 101.0, "percentile"),
        (("optical_depth", "luminance_ceiling"), 1.0, "luminance_ceiling"),
        (("center", "alpha"), 1.1, "alpha"),
        (("boundary", "casing_width_pt"), 0.0, "casing_width_pt"),
    ],
)
def test_treatment_recipe_rejects_invalid_ranges(
    tmp_path: Path,
    path: tuple[str, str],
    value: float,
    message: str,
) -> None:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload[path[0]][path[1]] = value
    target = tmp_path / "invalid.yml"
    target.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_near_depth_recipe(target)


def test_treatment_recipe_requires_relative_base_recipe_path(tmp_path: Path) -> None:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload["source_kinematical_recipe"] = "/tmp/base.yml"
    target = tmp_path / "invalid.yml"
    target.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="relative path"):
        load_near_depth_recipe(target)
