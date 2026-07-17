from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from kikuchi_lab.art_products.hemisphere_recipe import (
    load_hemisphere_series_recipe,
)
from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.series_sheet import (
    PANEL_RENDERER_VERSION,
    PANEL_SIZE_PX,
    SeriesSheetCell,
    render_series_sheet,
    write_series_sheet_bundle,
)
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import load_direct_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"
CELL_ORDER = (
    "ice-ih:standard",
    "ice-ih:wide",
    "forsterite:standard",
    "forsterite:wide",
    "quartz:standard",
    "quartz:wide",
    "zircon:standard",
    "zircon:wide",
    "titanite:standard",
    "titanite:wide",
)

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


@pytest.fixture(scope="module")
def sheet_cells() -> tuple[SeriesSheetCell, ...]:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    composition = series.composition_for("quartz")
    reflector_path = ROOT / "recipes/reflectors/quartz-art-bands.yml"
    reflector_recipe = load_direct_reflector_recipe(reflector_path)
    source = load_structure_record(
        (reflector_path.parent / reflector_recipe.source_record).resolve()
    )
    evidence = build_direct_reflector_evidence(source, reflector_recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    selection = select_tattoo_paths(catalog, composition)
    standard = build_tattoo_geometry(selection, composition, width_scale=1.0)
    wide = build_tattoo_geometry(selection, composition, width_scale=1.15)
    return tuple(
        SeriesSheetCell(
            phase_slug=phase_slug,
            treatment=treatment,
            geometry=standard if treatment == "standard" else wide,
            bundle_id=f"{phase_slug}-{treatment}-run-0123456789abcdef",
            selection_id=selection.selection_id,
            source_kind="reference" if cell_id == "ice-ih:standard" else "bundle",
        )
        for cell_id in CELL_ORDER
        for phase_slug, treatment in (cell_id.split(":"),)
    )


def test_sheet_draws_direct_900_pixel_panels_with_exact_ledger(
    sheet_cells: tuple[SeriesSheetCell, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Image.Image,
        "resize",
        lambda *_args, **_kwargs: pytest.fail("comparison resized a prior PNG"),
    )
    rendered = render_series_sheet(sheet_cells)

    with Image.open(BytesIO(rendered.comparison_png)) as image:
        assert image.size == (5 * PANEL_SIZE_PX, 2 * PANEL_SIZE_PX)
        assert image.mode == "1"
        assert image.getextrema() == (0, 255)
    assert PANEL_SIZE_PX == 900
    assert tuple(rendered.ledger["cell_order"]) == CELL_ORDER
    assert len(rendered.ledger["cells"]) == 10
    for index, (cell, expected_id) in enumerate(
        zip(rendered.ledger["cells"], CELL_ORDER, strict=True)
    ):
        assert cell["cell_id"] == expected_id
        assert cell["cell_index"] == index
        assert cell["panel_size_px"] == 900
        assert cell["renderer_version"] == PANEL_RENDERER_VERSION
        assert cell["geometry_id"].startswith("tattoo-geometry-")
        assert cell["selection_id"].startswith("tattoo-selection-")
        assert cell["orientation_id"].startswith("orientation-")
        assert cell["bundle_id"] == sheet_cells[index].bundle_id
    assert rendered.ledger["layout"] == {
        "columns": 5,
        "rows": 2,
        "row_order": ["standard", "wide"],
    }
    assert rendered.ledger["ink"] == "#000000"
    assert rendered.ledger["background"] == "#ffffff"
    assert rendered.ledger["stroke_clip_radius_mm"] == 63.8
    assert rendered.ledger["outer_boundary"] == {
        "outer_diameter_mm": 132.0,
        "stroke_width_mm": 2.2,
    }


def test_sheet_bundle_is_content_identified_atomic_and_no_replace(
    tmp_path: Path,
    sheet_cells: tuple[SeriesSheetCell, ...],
) -> None:
    rendered = render_series_sheet(sheet_cells)
    result = write_series_sheet_bundle(
        tmp_path,
        recipe_id="hemisphere-series-recipe-0123456789abcdef",
        rendered=rendered,
    )

    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.path.name == result.series_id
    assert manifest["run_id"] == result.series_id
    assert set(manifest["files"]) == {
        "comparison.png",
        "comparison-ledger.json",
    }
    assert result.comparison_sheet == result.path / "comparison.png"
    assert result.cell_order == CELL_ORDER

    from kikuchi_lab.artifacts import BundleExistsError

    with pytest.raises(BundleExistsError, match="already exists"):
        write_series_sheet_bundle(
            tmp_path,
            recipe_id="hemisphere-series-recipe-0123456789abcdef",
            rendered=rendered,
        )
