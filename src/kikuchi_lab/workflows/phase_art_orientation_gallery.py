"""Zero-master, all-preflight publication for the 3-by-5 phase orientation gallery."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from kikuchi_lab.art_products.clearance_selection import (
    select_standard_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.orientation_gallery_bundle import (
    OrientationGalleryCell,
    OrientationGalleryCellBundleResult,
    write_orientation_gallery_cell_bundle,
)
from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    load_orientation_gallery_recipe,
)
from kikuchi_lab.art_products.orientation_gallery_sheet import (
    OrientationGallerySheetBundleResult,
    render_orientation_gallery_sheet,
    write_orientation_gallery_sheet_bundle,
)
from kikuchi_lab.art_products.tattoo_vector import build_tattoo_geometry
from kikuchi_lab.artifacts import BundleExistsError

from .direct_phase_preflight import (
    build_parity_gated_direct_phase,
    load_passed_parity_reports,
)


@dataclass(frozen=True)
class PhaseArtOrientationGalleryResult:
    """Published cell bundles and one recipe-bound comparison under a gallery root."""

    path: Path
    cell_bundles: tuple[OrientationGalleryCellBundleResult, ...]
    comparison_id: str
    comparison_sheet: Path
    ledger_path: Path
    simulation_count: int
    cell_order: tuple[str, ...]
    manifest_sha256: str


def _expected_cell_order(recipe: OrientationGalleryRecipe) -> tuple[str, ...]:
    return tuple(
        f"{variant.slug}:{phase_slug}"
        for variant in recipe.variants
        for phase_slug in recipe.phase_order
    )


def _preflight_cells(recipe: OrientationGalleryRecipe, parity_root: str | Path) -> tuple[
    OrientationGalleryCell, ...
]:
    reports = load_passed_parity_reports(parity_root)
    direct_by_phase = {
        phase_slug: build_parity_gated_direct_phase(
            recipe_file=recipe.source_series_path,
            series=recipe.source_series,
            phase_slug=phase_slug,
            reports=reports,
        )
        for phase_slug in recipe.phase_order
    }
    cells: list[OrientationGalleryCell] = []
    for variant in recipe.variants:
        for phase_slug in recipe.phase_order:
            direct = direct_by_phase[phase_slug]
            composition = replace(
                recipe.source_series.composition_for(phase_slug),
                orientation=variant.orientation,
            )
            selection = select_standard_clearance_valid_tattoo_paths(
                direct.catalog,
                composition,
            )
            geometry = build_tattoo_geometry(
                selection,
                composition,
                width_scale=1.0,
            )
            cells.append(
                OrientationGalleryCell(
                    phase_slug=phase_slug,
                    variant=variant,
                    treatment=recipe.treatment,
                    catalog=direct.catalog,
                    composition=composition,
                    selection=selection,
                    geometry=geometry,
                    parity_report=direct.parity,
                )
            )
    return tuple(cells)


def _validate_preflighted_cells(
    recipe: OrientationGalleryRecipe,
    cells: tuple[OrientationGalleryCell, ...],
) -> None:
    expected_order = _expected_cell_order(recipe)
    cell_order = tuple(cell.cell_id for cell in cells)
    if cell_order != expected_order or len(cells) != 15:
        raise ValueError("orientation gallery preflight cells differ from the approved inventory")
    if len(set(cell_order)) != len(cell_order):
        raise ValueError("orientation gallery preflight cell IDs must be unique")
    if any(
        cell.treatment.name != "standard"
        or cell.treatment.arc_width_scale != 1.0
        or cell.geometry.orientation_id != cell.variant.orientation.orientation_id
        for cell in cells
    ):
        raise ValueError("orientation gallery preflight cells must use standard geometry")
    if any(cell.parity_report.simulation_count != 1 for cell in cells):
        raise ValueError("orientation gallery cells require published parity evidence")
    rendered = render_orientation_gallery_sheet(recipe, cells)
    if rendered.cell_order != expected_order:
        raise ValueError("orientation gallery preflight sheet order differs from the recipe")


def _relocate_cell_bundle(
    bundle: OrientationGalleryCellBundleResult,
    output_root: Path,
) -> OrientationGalleryCellBundleResult:
    path = output_root / bundle.run_id
    return OrientationGalleryCellBundleResult(
        run_id=bundle.run_id,
        path=path,
        svg=path / bundle.svg.name,
        stencil=path / bundle.stencil.name,
        manifest_sha256=bundle.manifest_sha256,
    )


def _relocate_sheet_bundle(
    bundle: OrientationGallerySheetBundleResult,
    output_root: Path,
) -> OrientationGallerySheetBundleResult:
    path = output_root / bundle.run_id
    return OrientationGallerySheetBundleResult(
        run_id=bundle.run_id,
        path=path,
        comparison_sheet=path / bundle.comparison_sheet.name,
        ledger_path=path / bundle.ledger_path.name,
        manifest_sha256=bundle.manifest_sha256,
    )


def render_phase_art_orientation_gallery(
    *,
    recipe_path: str | Path,
    parity_root: str | Path,
    output_root: str | Path,
) -> PhaseArtOrientationGalleryResult:
    """Preflight all 15 cells, then atomically promote one new gallery root."""
    recipe = load_orientation_gallery_recipe(recipe_path)
    cells = _preflight_cells(recipe, parity_root)
    _validate_preflighted_cells(recipe, cells)

    requested_root = Path(output_root).resolve()
    if requested_root.exists():
        raise BundleExistsError(
            f"orientation gallery root already exists: {requested_root}"
        )
    requested_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{requested_root.name}-staging-",
            dir=requested_root.parent,
        )
    )
    try:
        staged_cells = tuple(
            write_orientation_gallery_cell_bundle(staging, cell=cell) for cell in cells
        )
        staged_sheet = write_orientation_gallery_sheet_bundle(
            staging,
            recipe=recipe,
            cells=cells,
        )
        os.replace(staging, requested_root)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    published_cells = tuple(
        _relocate_cell_bundle(bundle, requested_root) for bundle in staged_cells
    )
    published_sheet = _relocate_sheet_bundle(staged_sheet, requested_root)
    return PhaseArtOrientationGalleryResult(
        path=requested_root,
        cell_bundles=published_cells,
        comparison_id=published_sheet.run_id,
        comparison_sheet=published_sheet.comparison_sheet,
        ledger_path=published_sheet.ledger_path,
        simulation_count=0,
        cell_order=_expected_cell_order(recipe),
        manifest_sha256=published_sheet.manifest_sha256,
    )


__all__ = [
    "PhaseArtOrientationGalleryResult",
    "render_phase_art_orientation_gallery",
]
