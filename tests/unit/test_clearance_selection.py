from __future__ import annotations

import importlib
import math
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from kikuchi_lab.art_products.catalog import _assign_cohorts
from kikuchi_lab.art_products.contracts import ArtBandCatalog, ArtBandMember
from kikuchi_lab.art_products.hemisphere_recipe import load_hemisphere_series_recipe
from kikuchi_lab.art_products import tattoo_selection
from kikuchi_lab.model.identity import plain_data
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"


def _clearance_selection() -> ModuleType:
    return importlib.import_module("kikuchi_lab.art_products.clearance_selection")


def _catalog(*, member_count: int = 13) -> ArtBandCatalog:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    inverse = orientation_matrix(recipe.orientation).T
    members = []
    for index in range(member_count):
        angle = index * math.pi / member_count
        normal_sample = np.array([math.cos(angle), math.sin(angle), 0.0])
        members.append(
            ArtBandMember(
                hkl=(index + 1, 1, 0),
                normal_crystal=inverse @ normal_sample,
                bragg_half_width_rad=0.030 - index * 0.0005,
                structure_factor_magnitude=100.0 - index,
                normalized_weight=1.0 - index * 0.03,
                globe_cohort=None,
                globe_eligible=True,
                tattoo_eligible=True,
                acceptance_state="unreviewed",
                acceptance_reason="synthetic exclusion-core candidate",
            )
        )
    members.sort(
        key=lambda member: (-member.normalized_weight, member.hkl, member.member_id)
    )
    cohort_by_member = _assign_cohorts(members)
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id="structure-clearance-selection-fixture",
        source_structure_sha256="a" * 64,
        source_recipe_id="recipe-source-clearance-selection-fixture",
        presentation_recipe_id="recipe-presentation-clearance-selection-fixture",
        eligibility_min_weight=0.08,
        members=tuple(
            replace(member, globe_cohort=cohort_by_member[member.member_id])
            for member in members
        ),
    )


def test_private_selector_excludes_without_mutating_or_dropping_candidates() -> None:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()
    original_catalog = catalog.to_dict()
    greedy = tattoo_selection.select_tattoo_paths(catalog, recipe)
    excluded_id = greedy.selected_paths[0].member_id

    selection = tattoo_selection._select_tattoo_paths(
        catalog,
        recipe,
        excluded_member_ids=frozenset({excluded_id}),
    )

    assert catalog.to_dict() == original_catalog
    assert selection.catalog_id == catalog.catalog_id
    assert tuple(candidate.member_id for candidate in selection.candidates) == tuple(
        candidate.member_id for candidate in greedy.candidates
    )
    assert excluded_id not in {path.member_id for path in selection.selected_paths}
    assert (
        selection.ledger["rejections"][excluded_id]
        == "wide_clearance_search_exclusion"
    )


def test_public_selector_remains_the_zero_exclusion_core() -> None:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()

    public = tattoo_selection.select_tattoo_paths(catalog, recipe)
    private = tattoo_selection._select_tattoo_paths(
        catalog,
        recipe,
        excluded_member_ids=frozenset(),
    )

    assert public.selection_id == private.selection_id
    assert plain_data(public.ledger) == plain_data(private.ledger)


def test_public_selector_preserves_the_legacy_insufficient_catalog_message() -> None:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")

    with pytest.raises(
        ValueError,
        match=r"^tattoo catalog has 10 eligible candidates; 11 are required$",
    ):
        tattoo_selection.select_tattoo_paths(_catalog(member_count=10), recipe)


def test_clearance_selector_returns_unchanged_greedy_selection_when_wide_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _clearance_selection()
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()
    greedy = tattoo_selection.select_tattoo_paths(catalog, recipe)
    scales: list[float] = []

    def accept_geometry(_selection, _recipe, *, width_scale: float):
        scales.append(width_scale)
        return object()

    monkeypatch.setattr(module, "build_tattoo_geometry", accept_geometry)

    selected = module.select_clearance_valid_tattoo_paths(catalog, recipe)

    assert tuple(path.member_id for path in selected.selected_paths) == tuple(
        path.member_id for path in greedy.selected_paths
    )
    assert selected.selection_id == greedy.selection_id
    assert plain_data(selected.ledger) == plain_data(greedy.ledger)
    assert scales == [1.15, 1.0]


def test_clearance_selector_branches_lower_priority_first_and_records_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _clearance_selection()
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()
    greedy = tattoo_selection.select_tattoo_paths(catalog, recipe)
    higher_priority_id = greedy.selected_paths[1].member_id
    lower_priority_id = greedy.selected_paths[9].member_id
    scales: list[float] = []

    def conflict_then_accept(selection, _recipe, *, width_scale: float):
        scales.append(width_scale)
        if lower_priority_id in {path.member_id for path in selection.selected_paths}:
            raise module.TattooClearanceError(
                "synthetic clearance conflict",
                clearance_kind="noncrossing_edge_gap",
                member_ids=(higher_priority_id, lower_priority_id),
            )
        return object()

    monkeypatch.setattr(module, "build_tattoo_geometry", conflict_then_accept)

    selected = module.select_clearance_valid_tattoo_paths(catalog, recipe)

    assert lower_priority_id not in {path.member_id for path in selected.selected_paths}
    assert higher_priority_id in {path.member_id for path in selected.selected_paths}
    assert selected.catalog_id == catalog.catalog_id
    assert scales == [1.15, 1.15, 1.0]
    assert selected.ledger["rejections"][lower_priority_id] == (
        "wide_clearance_search_exclusion"
    )
    assert plain_data(selected.ledger["wide_clearance_search"]) == {
        "algorithm_version": "bounded-bfs-wide-clearance-v1",
        "width_scale": 1.15,
        "state_limit": 256,
        "chosen_exclusions": [lower_priority_id],
        "evaluated_state_count": 2,
        "conflict_history": [
            {
                "evaluated_state": 1,
                "excluded_member_ids": [],
                "clearance_kind": "noncrossing_edge_gap",
                "member_ids": [higher_priority_id, lower_priority_id],
                "message": "synthetic clearance conflict",
            }
        ],
    }


def test_standard_clearance_selector_branches_crop_fragments_and_records_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _clearance_selection()
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()
    greedy = tattoo_selection.select_tattoo_paths(catalog, recipe)
    excluded_id = greedy.selected_paths[-1].member_id
    scales: list[float] = []

    def crop_conflict_then_accept(selection, _recipe, *, width_scale: float):
        scales.append(width_scale)
        if excluded_id in {path.member_id for path in selection.selected_paths}:
            raise module.TattooClearanceError(
                "synthetic crop fragment conflict",
                clearance_kind="crop_fragment",
                member_ids=(excluded_id,),
            )
        return object()

    monkeypatch.setattr(module, "build_tattoo_geometry", crop_conflict_then_accept)

    selected = module.select_standard_clearance_valid_tattoo_paths(catalog, recipe)

    assert excluded_id not in {path.member_id for path in selected.selected_paths}
    assert selected.ledger["rejections"][excluded_id] == (
        "standard_clearance_search_exclusion"
    )
    assert scales == [1.0, 1.0]
    assert plain_data(selected.ledger["standard_clearance_search"]) == {
        "algorithm_version": "bounded-bfs-standard-clearance-v1",
        "width_scale": 1.0,
        "state_limit": 256,
        "chosen_exclusions": [excluded_id],
        "evaluated_state_count": 2,
        "conflict_history": [
            {
                "evaluated_state": 1,
                "excluded_member_ids": [],
                "clearance_kind": "crop_fragment",
                "member_ids": [excluded_id],
                "message": "synthetic crop fragment conflict",
            }
        ],
    }


def test_clearance_selector_stops_at_the_state_bound_with_last_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _clearance_selection()
    assert module.MAX_CLEARANCE_SEARCH_STATES == 256
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    catalog = _catalog()

    def always_conflict(selection, _recipe, *, width_scale: float):
        assert width_scale == 1.15
        first, second = selection.selected_paths[-2:]
        raise module.TattooClearanceError(
            "synthetic persistent conflict",
            clearance_kind="unrelated_endpoint",
            member_ids=(first.member_id, second.member_id),
        )

    monkeypatch.setattr(module, "build_tattoo_geometry", always_conflict)
    monkeypatch.setattr(module, "MAX_CLEARANCE_SEARCH_STATES", 3)

    with pytest.raises(module.ClearanceSelectionFeasibilityError) as raised:
        module.select_clearance_valid_tattoo_paths(catalog, recipe)

    error = raised.value
    assert isinstance(error, ValueError)
    assert error.phase_slug == "quartz"
    assert error.catalog_id == catalog.catalog_id
    assert error.evaluated_state_count == 3
    assert error.last_conflict == {
        "clearance_kind": "unrelated_endpoint",
        "member_ids": error.last_conflict["member_ids"],
        "message": "synthetic persistent conflict",
    }
    assert "quartz" in str(error)
    assert catalog.catalog_id in str(error)
    assert "3 evaluated states" in str(error)
    assert "synthetic persistent conflict" in str(error)


def test_clearance_selection_and_errors_are_public_art_product_seams() -> None:
    from kikuchi_lab import art_products

    module = _clearance_selection()
    assert (
        art_products.select_clearance_valid_tattoo_paths
        is module.select_clearance_valid_tattoo_paths
    )
    assert (
        art_products.ClearanceSelectionFeasibilityError
        is module.ClearanceSelectionFeasibilityError
    )
    assert art_products.TattooClearanceError is module.TattooClearanceError
