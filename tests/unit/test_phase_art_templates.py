from __future__ import annotations

from kikuchi_lab.art_products.hemisphere_recipe import load_hemisphere_series_recipe
from kikuchi_lab.workflows.phase_art_templates import (
    TEMPLATE_VARIANTS,
    composition_for_phase_template,
)


def test_phase_template_variants_reuse_the_approved_active_bunge_views() -> None:
    series = load_hemisphere_series_recipe(
        "recipes/art/five-phase-hemisphere-series.yml"
    )

    templates = tuple(
        composition_for_phase_template(series, "diamond", variant)
        for variant in TEMPLATE_VARIANTS
    )

    assert tuple(variant.slug for variant in TEMPLATE_VARIANTS) == (
        "standard",
        "azimuthal-60",
        "tilt-plus-20",
        "oblique-high",
    )
    assert tuple(template.phase_slug for template in templates) == ("diamond",) * 4
    assert tuple(template.orientation.euler_bunge_deg for template in templates) == (
        (17.0, 31.0, 43.0),
        (77.0, 31.0, 43.0),
        (17.0, 51.0, 43.0),
        (97.0, 71.0, 83.0),
    )
    assert all(template.orientation.frame == "crystal_to_sample" for template in templates)
