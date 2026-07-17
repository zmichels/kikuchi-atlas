from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.hemisphere_recipe import load_hemisphere_series_recipe
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"


@lru_cache(maxsize=None)
def _catalog(phase_slug: str):
    source = load_structure_record(ROOT / f"phases/{phase_slug}/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / f"recipes/reflectors/{phase_slug}-art-bands.yml"
    )
    evidence = build_direct_reflector_evidence(source, recipe)
    return build_art_band_catalog_from_evidence(evidence)


def test_standard_and_wide_share_selection_and_centerlines() -> None:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    composition = series.composition_for("quartz")
    selection = select_tattoo_paths(_catalog("quartz"), composition)

    standard = build_tattoo_geometry(selection, composition, width_scale=1.0)
    wide = build_tattoo_geometry(selection, composition, width_scale=1.15)

    assert [path.member_id for path in standard.paths] == [
        path.member_id for path in wide.paths
    ]
    for ordinary, widened in zip(standard.paths, wide.paths, strict=True):
        np.testing.assert_array_equal(ordinary.points_mm, widened.points_mm)
        assert widened.width_mm == pytest.approx(
            ordinary.width_mm * 1.15,
            abs=1e-12,
        )
    assert standard.boundary.to_dict() == wide.boundary.to_dict()
    assert standard.geometry_id != wide.geometry_id


def test_naive_forsterite_selection_is_rejected_without_weakening_clearance() -> None:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    composition = series.composition_for("forsterite")
    selection = select_tattoo_paths(_catalog("forsterite"), composition)

    with pytest.raises(ValueError, match="noncrossing edge gap"):
        build_tattoo_geometry(selection, composition, width_scale=1.15)


@pytest.mark.parametrize("width_scale", [True, 0.99, 1.1500000001, float("nan")])
def test_geometry_rejects_unapproved_width_scale(width_scale: object) -> None:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    composition = series.composition_for("quartz")
    selection = select_tattoo_paths(_catalog("quartz"), composition)

    with pytest.raises(ValueError, match="width_scale"):
        build_tattoo_geometry(
            selection,
            composition,
            width_scale=width_scale,
        )
