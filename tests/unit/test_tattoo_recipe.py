from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from kikuchi_lab.art_products.tattoo_recipe import TattooRecipe, load_tattoo_recipe


RECIPE = Path("recipes/art/ice-ih-tattoo.yml")


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "ice-ih-tattoo",
        "orientation": {
            "euler_bunge_deg": [17.0, 31.0, 43.0],
            "frame": "crystal_to_sample",
        },
        "artboard_size_mm": 145.0,
        "path_allocation": {"dominant": 4, "secondary": 4, "fine": 3},
        "stroke_widths_mm": {
            "dominant": [4.8, 4.2, 3.6, 3.1],
            "secondary": [2.5, 2.2, 1.9, 1.6],
            "fine": [1.2, 1.0, 0.8],
        },
        "great_circle_samples": 721,
        "crop_radius": 0.90,
        "redundancy_threshold_deg": 4.0,
        "score_weights": {
            "strength": 0.40,
            "angular_width": 0.15,
            "nonredundancy": 0.20,
            "coverage": 0.15,
            "zone_relationship": 0.10,
        },
        "coverage_sectors": 6,
        "zone_interior_margin_deg": 6.0,
        "projection_boundary": {
            "enabled": True,
            "role": "stereographic_hemisphere_boundary",
            "scientific_claim": "noncrystallographic_projection_primitive",
            "outer_diameter_mm": 132.0,
            "stroke_width_mm": 2.2,
            "ink": "#000000",
        },
        "include_nodes": False,
        "spatial_filter": "none",
        "primary_palette": {"ink": "#000000", "substrate": "skin"},
    }


def _write_recipe(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "tattoo.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _load(payload: dict[str, object]) -> TattooRecipe:
    with TemporaryDirectory() as directory:
        return load_tattoo_recipe(_write_recipe(Path(directory), payload))


def _set_path(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
    target = payload
    for field in path[:-1]:
        child = target[field]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = value


def test_tracked_tattoo_recipe_loads_the_approved_primary_contract() -> None:
    recipe = load_tattoo_recipe(RECIPE)

    assert isinstance(recipe, TattooRecipe)
    assert recipe.schema_version == 1
    assert recipe.name == "ice-ih-tattoo"
    assert recipe.orientation.euler_bunge_deg == (17.0, 31.0, 43.0)
    assert recipe.orientation.frame == "crystal_to_sample"
    assert recipe.artboard_size_mm == 145.0
    assert recipe.path_allocation == {"dominant": 4, "secondary": 4, "fine": 3}
    assert recipe.stroke_widths_mm == {
        "dominant": (4.8, 4.2, 3.6, 3.1),
        "secondary": (2.5, 2.2, 1.9, 1.6),
        "fine": (1.2, 1.0, 0.8),
    }
    assert recipe.great_circle_samples == 721
    assert recipe.crop_radius == 0.90
    assert recipe.redundancy_threshold_deg == 4.0
    assert recipe.score_weights == {
        "strength": 0.40,
        "angular_width": 0.15,
        "nonredundancy": 0.20,
        "coverage": 0.15,
        "zone_relationship": 0.10,
    }
    assert recipe.coverage_sectors == 6
    assert recipe.zone_interior_margin_deg == 6.0
    assert recipe.include_nodes is False
    assert recipe.spatial_filter == "none"
    assert recipe.primary_palette == {"ink": "#000000", "substrate": "skin"}
    assert recipe.recipe_id.startswith("tattoo-recipe-")


def test_tracked_recipe_has_exact_complete_hemisphere_boundary() -> None:
    recipe = load_tattoo_recipe(RECIPE)
    assert dict(recipe.projection_boundary) == {
        "enabled": True,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "outer_diameter_mm": 132.0,
        "stroke_width_mm": 2.2,
        "ink": "#000000",
    }
    assert "include_rim" not in recipe.to_dict()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("enabled", False),
        ("outer_diameter_mm", 131.9),
        ("stroke_width_mm", 2.1),
        ("role", "reflector"),
        ("scientific_claim", "crystallographic_reflector"),
        ("ink", "#111111"),
    ),
)
def test_recipe_rejects_nonapproved_boundary(field: str, value: object) -> None:
    payload = _payload()
    payload["projection_boundary"][field] = value
    with pytest.raises(ValueError, match="projection_boundary"):
        _load(payload)


def test_tattoo_recipe_collections_are_deeply_immutable() -> None:
    recipe = load_tattoo_recipe(RECIPE)

    with pytest.raises(FrozenInstanceError):
        recipe.artboard_size_mm = 152.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        recipe.path_allocation["dominant"] = 3  # type: ignore[index]
    with pytest.raises(TypeError):
        recipe.stroke_widths_mm["dominant"] = (5.0,)  # type: ignore[index]
    with pytest.raises(TypeError):
        recipe.score_weights["strength"] = 1.0  # type: ignore[index]
    with pytest.raises(TypeError):
        recipe.primary_palette["ink"] = "red"  # type: ignore[index]


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("schema_version",), 2, "schema_version"),
        (("schema_version",), True, "schema_version"),
        (("name",), "ice-tattoo", "name"),
        (("orientation", "euler_bunge_deg"), [17.0, 31.0, 42.0], "orientation"),
        (("orientation", "frame"), "sample_to_crystal", "orientation"),
        (("artboard_size_mm",), 144.0, "artboard_size_mm"),
        (("artboard_size_mm",), True, "artboard_size_mm"),
        (("path_allocation", "dominant"), 3, "path_allocation"),
        (("path_allocation", "fine"), True, "path_allocation"),
        (("stroke_widths_mm", "dominant"), [4.8, 4.2, 3.6, 3.0], "stroke_widths_mm"),
        (("stroke_widths_mm", "fine"), [1.2, 1.0], "stroke_widths_mm"),
        (("great_circle_samples",), 720, "great_circle_samples"),
        (("great_circle_samples",), True, "great_circle_samples"),
        (("crop_radius",), 0.91, "crop_radius"),
        (("redundancy_threshold_deg",), 3.9, "redundancy_threshold_deg"),
        (("score_weights", "strength"), 0.39, "score_weights"),
        (("coverage_sectors",), 5, "coverage_sectors"),
        (("zone_interior_margin_deg",), 5.0, "zone_interior_margin_deg"),
        (("include_nodes",), True, "include_nodes"),
        (("spatial_filter",), "gaussian", "spatial_filter"),
        (("primary_palette", "ink"), "black", "primary_palette"),
        (("primary_palette", "substrate"), "transparent", "primary_palette"),
    ],
)
def test_tattoo_recipe_rejects_every_noncanonical_value(
    tmp_path: Path,
    path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    payload = deepcopy(_payload())
    _set_path(payload, path, value)

    with pytest.raises(ValueError, match=message):
        load_tattoo_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize("mutation", ["missing", "additional"])
def test_tattoo_recipe_requires_exact_schema_keys(tmp_path: Path, mutation: str) -> None:
    payload = _payload()
    if mutation == "missing":
        del payload["crop_radius"]
    else:
        payload["detector_frame"] = False

    with pytest.raises(ValueError, match="fields differ from the schema"):
        load_tattoo_recipe(_write_recipe(tmp_path, payload))
