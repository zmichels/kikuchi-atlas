from __future__ import annotations

import math
from collections import Counter
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from kikuchi_lab.art_products.contracts import ArtBandCatalog, ArtBandMember
from kikuchi_lab.art_products.tattoo_recipe import load_tattoo_recipe
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.model.identity import plain_data
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


RECIPE = "recipes/art/ice-ih-tattoo.yml"
SCORE_NAMES = {
    "strength",
    "angular_width",
    "nonredundancy",
    "coverage",
    "zone_relationship",
}


def _normal(colatitude_deg: float, azimuth_deg: float) -> np.ndarray:
    colatitude = math.radians(colatitude_deg)
    azimuth = math.radians(azimuth_deg)
    return np.array(
        [
            math.sin(colatitude) * math.cos(azimuth),
            math.sin(colatitude) * math.sin(azimuth),
            math.cos(colatitude),
        ]
    )


def _catalog() -> tuple[ArtBandCatalog, str]:
    directions = [_normal(8.0, 15.0)]
    directions.extend(_normal(28.0, azimuth) for azimuth in (0, 90, 180, 270))
    directions.extend(
        _normal(50.0, azimuth) for azimuth in (0, 60, 120, 180, 240, 300)
    )
    directions.extend(
        _normal(74.0, azimuth) for azimuth in (0, 60, 120, 180, 240, 300)
    )
    members = []
    for index, normal in enumerate(directions):
        members.append(
            ArtBandMember(
                hkl=(index + 1, 0, 1),
                normal_crystal=normal,
                bragg_half_width_rad=0.030 if index == 0 else 0.012 + 0.0004 * (index % 5),
                structure_factor_magnitude=100.0 - index,
                normalized_weight=1.0 - 0.025 * index,
                globe_cohort=4 if index < 4 else 3,
                globe_eligible=True,
                tattoo_eligible=True,
                acceptance_state="unreviewed",
                acceptance_reason="synthetic tattoo selection candidate",
            )
        )
    redundant = ArtBandMember(
        hkl=(99, 0, 1),
        normal_crystal=_normal(10.0, 15.0),
        bragg_half_width_rad=0.010,
        structure_factor_magnitude=99.5,
        normalized_weight=0.99,
        globe_cohort=4,
        globe_eligible=True,
        tattoo_eligible=True,
        acceptance_state="unreviewed",
        acceptance_reason="synthetic angular redundancy candidate",
    )
    members.append(redundant)
    return (
        ArtBandCatalog(
            schema_version=1,
            source_structure_id="structure-ice-ih-synthetic",
            source_structure_sha256="b" * 64,
            source_recipe_id="recipe-source-synthetic",
            presentation_recipe_id="recipe-presentation-synthetic",
            eligibility_min_weight=0.10,
            members=tuple(members),
        ),
        redundant.member_id,
    )


def test_selection_is_deterministic_rotated_and_exactly_allocated() -> None:
    catalog, redundant_id = _catalog()
    recipe = load_tattoo_recipe(RECIPE)

    first = select_tattoo_paths(catalog, recipe)
    repeated = select_tattoo_paths(catalog, recipe)

    first_ids = tuple(path.member_id for path in first.selected_paths)
    assert first_ids == tuple(path.member_id for path in repeated.selected_paths)
    assert first.selection_id == repeated.selection_id
    assert plain_data(first.ledger) == plain_data(repeated.ledger)
    assert len(first_ids) == len(set(first_ids)) == 11
    assert Counter(path.tier for path in first.selected_paths) == {
        "dominant": 4,
        "secondary": 4,
        "fine": 3,
    }
    assert [path.width_mm for path in first.selected_paths] == [
        4.8,
        4.2,
        3.6,
        3.1,
        2.5,
        2.2,
        1.9,
        1.6,
        1.2,
        1.0,
        0.8,
    ]

    matrix = orientation_matrix(recipe.orientation)
    member_by_id = {member.member_id: member for member in catalog.members}
    for candidate in first.candidates:
        np.testing.assert_allclose(
            candidate.normal_sample,
            matrix @ member_by_id[candidate.member_id].normal_crystal,
            rtol=0.0,
            atol=5e-13,
        )

    assert redundant_id not in first_ids
    assert first.ledger["rejections"][redundant_id] == "angular_redundancy"


def test_center_trace_sampling_projection_and_scores_are_numeric() -> None:
    catalog, _ = _catalog()
    recipe = load_tattoo_recipe(RECIPE)

    selection = select_tattoo_paths(catalog, recipe)
    candidate = selection.candidates[1]

    assert candidate.great_circle_sample.shape == (721, 3)
    assert candidate.center_trace.shape == (361, 2)
    np.testing.assert_allclose(
        candidate.great_circle_sample @ candidate.normal_sample,
        0.0,
        rtol=0.0,
        atol=5e-13,
    )
    np.testing.assert_allclose(
        np.linalg.norm(candidate.great_circle_sample, axis=1),
        1.0,
        rtol=0.0,
        atol=5e-13,
    )
    upper = candidate.great_circle_sample[:361]
    assert np.min(upper[:, 2]) >= -5e-13
    np.testing.assert_allclose(
        candidate.center_trace,
        upper[:, :2] / (1.0 + upper[:, 2, None]),
        rtol=0.0,
        atol=5e-13,
    )

    strongest = selection.selected_paths[0]
    assert set(strongest.score_components) == SCORE_NAMES
    assert strongest.score_components == {
        "strength": 1.0,
        "angular_width": 1.0,
        "nonredundancy": 1.0,
        "coverage": 1.0,
        "zone_relationship": 0.0,
    }
    assert strongest.total_score == pytest.approx(0.90, abs=1e-15)
    for path in selection.selected_paths:
        assert all(
            isinstance(score, float) and math.isfinite(score) and 0.0 <= score <= 1.0
            for score in path.score_components.values()
        )
        expected = sum(
            recipe.score_weights[name] * path.score_components[name]
            for name in SCORE_NAMES
        )
        assert path.total_score == pytest.approx(expected, abs=1e-15)


def test_candidate_selection_arrays_and_ledgers_are_deeply_immutable() -> None:
    catalog, redundant_id = _catalog()
    selection = select_tattoo_paths(catalog, load_tattoo_recipe(RECIPE))
    candidate = selection.candidates[1]
    selected = selection.selected_paths[0]

    for array in (
        candidate.normal_crystal,
        candidate.normal_sample,
        candidate.great_circle_sample,
        candidate.center_trace,
        selected.normal_sample,
        selected.center_trace,
    ):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array[...] = 0.0
    with pytest.raises(FrozenInstanceError):
        candidate.member_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        selected.width_mm = 9.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        selected.score_components["strength"] = 0.0  # type: ignore[index]
    with pytest.raises(TypeError):
        selection.ledger["rejections"][redundant_id] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        selection.ledger["candidate_scores"][candidate.member_id][0][
            "score_components"
        ]["strength"] = 0.0  # type: ignore[index]
