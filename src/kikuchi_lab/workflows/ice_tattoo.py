"""Primary Ice tattoo workflow from a strict retained art-band catalog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.art_products.catalog import load_art_band_catalog
from kikuchi_lab.art_products.tattoo_bundle import DISCLAIMER_TEXT, write_tattoo_bundle
from kikuchi_lab.art_products.tattoo_recipe import load_tattoo_recipe
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)


@dataclass(frozen=True)
class IceTattooResult:
    """Published primary tattoo identities and retained bundle location."""

    run_id: str
    path: Path
    catalog_id: str
    selection_id: str
    geometry_id: str
    treatment: str
    manifest_sha256: str


def render_ice_tattoo(
    *,
    catalog_path: str | Path,
    recipe_path: str | Path,
    output_root: str | Path,
    treatment: str,
) -> IceTattooResult:
    """Rebuild strict primary geometry and publish all canonical derivatives."""
    if treatment == "graywash":
        raise ValueError("graywash requires accepted primary geometry")
    if treatment != "primary":
        raise ValueError("tattoo treatment must be primary or graywash")

    catalog = load_art_band_catalog(catalog_path)
    recipe = load_tattoo_recipe(recipe_path)
    selection = select_tattoo_paths(catalog, recipe)
    geometry = build_tattoo_geometry(selection, recipe)
    rendered = render_primary_tattoo(geometry)
    bundle = write_tattoo_bundle(
        output_root,
        catalog=catalog,
        recipe=recipe,
        selection=selection,
        geometry=geometry,
        rendered=rendered,
        treatment=treatment,
        disclaimer=DISCLAIMER_TEXT,
    )
    return IceTattooResult(
        run_id=bundle.run_id,
        path=bundle.path,
        catalog_id=catalog.catalog_id,
        selection_id=selection.selection_id,
        geometry_id=geometry.geometry_id,
        treatment=treatment,
        manifest_sha256=bundle.manifest_sha256,
    )


__all__ = ["IceTattooResult", "render_ice_tattoo"]
