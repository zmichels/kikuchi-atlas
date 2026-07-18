from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.reflectors.recipe import load_reflector_recipe


ROOT = Path(__file__).parents[2]


def test_ice_catalog_recipe_is_closed_and_records_selection_policy() -> None:
    recipe = load_reflector_recipe(ROOT / "recipes/reflectors/ice-ih-catalog.yml")

    assert recipe.eligibility_min_weight == 0.08
    assert recipe.tie_policy == "keep_equal_weights_together"
    assert recipe.cohort_count == 4
    assert recipe.recipe_id.startswith("reflector-recipe-")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_record", "/tmp/ice.yml", "relative"),
        ("energy_kev", 0, "positive"),
        ("min_dspacing_angstrom", 0, "positive"),
        ("cohort_count", 3, "cohort_count"),
        ("eligibility_min_weight", 0.07, "0.08"),
    ],
)
def test_loader_rejects_invalid_policy_values(
    tmp_path: Path, field: str, value: object, match: str
) -> None:
    recipe_text = (ROOT / "recipes/reflectors/ice-ih-catalog.yml").read_text(encoding="utf-8")
    changed = recipe_text.replace(f"{field}: ", f"{field}: {value} # ", 1)
    if field == "source_record":
        changed = recipe_text.replace("source_record: ", "source_record: /tmp/ice.yml # ", 1)
    path = tmp_path / "invalid.yml"
    path.write_text(changed, encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        load_reflector_recipe(path)


def test_loader_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "unknown.yml"
    path.write_text(
        (ROOT / "recipes/reflectors/ice-ih-catalog.yml").read_text(encoding="utf-8")
        + "unexpected: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown keys"):
        load_reflector_recipe(path)


@pytest.mark.parametrize("field", ["schema_version", "eligibility_min_weight"])
def test_loader_rejects_duplicate_mapping_keys(tmp_path: Path, field: str) -> None:
    path = tmp_path / "duplicate.yml"
    path.write_text(
        (ROOT / "recipes/reflectors/ice-ih-catalog.yml").read_text(encoding="utf-8")
        + f"{field}: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=f"duplicate key: {field}"):
        load_reflector_recipe(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "'1'"),
        ("schema_version", "1.0"),
        ("schema_version", "true"),
        ("cohort_count", "'4'"),
        ("cohort_count", "4.0"),
        ("cohort_count", "true"),
        ("energy_kev", "'20.0'"),
        ("energy_kev", "true"),
        ("min_dspacing_angstrom", "'1.0'"),
        ("min_dspacing_angstrom", "true"),
        ("eligibility_min_weight", "'0.08'"),
        ("eligibility_min_weight", "true"),
    ],
)
def test_loader_rejects_scalar_type_coercion(tmp_path: Path, field: str, value: str) -> None:
    recipe_text = (ROOT / "recipes/reflectors/ice-ih-catalog.yml").read_text(encoding="utf-8")
    path = tmp_path / "invalid-type.yml"
    path.write_text(recipe_text.replace(f"{field}: ", f"{field}: {value} # ", 1), encoding="utf-8")

    with pytest.raises(ValueError, match=field):
        load_reflector_recipe(path)
