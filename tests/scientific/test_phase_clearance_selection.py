from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.clearance_selection import (
    select_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.hemisphere_recipe import load_hemisphere_series_recipe
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.model.identity import plain_data
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"
EXPECTED_SEARCH = {
    "quartz": (1, frozenset()),
    "forsterite": (
        6,
        frozenset(
            {
                "art-band-member-9cfe1780af420206",
                "art-band-member-de7105e0699dae4a",
            }
        ),
    ),
    "zircon": (2, frozenset({"art-band-member-4153b731afe5cd0c"})),
    "titanite": (2, frozenset({"art-band-member-68518911e93cd5da"})),
}


@lru_cache(maxsize=None)
def _catalog(phase_slug: str):
    source = load_structure_record(ROOT / f"phases/{phase_slug}/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / f"recipes/reflectors/{phase_slug}-art-bands.yml"
    )
    evidence = build_direct_reflector_evidence(source, recipe)
    return build_art_band_catalog_from_evidence(evidence)


@pytest.mark.parametrize("phase_slug", tuple(EXPECTED_SEARCH))
def test_real_phase_selection_satisfies_fixed_clearance_search_locks(
    phase_slug: str,
) -> None:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for(phase_slug)
    catalog = _catalog(phase_slug)
    catalog_before = catalog.to_dict()
    greedy = select_tattoo_paths(catalog, recipe)

    selection = select_clearance_valid_tattoo_paths(catalog, recipe)

    expected_states, expected_exclusions = EXPECTED_SEARCH[phase_slug]
    assert catalog.to_dict() == catalog_before
    assert selection.catalog_id == catalog.catalog_id
    assert tuple(candidate.member_id for candidate in selection.candidates) == tuple(
        candidate.member_id for candidate in greedy.candidates
    )
    assert expected_exclusions.isdisjoint(
        path.member_id for path in selection.selected_paths
    )
    if not expected_exclusions:
        assert selection.selection_id == greedy.selection_id
        assert plain_data(selection.ledger) == plain_data(greedy.ledger)
        assert "wide_clearance_search" not in selection.ledger
    else:
        search = selection.ledger["wide_clearance_search"]
        assert search["evaluated_state_count"] == expected_states
        assert frozenset(search["chosen_exclusions"]) == expected_exclusions
        for member_id in expected_exclusions:
            assert (
                selection.ledger["rejections"][member_id]
                == "wide_clearance_search_exclusion"
            )

    standard = build_tattoo_geometry(selection, recipe, width_scale=1.0)
    wide = build_tattoo_geometry(selection, recipe, width_scale=1.15)
    assert [path.member_id for path in standard.paths] == [
        path.member_id for path in wide.paths
    ]
    for standard_path, wide_path in zip(standard.paths, wide.paths, strict=True):
        np.testing.assert_array_equal(standard_path.points_mm, wide_path.points_mm)
        assert wide_path.width_mm == pytest.approx(
            standard_path.width_mm * 1.15,
            abs=1e-12,
        )
