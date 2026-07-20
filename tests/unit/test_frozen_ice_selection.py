from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.contracts import ArtBandCatalog
from kikuchi_lab.art_products.tattoo_recipe import load_tattoo_recipe
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "recipes/art/ice-ih-reviewed-selection-v2.yml"
TATTOO_RECIPE = ROOT / "recipes/art/ice-ih-tattoo.yml"
REFLECTOR_RECIPE = ROOT / "recipes/reflectors/ice-ih-art-bands.yml"
EXPECTED_HKLS = (
    (0, 0, 2),
    (1, -2, 0),
    (2, -1, 0),
    (1, 1, 0),
    (1, -2, 2),
    (2, 0, 0),
    (2, -1, -2),
    (2, -1, 2),
    (1, -2, -2),
    (1, 1, -2),
    (1, 1, 2),
)


def _corrected_catalog() -> ArtBandCatalog:
    source = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe(REFLECTOR_RECIPE)
    evidence = build_direct_reflector_evidence(source, recipe)
    return build_art_band_catalog_from_evidence(evidence)


def test_reviewed_manifest_rebinds_the_same_hkls_to_corrected_members() -> None:
    from kikuchi_lab.art_products.frozen_selection import (
        bind_frozen_tattoo_selection,
        load_frozen_tattoo_selection,
    )

    catalog = _corrected_catalog()
    recipe = load_tattoo_recipe(TATTOO_RECIPE)
    manifest = load_frozen_tattoo_selection(MANIFEST)

    selection = bind_frozen_tattoo_selection(catalog, recipe, manifest)
    geometry = build_tattoo_geometry(selection, recipe)

    assert manifest.ordered_hkls == EXPECTED_HKLS
    assert tuple(selection.ledger["ordered_hkls"]) == EXPECTED_HKLS
    assert selection.ledger["selection_mode"] == (
        "reviewed_hkl_rebind_under_corrected_physics"
    )
    assert selection.ledger["legacy_catalog_id"] == (
        "art-band-catalog-05f58424b717d5ad"
    )
    assert selection.ledger["legacy_selection_id"] == (
        "tattoo-selection-211db31bbe061d6d"
    )
    assert selection.catalog_id == catalog.catalog_id
    assert selection.selection_id != manifest.legacy_selection_id
    assert len(selection.selected_paths) == 11
    assert len(geometry.paths) == 11
    assert geometry.boundary.outer_diameter_mm == 132.0


def test_reviewed_manifest_requires_every_hkl_to_remain_eligible() -> None:
    from kikuchi_lab.art_products.frozen_selection import (
        bind_frozen_tattoo_selection,
        load_frozen_tattoo_selection,
    )

    catalog = _corrected_catalog()
    manifest = load_frozen_tattoo_selection(MANIFEST)
    recipe = load_tattoo_recipe(TATTOO_RECIPE)
    target = next(member for member in catalog.members if member.hkl == EXPECTED_HKLS[0])
    forged_members = tuple(
        replace(member, tattoo_eligible=False) if member.member_id == target.member_id else member
        for member in catalog.members
    )
    forged = ArtBandCatalog(
        schema_version=catalog.schema_version,
        source_structure_id=catalog.source_structure_id,
        source_structure_sha256=catalog.source_structure_sha256,
        source_recipe_id=catalog.source_recipe_id,
        presentation_recipe_id=catalog.presentation_recipe_id,
        eligibility_min_weight=catalog.eligibility_min_weight,
        members=forged_members,
    )

    with pytest.raises(ValueError, match="reviewed HKL.*eligible"):
        bind_frozen_tattoo_selection(forged, recipe, manifest)


def test_reviewed_manifest_loader_rejects_hkl_drift(tmp_path: Path) -> None:
    from kikuchi_lab.art_products.frozen_selection import load_frozen_tattoo_selection

    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload["paths"][0]["hkl"] = [0, 0, -2]
    path = tmp_path / "manifest.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical"):
        load_frozen_tattoo_selection(path)
