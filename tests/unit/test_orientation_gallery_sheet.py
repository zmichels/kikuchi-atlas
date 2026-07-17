from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.clearance_selection import (
    select_standard_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
)
from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    load_orientation_gallery_recipe,
)
from kikuchi_lab.art_products.orientation_gallery_sheet import (
    ORIENTATION_GALLERY_CELL_ORDER,
    ORIENTATION_GALLERY_PANEL_SIZE_PX,
    OrientationGallerySheetCell,
    render_orientation_gallery_sheet,
)
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
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
def sheet_cells() -> tuple[OrientationGallerySheetCell, ...]:
    gallery: OrientationGalleryRecipe = load_orientation_gallery_recipe(GALLERY_RECIPE)
    reflector_path = ROOT / "recipes/reflectors/quartz-art-bands.yml"
    reflector_recipe = load_direct_reflector_recipe(reflector_path)
    source = load_structure_record(
        (reflector_path.parent / reflector_recipe.source_record).resolve()
    )
    evidence = build_direct_reflector_evidence(source, reflector_recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    geometries = {}
    selections = {}
    for variant in gallery.variants:
        composition: HemisphereCompositionRecipe = replace(
            gallery.source_series.composition_for("quartz"),
            orientation=variant.orientation,
        )
        selection = select_standard_clearance_valid_tattoo_paths(catalog, composition)
        geometries[variant.slug] = build_tattoo_geometry(
            selection, composition, width_scale=1.0
        )
        selections[variant.slug] = selection

    return tuple(
        OrientationGallerySheetCell(
            phase_slug=phase_slug,
            variant=variant,
            geometry=replace(
                geometries[variant.slug],
                orientation_id=variant.orientation.orientation_id,
            ),
            source_catalog_id=catalog.catalog_id,
            parity_report_id="reflector-parity-report-sheet-fixture",
            selection_id=selections[variant.slug].selection_id,
        )
        for variant in gallery.variants
        for phase_slug in gallery.phase_order
    )


def test_native_sheet_is_a_direct_labeled_three_by_five_vector_render(
    sheet_cells: tuple[OrientationGallerySheetCell, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Image.Image,
        "resize",
        lambda *_args, **_kwargs: pytest.fail("sheet resized imported raster content"),
    )

    rendered = render_orientation_gallery_sheet(sheet_cells)

    with Image.open(BytesIO(rendered.comparison_png)) as image:
        assert image.size == (4500, 2700)
        assert image.mode in {"RGB", "RGBA"}
        assert image.getpixel((0, 0))[:3] == (255, 255, 255)
        assert image.getextrema()[0] == (0, 255)
        for row in range(3):
            for column in range(5):
                center_x = column * ORIENTATION_GALLERY_PANEL_SIZE_PX + 450
                center_y = row * ORIENTATION_GALLERY_PANEL_SIZE_PX + 41
                assert image.getpixel((center_x, center_y))[:3] == (0, 0, 0)
                assert image.getpixel((center_x, center_y - 30))[:3] != (0, 0, 0)

    assert ORIENTATION_GALLERY_PANEL_SIZE_PX == 900
    assert rendered.cell_order == ORIENTATION_GALLERY_CELL_ORDER
    assert len(rendered.ledger["cells"]) == 15
    assert rendered.ledger["layout"] == {
        "columns": 5,
        "rows": 3,
        "variant_row_order": ["azimuthal-60", "tilt-plus-20", "oblique-high"],
    }
    for index, record in enumerate(rendered.ledger["cells"]):
        expected_variant, expected_phase = ORIENTATION_GALLERY_CELL_ORDER[index].split(":")
        assert record["cell_index"] == index
        assert record["variant_slug"] == expected_variant
        assert record["phase_slug"] == expected_phase
        assert record["row"] == index // 5
        assert record["column"] == index % 5
        assert record["panel_size_px"] == 900
        assert record["simulation_count"] == 0
