from pathlib import Path

import pytest
import yaml

from kikuchi_lab.habit.recipes import load_habit_recipe

ROOT = Path(__file__).parents[3]
RECIPE = ROOT / "recipes/habits/quartz-mtex-example.yml"


def _recipe_mapping() -> dict:
    raw = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    raw["phase"]["cif"] = str(ROOT / "phases/quartz/COD-9000775.cif")
    return raw


def _nested_mapping(raw: dict, path: tuple[str | int, ...]) -> dict:
    value = raw
    for part in path:
        value = value[part]
    return value


def _write_recipe(tmp_path: Path, raw: dict) -> Path:
    candidate = tmp_path / "habit.yml"
    candidate.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return candidate


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


def test_recipe_rejects_near_scaling_orientation_matrix(tmp_path: Path):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    text = (
        RECIPE.read_text(encoding="utf-8")
        .replace("../../phases/quartz/COD-9000775.cif", str(cif))
        .replace(
            "maximum_dimension_mm: 60.0",
            "maximum_dimension_mm: 60.0\n  orientation_matrix: [[1.000004,0,0],[0,1,0],[0,0,1]]",
        )
    )
    candidate = tmp_path / "near-scaling.yml"
    candidate.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="proper orthogonal rotation"):
        load_habit_recipe(candidate)


@pytest.mark.parametrize("convention", ["hkl", "hkil"])
def test_recipe_rejects_all_zero_family(tmp_path: Path, convention: str):
    cif = ROOT / "phases/quartz/COD-9000775.cif"
    zero_family = "[0, 0, 0]" if convention == "hkl" else "[0, 0, 0, 0]"
    text = (
        RECIPE.read_text(encoding="utf-8")
        .replace("../../phases/quartz/COD-9000775.cif", str(cif))
        .replace("index_convention: hkil", f"index_convention: {convention}")
        .replace("family: [1, 0, -1, 0]", f"family: {zero_family}")
    )
    candidate = tmp_path / f"zero-{convention}.yml"
    candidate.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="family must not be all zero"):
        load_habit_recipe(candidate)


@pytest.mark.parametrize(
    ("path", "mapping_name", "unknown_key"),
    [
        ((), "root", "unexpected_root"),
        (("phase",), "phase", "unexpected_phase"),
        (("phase", "provenance"), "phase provenance", "unexpected_provenance"),
        (("habit",), "habit", "unexpected_habit"),
        (("habit", "faces", 0), "habit face", "unexpected_face"),
        (("geometry",), "geometry", "orientation_matrx"),
        (("fdm_context",), "fdm_context", "unexpected_fdm"),
    ],
)
def test_recipe_rejects_unknown_keys_at_every_mapping_level(
    tmp_path: Path,
    path: tuple[str | int, ...],
    mapping_name: str,
    unknown_key: str,
):
    raw = _recipe_mapping()
    _nested_mapping(raw, path)[unknown_key] = "typo"
    candidate = _write_recipe(tmp_path, raw)

    with pytest.raises(ValueError, match=rf"{mapping_name}.*unknown keys.*{unknown_key}"):
        load_habit_recipe(candidate)


@pytest.mark.parametrize(
    ("path", "mapping_name", "missing_key"),
    [
        ((), "root", "exports"),
        (("phase",), "phase", "formula"),
        (("phase", "provenance"), "phase provenance", "license"),
        (("habit",), "habit", "index_convention"),
        (("habit", "faces", 0), "habit face", "label"),
        (("geometry",), "geometry", "maximum_dimension_mm"),
        (("fdm_context",), "fdm_context", "nozzle_width_mm"),
    ],
)
def test_recipe_rejects_missing_required_keys_at_every_mapping_level(
    tmp_path: Path,
    path: tuple[str | int, ...],
    mapping_name: str,
    missing_key: str,
):
    raw = _recipe_mapping()
    del _nested_mapping(raw, path)[missing_key]
    candidate = _write_recipe(tmp_path, raw)

    with pytest.raises(ValueError, match=rf"{mapping_name}.*missing keys.*{missing_key}"):
        load_habit_recipe(candidate)
