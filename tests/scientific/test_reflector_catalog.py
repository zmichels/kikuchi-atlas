from __future__ import annotations

from pathlib import Path

from kikuchi_lab.reflectors.catalog import build_reflector_catalog
from kikuchi_lab.reflectors.recipe import load_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


def test_ice_catalog_is_real_and_tie_preserving() -> None:
    source = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_reflector_recipe(ROOT / "recipes/reflectors/ice-ih-catalog.yml")

    catalog = build_reflector_catalog(source, recipe)
    eligible = [member for member in catalog.members if member.eligible]

    assert len(catalog.members) == 30
    assert len(eligible) == 15
    assert catalog.selection["source_master_relative_factor"] == 0.03
    assert catalog.selection["selection_relative_factor"] == 0.22
    assert catalog.selection["weight_exponent"] == 2.0
    assert len({member.normalized_weight for member in eligible}) == 6
    assert {member.cohort for member in eligible} == {1, 2, 3, 4}
    assert eligible[0].cohort == 4
    assert eligible[-1].cohort == 1
    for weight in {member.normalized_weight for member in eligible}:
        assert len({member.cohort for member in eligible if member.normalized_weight == weight}) == 1
