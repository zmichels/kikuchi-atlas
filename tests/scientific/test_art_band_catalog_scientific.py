from __future__ import annotations

import numpy as np

from kikuchi_lab.near_depth.overlap import AxialBandSet
from kikuchi_lab.spherical_intensity.presentation import PresentationSource


def _synthetic_source() -> PresentationSource:
    hkls = np.array(
        [
            [4, 0, 0],
            [2, 0, 0],
            [3, 0, 0],
            [1, 0, 0],
            [2, 1, 0],
            [1, 1, 0],
            [3, 1, 0],
            [1, 2, 0],
            [2, 2, 1],
            [1, 0, 1],
            [2, 0, 1],
            [3, 0, 1],
        ],
        dtype=np.int32,
    )
    weights = np.array(
        [0.8, 1.0, 0.8, 0.7, 0.5, 0.6, 0.5, 0.4, 0.1, 0.3, 0.05, 0.2],
        dtype=np.float64,
    )
    angles = np.linspace(0.0, 2.0 * np.pi, len(hkls), endpoint=False)
    axial_bands = AxialBandSet(
        hkl=hkls,
        normals=np.column_stack(
            (np.cos(angles), np.sin(angles), np.zeros(len(hkls)))
        ),
        theta_radian=np.linspace(0.01, 0.021, len(hkls)),
        structure_factor_abs=np.linspace(24.0, 13.0, len(hkls)),
    )
    valid = np.zeros((3, 3), dtype=bool)
    valid[1, 1] = True
    return PresentationSource(
        toned_master=np.zeros((2, 3, 3), dtype=np.float32),
        axial_bands=axial_bands,
        band_weights=weights,
        overlap_normalization=1.0,
        upper_directions=np.array([[0.0, 0.0, 1.0]]),
        upper_valid=valid,
        gain=0.0,
        ceiling=0.9,
        ledger={"scientific_claim": "presentation_only"},
    )


def test_tie_aware_catalog_ranking_and_quartile_partition() -> None:
    from kikuchi_lab.art_products.catalog import build_art_band_catalog

    catalog = build_art_band_catalog(
        _synthetic_source(),
        source_structure_id="structure-ice-ih",
        source_structure_sha256="a" * 64,
        source_recipe_id="recipe-source-0123456789abcdef",
        presentation_recipe_id="recipe-presentation-0123456789abcdef",
        eligibility_min_weight=0.10,
    )

    assert len(catalog.members) == 12
    ordering = [
        (-member.normalized_weight, member.hkl, member.member_id)
        for member in catalog.members
    ]
    assert ordering == sorted(ordering)

    eligible = [member for member in catalog.members if member.globe_eligible]
    cohorts = {
        cohort: [member for member in eligible if member.globe_cohort == cohort]
        for cohort in (1, 2, 3, 4)
    }
    assert all(cohorts.values())
    assert {member.normalized_weight for member in cohorts[4]} == {1.0, 0.8}
    assert {member.normalized_weight for member in cohorts[3]} == {0.7, 0.6}
    assert {member.normalized_weight for member in cohorts[2]} == {0.5, 0.4}
    assert {member.normalized_weight for member in cohorts[1]} == {0.3, 0.2, 0.1}

    weight_cohorts: dict[float, set[int | None]] = {}
    for member in eligible:
        weight_cohorts.setdefault(member.normalized_weight, set()).add(
            member.globe_cohort
        )
    assert all(len(assigned) == 1 for assigned in weight_cohorts.values())


def test_catalog_eligibility_threshold_is_inclusive_for_both_products() -> None:
    from kikuchi_lab.art_products.catalog import build_art_band_catalog

    catalog = build_art_band_catalog(
        _synthetic_source(),
        source_structure_id="structure-ice-ih",
        source_structure_sha256="a" * 64,
        source_recipe_id="recipe-source-0123456789abcdef",
        presentation_recipe_id="recipe-presentation-0123456789abcdef",
        eligibility_min_weight=0.10,
    )

    at_threshold = next(
        member for member in catalog.members if member.normalized_weight == 0.10
    )
    below_threshold = next(
        member for member in catalog.members if member.normalized_weight == 0.05
    )
    assert at_threshold.globe_eligible is True
    assert at_threshold.tattoo_eligible is True
    assert at_threshold.globe_cohort in {1, 2, 3, 4}
    assert below_threshold.globe_eligible is False
    assert below_threshold.tattoo_eligible is False
    assert below_threshold.globe_cohort is None
    assert all(member.acceptance_state == "unreviewed" for member in catalog.members)
    assert all(
        member.acceptance_reason == "automatic catalog candidate"
        for member in catalog.members
    )
