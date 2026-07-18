from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.reflector_globe.field import bounded_union, evaluate_reflector_ridges
from kikuchi_lab.reflector_globe.recipes import (
    ReflectorRidgeGeometry,
    ReflectorRidgeRecipe,
    ReflectorRidgeSelection,
    RidgeTier,
)
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember


def make_member(
    *, normal: tuple[float, float, float], theta: float = 0.10, weight: float = 1.0, cohort: int = 4
) -> ReflectorMember:
    return ReflectorMember(
        (1, 0, 0), np.asarray(normal, dtype=float), 2.0, theta, 12.0, weight, True, cohort
    )


def catalog_of(*members: ReflectorMember) -> ReflectorCatalog:
    return ReflectorCatalog(
        "test-source", "a" * 64, 20.0, "reflector-recipe-test", {"test": True}, members
    )


def make_recipe(*, maximum_relief_mm: float = 3.0) -> ReflectorRidgeRecipe:
    tiers = {
        cohort: RidgeTier(
            height_mm=maximum_relief_mm,
            width_multiplier=1.0,
            minimum_width_mm=0.1,
            edge_fillet_fraction=0.2,
        )
        for cohort in range(1, 5)
    }
    return ReflectorRidgeRecipe(
        schema="kikuchi.reflector-ridge-recipe/v1",
        geometry=ReflectorRidgeGeometry(80.0, maximum_relief_mm, "icosphere", 2, "raised_outward"),
        selection=ReflectorRidgeSelection(
            "test-source", 20.0, 0.08, "keep_equal_weights_together", 4
        ),
        tiers=tiers,
    )


def test_one_band_has_a_raised_center_and_zero_outside_corridor() -> None:
    member = make_member(normal=(0.0, 0.0, 1.0), theta=0.10, weight=1.0)
    field = evaluate_reflector_ridges(catalog_of(member), make_recipe(), [[1, 0, 0], [0, 0, 1]])

    assert field.values[0] == pytest.approx(1.0)
    assert field.values[1] == pytest.approx(0.0)
    assert field.contributor_counts.tolist() == [1, 0]
    assert field.ledger[0].effective_half_width_rad == pytest.approx(0.10)


def test_band_field_is_antipodally_equal_and_union_is_bounded() -> None:
    catalog = catalog_of(
        make_member(normal=(0.0, 0.0, 1.0), cohort=4),
        make_member(normal=(0.0, 1.0, 0.0), cohort=3),
    )
    directions = np.asarray([[1.0, 0.0, 0.0], [0.7, 0.7, 0.141421356]], dtype=float)
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    field = evaluate_reflector_ridges(catalog, make_recipe(), np.vstack([directions, -directions]))

    assert np.allclose(field.values[: len(directions)], field.values[len(directions) :], atol=1e-12)
    assert np.all((0.0 <= field.values) & (field.values <= 1.0))
    assert field.field_id.startswith("reflector-ridge-field-")


def test_bounded_union_prevents_additive_spikes() -> None:
    assert bounded_union(np.asarray([[0.8], [0.8]])).item() == pytest.approx(0.96)


def test_physical_minimum_width_is_converted_at_the_base_radius() -> None:
    member = make_member(normal=(0.0, 0.0, 1.0), theta=0.001)
    field = evaluate_reflector_ridges(catalog_of(member), make_recipe(), [[1.0, 0.0, 0.0]])

    assert field.ledger[0].effective_half_width_rad == pytest.approx(0.1 / 40.0)


def test_evaluation_rejects_nonunit_directions_and_invalid_selected_normals() -> None:
    member = make_member(normal=(0.0, 0.0, 1.0))
    with pytest.raises(ValueError, match="unit directions"):
        evaluate_reflector_ridges(catalog_of(member), make_recipe(), [[2.0, 0.0, 0.0]])

    object.__setattr__(member, "normal_crystal", np.asarray([0.0, 0.0, 2.0]))
    with pytest.raises(ValueError, match="unit normal"):
        evaluate_reflector_ridges(catalog_of(member), make_recipe(), [[1.0, 0.0, 0.0]])
