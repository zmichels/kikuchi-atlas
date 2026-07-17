"""Native direct-vector renderer and immutable bundle for the 3-by-5 gallery."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kikuchi_lab.model.identity import plain_data, stable_id

from .contracts import TattooGeometry
from .orientation_gallery_bundle import _publish_idempotent_payload
from .orientation_gallery_recipe import OrientationGalleryVariant
from .tattoo_bundle import _ValidatedPayload, _sha256_bytes
from .tattoo_vector import validate_tattoo_geometry


ORIENTATION_GALLERY_PANEL_SIZE_PX = 900
ORIENTATION_GALLERY_RENDERER_VERSION = "direct-pillow-rgb-vector-v1"
_PHASE_ORDER = ("ice-ih", "forsterite", "quartz", "zircon", "titanite")
_VARIANT_ORDER = ("azimuthal-60", "tilt-plus-20", "oblique-high")
ORIENTATION_GALLERY_CELL_ORDER = tuple(
    f"{variant}:{phase}"
    for variant in _VARIANT_ORDER
    for phase in _PHASE_ORDER
)


@dataclass(frozen=True)
class OrientationGallerySheetCell:
    """One evidence-linked geometry cell in the fixed row-major gallery order."""

    phase_slug: str
    variant: OrientationGalleryVariant
    geometry: TattooGeometry
    source_catalog_id: str
    parity_report_id: str
    selection_id: str

    def __post_init__(self) -> None:
        if self.phase_slug not in _PHASE_ORDER:
            raise ValueError("orientation gallery sheet phase_slug is not approved")
        if not isinstance(self.variant, OrientationGalleryVariant):
            raise TypeError("orientation gallery sheet variant must be an OrientationGalleryVariant")
        if self.variant.slug not in _VARIANT_ORDER:
            raise ValueError("orientation gallery sheet variant is not approved")
        if not isinstance(self.geometry, TattooGeometry):
            raise TypeError("orientation gallery sheet geometry must be a TattooGeometry")
        for field in ("source_catalog_id", "parity_report_id", "selection_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"orientation gallery sheet {field} must be non-empty text")
        if self.geometry.catalog_id != self.source_catalog_id:
            raise ValueError("orientation gallery sheet geometry catalog does not match source")
        if self.geometry.orientation_id != self.variant.orientation.orientation_id:
            raise ValueError("orientation gallery sheet geometry does not match variant")
        validate_tattoo_geometry(self.geometry)

    @property
    def cell_id(self) -> str:
        return f"{self.variant.slug}:{self.phase_slug}"


@dataclass(frozen=True)
class RenderedOrientationGallerySheet:
    """Native comparison PNG and its content-normalized ledger."""

    comparison_png: bytes
    ledger: Mapping[str, object]
    cell_order: tuple[str, ...]


@dataclass(frozen=True)
class OrientationGallerySheetBundleResult:
    """The content-addressed location of one rendered comparison sheet."""

    run_id: str
    path: Path
    comparison_sheet: Path
    ledger_path: Path
    manifest_sha256: str


def _draw_geometry(panel: Image.Image, geometry: TattooGeometry) -> None:
    """Draw physical path vectors directly, matching the cell SVG geometry."""
    scale = ORIENTATION_GALLERY_PANEL_SIZE_PX / geometry.artboard_size_mm
    band_layer = Image.new("L", panel.size, 0)
    band_draw = ImageDraw.Draw(band_layer)
    for path in geometry.paths:
        points = [
            (float(point[0]) * scale, float(point[1]) * scale)
            for point in path.points_mm
        ]
        width_px = max(1, round(path.width_mm * scale))
        band_draw.line(points, fill=255, width=width_px, joint="curve")
        cap_radius = width_px / 2.0
        for x_coordinate, y_coordinate in points:
            band_draw.ellipse(
                (
                    x_coordinate - cap_radius,
                    y_coordinate - cap_radius,
                    x_coordinate + cap_radius,
                    y_coordinate + cap_radius,
                ),
                fill=255,
            )
    center_x, center_y = geometry.boundary.center_mm
    clip_radius_mm = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    clip = Image.new("L", panel.size, 0)
    ImageDraw.Draw(clip).ellipse(
        (
            (center_x - clip_radius_mm) * scale,
            (center_y - clip_radius_mm) * scale,
            (center_x + clip_radius_mm) * scale,
            (center_y + clip_radius_mm) * scale,
        ),
        fill=255,
    )
    panel.paste((0, 0, 0), mask=ImageChops.multiply(band_layer, clip))
    outer_radius_mm = geometry.boundary.outer_diameter_mm / 2.0
    ImageDraw.Draw(panel).ellipse(
        (
            (center_x - outer_radius_mm) * scale,
            (center_y - outer_radius_mm) * scale,
            (center_x + outer_radius_mm) * scale,
            (center_y + outer_radius_mm) * scale,
        ),
        outline=(0, 0, 0),
        width=round(geometry.boundary.width_mm * scale),
    )


def _draw_labels(
    panel: Image.Image,
    cell: OrientationGallerySheetCell,
    *,
    column: int,
) -> None:
    """Keep labels in the page margin above, never over the circular panel."""
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    if column == 0:
        draw.text((4, 3), cell.variant.slug, fill=(0, 0, 0), font=font)
        phase_x = 112
    else:
        phase_x = 4
    draw.text((phase_x, 3), cell.phase_slug, fill=(0, 0, 0), font=font)


def _cell_record(cell: OrientationGallerySheetCell, index: int) -> dict[str, object]:
    return {
        "cell_id": cell.cell_id,
        "cell_index": index,
        "row": index // len(_PHASE_ORDER),
        "column": index % len(_PHASE_ORDER),
        "phase_slug": cell.phase_slug,
        "variant_id": cell.variant.variant_id,
        "variant_slug": cell.variant.slug,
        "orientation_id": cell.variant.orientation.orientation_id,
        "euler_bunge_deg": list(cell.variant.orientation.euler_bunge_deg),
        "orientation_frame": cell.variant.orientation.frame,
        "selection_id": cell.selection_id,
        "geometry_id": cell.geometry.geometry_id,
        "source_catalog_id": cell.source_catalog_id,
        "parity_report_id": cell.parity_report_id,
        "simulation_count": 0,
        "renderer_version": ORIENTATION_GALLERY_RENDERER_VERSION,
        "panel_size_px": ORIENTATION_GALLERY_PANEL_SIZE_PX,
    }


def render_orientation_gallery_sheet(
    cells: Sequence[OrientationGallerySheetCell],
) -> RenderedOrientationGallerySheet:
    """Render the fixed 3-by-5 gallery directly from geometry path vectors."""
    ordered = tuple(cells)
    if len(ordered) != len(ORIENTATION_GALLERY_CELL_ORDER) or any(
        not isinstance(cell, OrientationGallerySheetCell) for cell in ordered
    ):
        raise ValueError("orientation gallery sheet requires exactly fifteen cells")
    cell_order = tuple(cell.cell_id for cell in ordered)
    if cell_order != ORIENTATION_GALLERY_CELL_ORDER:
        raise ValueError("orientation gallery sheet cells differ from the approved order")
    boundary = ordered[0].geometry.boundary.to_dict()
    if any(cell.geometry.boundary.to_dict() != boundary for cell in ordered[1:]):
        raise ValueError("orientation gallery sheet geometries must share one boundary")

    comparison = Image.new(
        "RGB",
        (
            len(_PHASE_ORDER) * ORIENTATION_GALLERY_PANEL_SIZE_PX,
            len(_VARIANT_ORDER) * ORIENTATION_GALLERY_PANEL_SIZE_PX,
        ),
        (255, 255, 255),
    )
    records: list[dict[str, object]] = []
    for index, cell in enumerate(ordered):
        record = _cell_record(cell, index)
        panel = Image.new(
            "RGB",
            (ORIENTATION_GALLERY_PANEL_SIZE_PX, ORIENTATION_GALLERY_PANEL_SIZE_PX),
            (255, 255, 255),
        )
        _draw_geometry(panel, cell.geometry)
        _draw_labels(panel, cell, column=record["column"])
        comparison.paste(
            panel,
            (
                record["column"] * ORIENTATION_GALLERY_PANEL_SIZE_PX,
                record["row"] * ORIENTATION_GALLERY_PANEL_SIZE_PX,
            ),
        )
        records.append(record)
    png = BytesIO()
    comparison.save(png, format="PNG", compress_level=9, optimize=False)
    ledger_content: dict[str, object] = {
        "schema_version": 1,
        "cell_order": list(cell_order),
        "layout": {
            "columns": 5,
            "rows": 3,
            "variant_row_order": list(_VARIANT_ORDER),
        },
        "renderer_version": ORIENTATION_GALLERY_RENDERER_VERSION,
        "panel_size_px": ORIENTATION_GALLERY_PANEL_SIZE_PX,
        "ink": "#000000",
        "background": "#ffffff",
        "cells": records,
    }
    ledger = {
        "ledger_id": stable_id("orientation-gallery-comparison-ledger", ledger_content),
        **ledger_content,
    }
    return RenderedOrientationGallerySheet(
        comparison_png=png.getvalue(),
        ledger=ledger,
        cell_order=cell_order,
    )


def _validated_sheet_payload(
    *,
    recipe_id: str,
    rendered: RenderedOrientationGallerySheet,
) -> tuple[str, _ValidatedPayload]:
    if not isinstance(recipe_id, str) or not recipe_id:
        raise ValueError("orientation gallery recipe_id must be non-empty text")
    if not isinstance(rendered, RenderedOrientationGallerySheet):
        raise TypeError("rendered must be a RenderedOrientationGallerySheet")
    if rendered.cell_order != ORIENTATION_GALLERY_CELL_ORDER:
        raise ValueError("orientation gallery rendered cell order differs from the contract")
    with Image.open(BytesIO(rendered.comparison_png)) as image:
        if image.mode not in {"RGB", "RGBA"} or image.size != (4500, 2700):
            raise ValueError("orientation gallery comparison PNG must be RGB/RGBA 4500 by 2700")
        if image.getpixel((0, 0))[:3] != (255, 255, 255):
            raise ValueError("orientation gallery comparison PNG must have a white background")
    ledger = plain_data(rendered.ledger)
    ledger_content = {key: value for key, value in ledger.items() if key != "ledger_id"}
    if ledger.get("ledger_id") != stable_id(
        "orientation-gallery-comparison-ledger", ledger_content
    ):
        raise ValueError("orientation gallery comparison ledger ID differs from content")
    if ledger.get("cell_order") != list(ORIENTATION_GALLERY_CELL_ORDER):
        raise ValueError("orientation gallery comparison ledger cell order differs")
    cells = ledger.get("cells")
    if not isinstance(cells, list) or len(cells) != 15:
        raise ValueError("orientation gallery comparison ledger must contain fifteen cells")
    run_identity = {
        "schema_version": 1,
        "recipe_id": recipe_id,
        "ledger_id": ledger["ledger_id"],
        "comparison_sha256": _sha256_bytes(rendered.comparison_png),
        "cell_order": list(rendered.cell_order),
        "simulation_count": 0,
        "renderer_version": ORIENTATION_GALLERY_RENDERER_VERSION,
        "panel_size_px": ORIENTATION_GALLERY_PANEL_SIZE_PX,
    }
    run_id = stable_id("orientation-gallery-sheet", run_identity)
    return run_id, _ValidatedPayload(
        run_identity=run_identity,
        files={
            "orientation-gallery-comparison.png": rendered.comparison_png,
            "orientation-gallery-comparison-ledger.json": ledger,
        },
        payload_order=(
            "orientation-gallery-comparison.png",
            "orientation-gallery-comparison-ledger.json",
        ),
    )


def write_orientation_gallery_sheet_bundle(
    output_root: str | Path,
    *,
    recipe_id: str,
    rendered: RenderedOrientationGallerySheet,
) -> OrientationGallerySheetBundleResult:
    """Atomically publish one content-addressed native comparison sheet."""
    run_id, payload = _validated_sheet_payload(recipe_id=recipe_id, rendered=rendered)
    path, manifest_sha256 = _publish_idempotent_payload(
        output_root,
        run_id=run_id,
        payload=payload,
    )
    return OrientationGallerySheetBundleResult(
        run_id=run_id,
        path=path,
        comparison_sheet=path / "orientation-gallery-comparison.png",
        ledger_path=path / "orientation-gallery-comparison-ledger.json",
        manifest_sha256=manifest_sha256,
    )


__all__ = [
    "ORIENTATION_GALLERY_CELL_ORDER",
    "ORIENTATION_GALLERY_PANEL_SIZE_PX",
    "ORIENTATION_GALLERY_RENDERER_VERSION",
    "OrientationGallerySheetBundleResult",
    "OrientationGallerySheetCell",
    "RenderedOrientationGallerySheet",
    "render_orientation_gallery_sheet",
    "write_orientation_gallery_sheet_bundle",
]
