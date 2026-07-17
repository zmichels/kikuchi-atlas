"""Immutable contracts for science-art products derived from Kikuchi evidence."""

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
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


__all__ = [
    "ArtBandCatalog",
    "ArtBandMember",
    "FrozenTattooPath",
    "FrozenTattooSelection",
    "TattooBoundary",
    "TattooGeometry",
    "TattooPath",
    "bind_frozen_tattoo_selection",
    "build_art_band_catalog_from_evidence",
    "load_frozen_tattoo_selection",
]
