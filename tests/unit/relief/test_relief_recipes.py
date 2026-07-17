from pathlib import Path

import pytest

from kikuchi_lab.relief.recipes import load_relief_globe_recipe

ROOT = Path(__file__).parents[3]
RECIPE = ROOT / "recipes/relief/forsterite-intensity-globe.yml"


def test_forsterite_relief_recipe_preserves_approved_contract():
    recipe = load_relief_globe_recipe(RECIPE)
    assert recipe.schema == "kikuchi.relief-globe-recipe/v1"
    assert recipe.source.product_id == "master-437f865cd0f68384"
    assert recipe.source.array_sha256 == (
        "7cefc253da7c1d17babca40cfeab12be1e3b400cf259bd28686df51c78451f2e"
    )
    assert recipe.source.file_sha256 == (
        "cd056ab4af34aa3695e492f2f6a85f47beb5e97658ef6c5cc4120802ae161c03"
    )
    assert recipe.geometry.base_diameter_mm == 80.0
    assert recipe.geometry.maximum_relief_mm == 1.2
    assert recipe.geometry.topology == "icosphere"
    assert recipe.geometry.subdivisions == 7
    assert recipe.mapping.percentiles == (1.0, 99.0)
    assert recipe.mapping.gamma == 1.0
    assert recipe.mapping.direction == "bright_outward"
    assert recipe.filter.kind == "spherical_gaussian"
    assert recipe.filter.fwhm_mm == 0.8
    assert recipe.filter.cutoff_sigma == 3.0
    assert recipe.exports == ("stl",)
    assert recipe.recipe_id == load_relief_globe_recipe(RECIPE).recipe_id
    assert "local/" not in str(recipe.identity_dict())


@pytest.mark.parametrize(
    ("needle", "replacement", "message"),
    [
        ("orientation", "orientation_matrx: identity\n", "unknown keys"),
        ("base_diameter_mm: 80.0", "base_diameter_mm: 0", "base_diameter_mm"),
        ("maximum_relief_mm: 1.2", "maximum_relief_mm: -1", "maximum_relief_mm"),
        ("upper: 99.0", "upper: 1.0", "percentile"),
        ("gamma: 1.0", "gamma: false", "gamma"),
        ("fwhm_mm: 0.8", "fwhm_mm: .nan", "fwhm_mm"),
    ],
)
def test_recipe_rejects_unknown_and_invalid_semantics(
    tmp_path: Path, needle: str, replacement: str, message: str
):
    text = RECIPE.read_text(encoding="utf-8")
    text = text.replace(needle, replacement) if needle != "orientation" else text + replacement
    candidate = tmp_path / "candidate.yml"
    candidate.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_relief_globe_recipe(candidate)


def test_recipe_parser_preserves_valid_noncanonical_choices_for_layered_consumers(tmp_path):
    text = RECIPE.read_text(encoding="utf-8")
    text = text.replace("subdivisions: 7", "subdivisions: 6")
    text = text.replace("topology: icosphere", "topology: alternate-sphere")
    text = text.replace("direction: bright_outward", "direction: dark_outward")
    text = text.replace("kind: spherical_gaussian", "kind: alternate_filter")
    text = text.replace("formats: [stl]", "formats: [obj, stl]")
    candidate = tmp_path / "noncanonical.yml"
    candidate.write_text(text, encoding="utf-8")

    recipe = load_relief_globe_recipe(candidate)

    assert recipe.geometry.subdivisions == 6
    assert recipe.geometry.topology == "alternate-sphere"
    assert recipe.mapping.direction == "dark_outward"
    assert recipe.filter.kind == "alternate_filter"
    assert recipe.exports == ("obj", "stl")
