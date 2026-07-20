from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.clearance_selection import (
    select_standard_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
)
from kikuchi_lab.art_products.orientation_gallery_bundle import (
    OrientationGalleryCell,
    write_orientation_gallery_cell_bundle,
)
from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    load_orientation_gallery_recipe,
)
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.kinematical.reflector_parity import compare_reflector_evidence
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
GALLERY_RECIPE = ROOT / "recipes/art/five-phase-standard-orientation-gallery.yml"

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


@pytest.fixture(scope="module")
def gallery_cell() -> OrientationGalleryCell:
    gallery: OrientationGalleryRecipe = load_orientation_gallery_recipe(GALLERY_RECIPE)
    reflector_path = ROOT / "recipes/reflectors/quartz-art-bands.yml"
    reflector_recipe = load_direct_reflector_recipe(reflector_path)
    source = load_structure_record(
        (reflector_path.parent / reflector_recipe.source_record).resolve()
    )
    evidence = build_direct_reflector_evidence(source, reflector_recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    variant = gallery.variants[0]
    composition: HemisphereCompositionRecipe = replace(
        gallery.source_series.composition_for("quartz"),
        orientation=variant.orientation,
    )
    selection = select_standard_clearance_valid_tattoo_paths(catalog, composition)
    geometry = build_tattoo_geometry(selection, composition, width_scale=1.0)
    parity = compare_reflector_evidence(evidence, evidence).with_master(
        np.arange(2 * 65 * 65, dtype=np.float64).reshape(2, 65, 65)
    )
    parity.validate_for_publication()
    return OrientationGalleryCell(
        phase_slug="quartz",
        variant=variant,
        treatment=gallery.treatment,
        catalog=catalog,
        composition=composition,
        selection=selection,
        geometry=geometry,
        parity_report=parity,
    )


def test_cell_bundle_snapshots_direct_evidence_and_renders_geometry_only(
    tmp_path: Path,
    gallery_cell: OrientationGalleryCell,
) -> None:
    result = write_orientation_gallery_cell_bundle(tmp_path, cell=gallery_cell)

    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    assert result.path.name == result.run_id
    assert result.svg.name == "quartz-azimuthal-60.svg"
    assert result.stencil.name == "quartz-azimuthal-60-stencil.png"
    assert set(manifest["files"]) == {
        "quartz-azimuthal-60.svg",
        "quartz-azimuthal-60-stencil.png",
        "art-band-catalog.json",
        "hemisphere-composition-recipe.json",
        "band-selection-ledger.json",
        "path-geometry.json",
        "gallery-treatment-orientation.json",
        "reflector-parity-report.json",
        "scientific-claim.txt",
    }
    for name, checksum in manifest["files"].items():
        assert checksum["bytes"] == (result.path / name).stat().st_size
        assert len(checksum["sha256"]) == 64

    with Image.open(BytesIO(result.stencil.read_bytes())) as stencil:
        assert stencil.mode == "RGB"
        assert stencil.getpixel((0, 0)) == (255, 255, 255)
        assert stencil.getextrema() == ((0, 255), (0, 255), (0, 255))
    assert 'stroke="#000000"' in result.svg.read_text(encoding="utf-8")

    identity = manifest["run_identity"]
    assert identity["phase_slug"] == "quartz"
    assert identity["variant_id"] == gallery_cell.variant.variant_id
    assert identity["euler_bunge_deg"] == [77.0, 31.0, 43.0]
    assert identity["orientation_frame"] == "crystal_to_sample"
    assert identity["source_catalog_id"] == gallery_cell.catalog.catalog_id
    assert identity["parity_report_id"] == gallery_cell.parity_report.report_id
    assert identity["selection_id"] == gallery_cell.selection.selection_id
    assert identity["geometry_id"] == gallery_cell.geometry.geometry_id
    assert identity["simulation_count"] == 0


def test_byte_identical_cell_request_reuses_the_existing_bundle(
    tmp_path: Path,
    gallery_cell: OrientationGalleryCell,
) -> None:
    first = write_orientation_gallery_cell_bundle(tmp_path, cell=gallery_cell)
    second = write_orientation_gallery_cell_bundle(tmp_path, cell=gallery_cell)

    assert second == first


def test_divergent_existing_cell_bundle_is_never_replaced(
    tmp_path: Path,
    gallery_cell: OrientationGalleryCell,
) -> None:
    result = write_orientation_gallery_cell_bundle(tmp_path, cell=gallery_cell)
    result.stencil.write_bytes(b"divergent existing content")

    from kikuchi_lab.artifacts import BundleExistsError

    with pytest.raises(BundleExistsError, match="divergent"):
        write_orientation_gallery_cell_bundle(tmp_path, cell=gallery_cell)


def test_gallery_cell_rejects_an_ice_only_frozen_reference_substitution(
    gallery_cell: OrientationGalleryCell,
) -> None:
    with pytest.raises(ValueError, match="frozen Ice reference"):
        replace(
            gallery_cell,
            frozen_reference_id="frozen-tattoo-selection-f0e4f843362bab65",
        )
