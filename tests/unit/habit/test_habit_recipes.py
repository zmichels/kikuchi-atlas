from pathlib import Path

import pytest

from kikuchi_lab.habit.recipes import load_habit_recipe

ROOT = Path(__file__).parents[3]
RECIPE = ROOT / "recipes/habits/quartz-mtex-example.yml"


def test_quartz_recipe_preserves_explicit_support_distances_and_source_identity():
    recipe = load_habit_recipe(RECIPE)

    assert recipe.schema == "kikuchi.habit-recipe/v1"
    assert recipe.phase.name == "quartz"
    assert recipe.phase.space_group_number == 154
    assert recipe.index_convention == "hkil"
    assert recipe.maximum_dimension_mm == 60.0
    assert {face.label: face.relative_distance for face in recipe.faces} == {
        "m": pytest.approx(0.5091702048436217),
        "r": pytest.approx(1.0),
        "z": pytest.approx(1.1111111111111112),
        "s1": pytest.approx(0.9557191976124586),
        "x1": pytest.approx(0.7545681549701853),
    }
    assert recipe.phase.cif_sha256 == (
        "10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57"
    )
    assert recipe.recipe_id == load_habit_recipe(RECIPE).recipe_id
    assert str(ROOT) not in str(recipe.identity_dict())


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("relative_distance: 1.0", "relative_distance"),
        ("family: [1, 0, 0, 0]", "h + k + i"),
        ("maximum_dimension_mm: 0", "maximum_dimension_mm"),
    ],
)
def test_recipe_rejects_nonpositive_distance_invalid_hkil_and_scale(
    tmp_path: Path, replacement: str, message: str
):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = RECIPE.read_text(encoding="utf-8").replace(
        "../../phases/quartz/COD-9000775.cif", str(cif)
    )
    if "relative_distance" in replacement:
        text = text.replace("relative_distance: 0.5091702048436217", "relative_distance: 0")
    elif "family" in replacement:
        text = text.replace("family: [1, 0, -1, 0]", replacement)
    else:
        text = text.replace("maximum_dimension_mm: 60.0", replacement)
    candidate = tmp_path / "habit.yml"
    candidate.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_habit_recipe(candidate)


def test_orientation_defaults_to_identity():
    recipe = load_habit_recipe(RECIPE)
    assert recipe.orientation_matrix == (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def test_recipe_rejects_reflection_matrix(tmp_path: Path):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = (
        RECIPE.read_text(encoding="utf-8")
        .replace("../../phases/quartz/COD-9000775.cif", str(cif))
        .replace(
            "maximum_dimension_mm: 60.0",
            "maximum_dimension_mm: 60.0\n  orientation_matrix: [[-1,0,0],[0,1,0],[0,0,1]]",
        )
    )
    candidate = tmp_path / "reflection.yml"
    candidate.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="proper orthogonal rotation"):
        load_habit_recipe(candidate)


def test_recipe_rejects_explicit_null_orientation_matrix(tmp_path: Path):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = (
        RECIPE.read_text(encoding="utf-8")
        .replace("../../phases/quartz/COD-9000775.cif", str(cif))
        .replace(
            "maximum_dimension_mm: 60.0",
            "maximum_dimension_mm: 60.0\n  orientation_matrix: null",
        )
    )
    candidate = tmp_path / "null-orientation.yml"
    candidate.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="finite 3 by 3 matrix"):
        load_habit_recipe(candidate)
