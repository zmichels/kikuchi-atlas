from __future__ import annotations

from copy import copy
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
from kikuchi_lab.art_products.orientation_gallery_bundle import OrientationGalleryCell
from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    OrientationGalleryVariant,
    load_orientation_gallery_recipe,
)
from kikuchi_lab.art_products.orientation_gallery_sheet import (
    ORIENTATION_GALLERY_CELL_ORDER,
    ORIENTATION_GALLERY_PANEL_SIZE_PX,
    RenderedOrientationGallerySheet,
    render_orientation_gallery_sheet,
    write_orientation_gallery_sheet_bundle,
)
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.kinematical.reflector_parity import compare_reflector_evidence
from kikuchi_lab.model.recipes import Orientation
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
def gallery_recipe() -> OrientationGalleryRecipe:
    return load_orientation_gallery_recipe(GALLERY_RECIPE)


@pytest.fixture(scope="module")
def gallery_cells(
    gallery_recipe: OrientationGalleryRecipe,
) -> tuple[OrientationGalleryCell, ...]:
    cells: list[OrientationGalleryCell] = []
    for phase_slug in gallery_recipe.phase_order:
        reflector_path = (
            GALLERY_RECIPE.parent
            / gallery_recipe.source_series.reflector_recipes[phase_slug]
        ).resolve()
        reflector_recipe = load_direct_reflector_recipe(reflector_path)
        source = load_structure_record(
            (reflector_path.parent / reflector_recipe.source_record).resolve()
        )
        evidence = build_direct_reflector_evidence(source, reflector_recipe)
        catalog = build_art_band_catalog_from_evidence(evidence)
        parity = compare_reflector_evidence(evidence, evidence).with_master(
            np.arange(2 * 65 * 65, dtype=np.float64).reshape(2, 65, 65)
        )
        parity.validate_for_publication()
        for variant in gallery_recipe.variants:
            composition: HemisphereCompositionRecipe = replace(
                gallery_recipe.source_series.composition_for(phase_slug),
                orientation=variant.orientation,
            )
            selection = select_standard_clearance_valid_tattoo_paths(
                catalog, composition
            )
            geometry = build_tattoo_geometry(selection, composition, width_scale=1.0)
            cells.append(
                OrientationGalleryCell(
                    phase_slug=phase_slug,
                    variant=variant,
                    treatment=gallery_recipe.treatment,
                    catalog=catalog,
                    composition=composition,
                    selection=selection,
                    geometry=geometry,
                    parity_report=parity,
                )
            )
    return tuple(
        next(
            cell
            for cell in cells
            if cell.cell_id == f"{variant}:{phase_slug}"
        )
        for variant, phase_slug in (
            cell_id.split(":") for cell_id in ORIENTATION_GALLERY_CELL_ORDER
        )
    )


def _forged(
    cell: OrientationGalleryCell,
    **changes: object,
) -> OrientationGalleryCell:
    forged = copy(cell)
    for field, value in changes.items():
        object.__setattr__(forged, field, value)
    return forged


def _with_first(
    cells: tuple[OrientationGalleryCell, ...],
    first: OrientationGalleryCell,
) -> tuple[OrientationGalleryCell, ...]:
    return (first, *cells[1:])


def _complete_substitute_cell(
    gallery_recipe: OrientationGalleryRecipe,
    gallery_cells: tuple[OrientationGalleryCell, ...],
    *,
    slot_phase_slug: str,
    provenance_phase_slug: str,
    variant: OrientationGalleryVariant,
) -> OrientationGalleryCell:
    source_cell = next(
        cell
        for cell in gallery_cells
        if cell.phase_slug == provenance_phase_slug
        and cell.variant.slug == variant.slug
    )
    composition = replace(
        gallery_recipe.source_series.composition_for(slot_phase_slug),
        orientation=variant.orientation,
    )
    selection = select_standard_clearance_valid_tattoo_paths(
        source_cell.catalog, composition
    )
    geometry = build_tattoo_geometry(selection, composition, width_scale=1.0)
    return OrientationGalleryCell(
        phase_slug=slot_phase_slug,
        variant=variant,
        treatment=gallery_recipe.treatment,
        catalog=source_cell.catalog,
        composition=composition,
        selection=selection,
        geometry=geometry,
        parity_report=source_cell.parity_report,
    )


def test_native_sheet_is_a_direct_labeled_three_by_five_vector_render(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Image.Image,
        "resize",
        lambda *_args, **_kwargs: pytest.fail("sheet resized imported raster content"),
    )

    rendered = render_orientation_gallery_sheet(gallery_recipe, gallery_cells)

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
        assert record["treatment"] == "standard"
        assert record["arc_width_scale"] == 1.0


def test_sheet_revalidates_a_false_phase_label_before_rendering(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    forged = _forged(gallery_cells[0], phase_slug="quartz")

    with pytest.raises(ValueError, match="phase_slug"):
        render_orientation_gallery_sheet(gallery_recipe, _with_first(gallery_cells, forged))


def test_sheet_revalidates_a_false_variant_orientation_before_rendering(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    forged = _forged(gallery_cells[0], variant=gallery_recipe.variants[1])

    with pytest.raises(ValueError, match="variant orientation"):
        render_orientation_gallery_sheet(gallery_recipe, _with_first(gallery_cells, forged))


def test_sheet_rejects_another_phases_geometry_before_rendering(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    forged = _forged(gallery_cells[0], geometry=gallery_cells[1].geometry)

    with pytest.raises(ValueError, match="geometry catalog"):
        render_orientation_gallery_sheet(gallery_recipe, _with_first(gallery_cells, forged))


def test_sheet_rejects_wide_geometry_and_nonstandard_treatment_before_rendering(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    wide_geometry = build_tattoo_geometry(
        gallery_cells[0].selection,
        gallery_cells[0].composition,
        width_scale=1.15,
    )
    wide_geometry_cell = _forged(gallery_cells[0], geometry=wide_geometry)
    wide_treatment_cell = _forged(
        gallery_cells[0],
        treatment=gallery_recipe.source_series.treatments["wide"],
    )

    with pytest.raises(ValueError, match="standard geometry"):
        render_orientation_gallery_sheet(
            gallery_recipe, _with_first(gallery_cells, wide_geometry_cell)
        )
    with pytest.raises(ValueError, match="standard treatment"):
        render_orientation_gallery_sheet(
            gallery_recipe, _with_first(gallery_cells, wide_treatment_cell)
        )


def test_sheet_rejects_a_complete_substitute_phase_cell_not_configured_for_slot(
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    substitute = _complete_substitute_cell(
        gallery_recipe,
        gallery_cells,
        slot_phase_slug="ice-ih",
        provenance_phase_slug="quartz",
        variant=gallery_recipe.variants[0],
    )

    with pytest.raises(ValueError, match="direct-reflector provenance"):
        render_orientation_gallery_sheet(
            gallery_recipe, _with_first(gallery_cells, substitute)
        )


def test_sheet_bundle_rejects_a_complete_arbitrary_bunge_variant_under_approved_slug(
    tmp_path: Path,
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    arbitrary_variant = OrientationGalleryVariant(
        slug="azimuthal-60",
        orientation=Orientation(
            euler_bunge_deg=(13.0, 23.0, 33.0),
            frame="crystal_to_sample",
        ),
    )
    substitute = _complete_substitute_cell(
        gallery_recipe,
        gallery_cells,
        slot_phase_slug="ice-ih",
        provenance_phase_slug="ice-ih",
        variant=arbitrary_variant,
    )

    with pytest.raises(ValueError, match="canonical variant"):
        write_orientation_gallery_sheet_bundle(
            tmp_path,
            recipe=gallery_recipe,
            cells=_with_first(gallery_cells, substitute),
        )


def test_sheet_bundle_derives_from_cells_and_rejects_caller_rendered_bytes(
    tmp_path: Path,
    gallery_cells: tuple[OrientationGalleryCell, ...],
    gallery_recipe: OrientationGalleryRecipe,
) -> None:
    result = write_orientation_gallery_sheet_bundle(
        tmp_path,
        recipe=gallery_recipe,
        cells=gallery_cells,
    )
    assert result.comparison_sheet.is_file()
    assert result.ledger_path.is_file()
    forged = RenderedOrientationGallerySheet(
        comparison_png=b"forged imported raster",
        ledger={
            "ledger_id": "orientation-gallery-comparison-ledger-forged",
            "cells": [{"simulation_count": 1}],
        },
        cell_order=ORIENTATION_GALLERY_CELL_ORDER,
    )

    with pytest.raises(ValueError, match="caller-provided rendered"):
        write_orientation_gallery_sheet_bundle(
            tmp_path,
            recipe=gallery_recipe,
            cells=gallery_cells,
            rendered=forged,
        )
