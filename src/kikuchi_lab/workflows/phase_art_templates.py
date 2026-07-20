"""Reusable standard-width direct-reflector tattoo template publication."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from kikuchi_lab.art_products.catalog import load_art_band_catalog
from kikuchi_lab.art_products.clearance_selection import (
    select_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.hemisphere_bundle import (
    PhaseHemisphereBundleResult,
    write_phase_hemisphere_bundle,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
    HemisphereSeriesRecipe,
    HemisphereTreatment,
)
from kikuchi_lab.art_products.tattoo_bundle import DISCLAIMER_TEXT
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)
from kikuchi_lab.model.recipes import Orientation


@dataclass(frozen=True)
class PhaseArtTemplateVariant:
    """One named active crystal-to-sample view for a print template."""

    slug: str
    orientation: Orientation

    def __post_init__(self) -> None:
        if self.orientation.frame != "crystal_to_sample":
            raise ValueError("template orientation must be crystal_to_sample")


TEMPLATE_VARIANTS = (
    PhaseArtTemplateVariant(
        "standard", Orientation((17.0, 31.0, 43.0), frame="crystal_to_sample")
    ),
    PhaseArtTemplateVariant(
        "azimuthal-60", Orientation((77.0, 31.0, 43.0), frame="crystal_to_sample")
    ),
    PhaseArtTemplateVariant(
        "tilt-plus-20", Orientation((17.0, 51.0, 43.0), frame="crystal_to_sample")
    ),
    PhaseArtTemplateVariant(
        "oblique-high", Orientation((97.0, 71.0, 83.0), frame="crystal_to_sample")
    ),
)


@dataclass(frozen=True)
class PhaseArtTemplateResult:
    """Published standard-width template bundles for one direct-reflector phase."""

    phase_slug: str
    bundles: tuple[tuple[PhaseArtTemplateVariant, PhaseHemisphereBundleResult], ...]

    @property
    def standard_bundle(self) -> PhaseHemisphereBundleResult:
        return self.bundles[0][1]


def composition_for_phase_template(
    series: HemisphereSeriesRecipe,
    phase_slug: str,
    variant: PhaseArtTemplateVariant,
) -> HemisphereCompositionRecipe:
    """Reuse the reviewed template policy with a new phase and active orientation."""
    if not isinstance(variant, PhaseArtTemplateVariant):
        raise TypeError("variant must be a PhaseArtTemplateVariant")
    base = series.composition_for(series.phase_order[0])
    return replace(base, phase_slug=phase_slug, orientation=variant.orientation)


def render_phase_art_templates(
    *,
    phase_slug: str,
    catalog_path: str | Path,
    series: HemisphereSeriesRecipe,
    output_root: str | Path,
    treatment: HemisphereTreatment | None = None,
) -> PhaseArtTemplateResult:
    """Publish active-orientation, standard-width templates from one saved catalog."""
    selected_treatment = series.treatments["standard"] if treatment is None else treatment
    if selected_treatment.name != "standard" or selected_treatment.arc_width_scale != 1.0:
        raise ValueError("phase art templates require the standard treatment")
    catalog = load_art_band_catalog(catalog_path)
    bundles: list[tuple[PhaseArtTemplateVariant, PhaseHemisphereBundleResult]] = []
    for variant in TEMPLATE_VARIANTS:
        composition = composition_for_phase_template(series, phase_slug, variant)
        selection = select_clearance_valid_tattoo_paths(catalog, composition)
        geometry = build_tattoo_geometry(selection, composition, width_scale=1.0)
        bundle = write_phase_hemisphere_bundle(
            output_root,
            phase_slug=phase_slug,
            treatment=selected_treatment,
            catalog=catalog,
            recipe=composition,
            selection=selection,
            geometry=geometry,
            rendered=render_primary_tattoo(geometry),
            disclaimer=DISCLAIMER_TEXT,
        )
        bundles.append((variant, bundle))
    return PhaseArtTemplateResult(phase_slug=phase_slug, bundles=tuple(bundles))


__all__ = [
    "PhaseArtTemplateResult",
    "PhaseArtTemplateVariant",
    "TEMPLATE_VARIANTS",
    "composition_for_phase_template",
    "render_phase_art_templates",
]
