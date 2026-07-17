"""Immutable contracts for science-art products derived from Kikuchi evidence."""

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.clearance_selection import (
    ClearanceSelectionFeasibilityError,
    select_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.contracts import (
    ArtBandCatalog,
    ArtBandMember,
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.art_products.frozen_selection import (
    FrozenTattooPath,
    FrozenTattooSelection,
    bind_frozen_tattoo_selection,
    load_frozen_tattoo_selection,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
    HemisphereSeriesRecipe,
    HemisphereTreatment,
    load_hemisphere_series_recipe,
)
from kikuchi_lab.art_products.tattoo_vector import TattooClearanceError
from kikuchi_lab.art_products.series_sheet import (
    RenderedSeriesSheet,
    SeriesSheetBundleResult,
    SeriesSheetCell,
    render_series_sheet,
    write_series_sheet_bundle,
)


__all__ = [
    "ArtBandCatalog",
    "ArtBandMember",
    "ClearanceSelectionFeasibilityError",
    "FrozenTattooPath",
    "FrozenTattooSelection",
    "HemisphereCompositionRecipe",
    "HemisphereSeriesRecipe",
    "HemisphereTreatment",
    "RenderedSeriesSheet",
    "SeriesSheetBundleResult",
    "SeriesSheetCell",
    "TattooBoundary",
    "TattooClearanceError",
    "TattooGeometry",
    "TattooPath",
    "bind_frozen_tattoo_selection",
    "build_art_band_catalog_from_evidence",
    "load_frozen_tattoo_selection",
    "load_hemisphere_series_recipe",
    "render_series_sheet",
    "select_clearance_valid_tattoo_paths",
    "write_series_sheet_bundle",
]
