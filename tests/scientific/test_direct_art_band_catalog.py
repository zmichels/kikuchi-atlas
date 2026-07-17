from __future__ import annotations

from pathlib import Path

from kikuchi_lab.art_products import build_art_band_catalog_from_evidence
from kikuchi_lab.kinematical import load_direct_reflector_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    build_direct_reflector_evidence,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


def test_direct_catalog_uses_owned_evidence_without_presentation_source() -> None:
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / "recipes/reflectors/ice-ih-art-bands.yml"
    )
    evidence = build_direct_reflector_evidence(record, recipe)

    catalog = build_art_band_catalog_from_evidence(evidence)

    assert catalog.source_structure_id == record.identifier
    assert catalog.source_structure_sha256 == record.sha256
    assert catalog.source_recipe_id == recipe.calculation_id
    assert catalog.presentation_recipe_id == recipe.weighting_id
    assert catalog.eligibility_min_weight == 0.08
    assert sum(member.tattoo_eligible for member in catalog.members) >= 11
