"""Direct vector-geometry rendering and publication for the phase series sheet."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kikuchi_lab.model.identity import plain_data, stable_id

from .contracts import TattooGeometry
from .tattoo_bundle import (
    _ValidatedPayload,
    _publish_validated_payload,
    _sha256_bytes,
)
from .tattoo_vector import validate_tattoo_geometry


PANEL_SIZE_PX = 900
PANEL_RENDERER_VERSION = "direct-pillow-binary-vector-v1"
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
_PHASE_ORDER = ("ice-ih", "forsterite", "quartz", "zircon", "titanite")
_ROW_ORDER = ("standard", "wide")


@dataclass(frozen=True)
class SeriesSheetCell:
    """One content-identified geometry placed in the comparison grid."""

    phase_slug: str
    treatment: Literal["standard", "wide"]
    geometry: TattooGeometry
    bundle_id: str
    selection_id: str
    source_kind: Literal["reference", "bundle"]

    def __post_init__(self) -> None:
        if self.phase_slug not in _PHASE_ORDER:
            raise ValueError("series sheet phase_slug is not in the approved order")
        if self.treatment not in _ROW_ORDER:
            raise ValueError("series sheet treatment must be standard or wide")
        if not isinstance(self.geometry, TattooGeometry):
            raise TypeError("series sheet geometry must be a TattooGeometry")
        for field in ("bundle_id", "selection_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"series sheet {field} must be non-empty text")
        if self.source_kind not in {"reference", "bundle"}:
            raise ValueError("series sheet source_kind must be reference or bundle")
        validate_tattoo_geometry(self.geometry)

    @property
    def cell_id(self) -> str:
        return f"{self.phase_slug}:{self.treatment}"


@dataclass(frozen=True)
class RenderedSeriesSheet:
    """Fully validated comparison bytes and their complete ledger."""

    comparison_png: bytes
    ledger: Mapping[str, object]
    cell_order: tuple[str, ...]


@dataclass(frozen=True)
class SeriesSheetBundleResult:
    """Published comparison-series identity and canonical paths."""

    series_id: str
    path: Path
    comparison_sheet: Path
    cell_order: tuple[str, ...]
    manifest_sha256: str


def _draw_geometry(panel: Image.Image, geometry: TattooGeometry) -> None:
    scale = PANEL_SIZE_PX / geometry.artboard_size_mm
    band_layer = Image.new("1", panel.size, 0)
    band_draw = ImageDraw.Draw(band_layer)
    for path in geometry.paths:
        points = [
            (float(point[0]) * scale, float(point[1]) * scale)
            for point in path.points_mm
        ]
        width_px = max(1, round(path.width_mm * scale))
        band_draw.line(points, fill=1, width=width_px, joint="curve")
        cap_radius = width_px / 2.0
        for x_coordinate, y_coordinate in points:
            band_draw.ellipse(
                (
                    x_coordinate - cap_radius,
                    y_coordinate - cap_radius,
                    x_coordinate + cap_radius,
                    y_coordinate + cap_radius,
                ),
                fill=1,
            )

    center_x, center_y = geometry.boundary.center_mm
    clip_radius_mm = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    circular_clip = Image.new("1", panel.size, 0)
    ImageDraw.Draw(circular_clip).ellipse(
        (
            (center_x - clip_radius_mm) * scale,
            (center_y - clip_radius_mm) * scale,
            (center_x + clip_radius_mm) * scale,
            (center_y + clip_radius_mm) * scale,
        ),
        fill=1,
    )
    panel.paste(0, mask=ImageChops.logical_and(band_layer, circular_clip))

    outer_radius_mm = geometry.boundary.outer_diameter_mm / 2.0
    ImageDraw.Draw(panel).ellipse(
        (
            (center_x - outer_radius_mm) * scale,
            (center_y - outer_radius_mm) * scale,
            (center_x + outer_radius_mm) * scale,
            (center_y + outer_radius_mm) * scale,
        ),
        outline=0,
        width=round(geometry.boundary.width_mm * scale),
    )


def _draw_labels(panel: Image.Image, cell: SeriesSheetCell) -> None:
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((4, 3), cell.phase_slug, fill=0, font=font)
    draw.text((4, PANEL_SIZE_PX - 15), cell.treatment, fill=0, font=font)


def _cell_record(cell: SeriesSheetCell, index: int) -> dict[str, object]:
    column = index // 2
    row = index % 2
    return {
        "cell_id": cell.cell_id,
        "cell_index": index,
        "column": column,
        "row": row,
        "phase": cell.phase_slug,
        "treatment": cell.treatment,
        "geometry_id": cell.geometry.geometry_id,
        "bundle_id": cell.bundle_id,
        "run_id": cell.bundle_id,
        "source_kind": cell.source_kind,
        "selection_id": cell.selection_id,
        "orientation_id": cell.geometry.orientation_id,
        "renderer_version": PANEL_RENDERER_VERSION,
        "panel_size_px": PANEL_SIZE_PX,
    }


def render_series_sheet(cells: Sequence[SeriesSheetCell]) -> RenderedSeriesSheet:
    """Draw the fixed five-by-two comparison directly from physical geometries."""
    ordered = tuple(cells)
    if len(ordered) != len(CELL_ORDER) or any(
        not isinstance(cell, SeriesSheetCell) for cell in ordered
    ):
        raise ValueError("series sheet requires exactly ten SeriesSheetCell values")
    cell_order = tuple(cell.cell_id for cell in ordered)
    if cell_order != CELL_ORDER:
        raise ValueError("series sheet cells differ from the exact approved order")
    if ordered[0].source_kind != "reference" or any(
        cell.source_kind != "bundle" for cell in ordered[1:]
    ):
        raise ValueError("only the first series cell may be the reviewed reference")
    boundary = ordered[0].geometry.boundary.to_dict()
    if any(cell.geometry.boundary.to_dict() != boundary for cell in ordered[1:]):
        raise ValueError("series sheet geometries must share one exact boundary")

    comparison = Image.new("1", (5 * PANEL_SIZE_PX, 2 * PANEL_SIZE_PX), 1)
    records: list[dict[str, object]] = []
    for index, cell in enumerate(ordered):
        panel = Image.new("1", (PANEL_SIZE_PX, PANEL_SIZE_PX), 1)
        _draw_geometry(panel, cell.geometry)
        _draw_labels(panel, cell)
        record = _cell_record(cell, index)
        comparison.paste(
            panel,
            (record["column"] * PANEL_SIZE_PX, record["row"] * PANEL_SIZE_PX),
        )
        records.append(record)

    payload = BytesIO()
    comparison.save(payload, format="PNG", compress_level=9, optimize=False)
    comparison_png = payload.getvalue()
    ledger_content: dict[str, object] = {
        "schema_version": 1,
        "cell_order": list(cell_order),
        "layout": {
            "columns": 5,
            "rows": 2,
            "row_order": list(_ROW_ORDER),
        },
        "renderer_version": PANEL_RENDERER_VERSION,
        "panel_size_px": PANEL_SIZE_PX,
        "ink": "#000000",
        "background": "#ffffff",
        "stroke_clip_radius_mm": 63.8,
        "outer_boundary": {
            "outer_diameter_mm": 132.0,
            "stroke_width_mm": 2.2,
        },
        "cells": records,
    }
    ledger = {
        "ledger_id": stable_id("phase-art-comparison-ledger", ledger_content),
        **ledger_content,
    }
    return RenderedSeriesSheet(
        comparison_png=comparison_png,
        ledger=ledger,
        cell_order=cell_order,
    )


def _validated_series_payload(
    *,
    recipe_id: str,
    rendered: RenderedSeriesSheet,
) -> tuple[str, _ValidatedPayload]:
    if not isinstance(recipe_id, str) or not recipe_id:
        raise ValueError("series recipe_id must be non-empty text")
    if not isinstance(rendered, RenderedSeriesSheet):
        raise TypeError("rendered must be a RenderedSeriesSheet")
    if rendered.cell_order != CELL_ORDER:
        raise ValueError("rendered series cell order differs from the contract")
    with Image.open(BytesIO(rendered.comparison_png)) as image:
        if image.mode != "1" or image.size != (4500, 1800):
            raise ValueError("comparison PNG must be binary 4500 by 1800 pixels")
        if image.getextrema() != (0, 255):
            raise ValueError("comparison PNG must contain only black and white")
    ledger = plain_data(rendered.ledger)
    ledger_content = {key: value for key, value in ledger.items() if key != "ledger_id"}
    if ledger.get("ledger_id") != stable_id(
        "phase-art-comparison-ledger", ledger_content
    ):
        raise ValueError("comparison ledger ID differs from its content")
    cells = ledger["cells"]
    bundle_ids = [cell["bundle_id"] for cell in cells]
    run_identity = {
        "schema_version": 1,
        "recipe_id": recipe_id,
        "ledger_id": ledger["ledger_id"],
        "comparison_sha256": _sha256_bytes(rendered.comparison_png),
        "cell_order": list(rendered.cell_order),
        "bundle_ids": bundle_ids,
        "new_bundle_count": 9,
        "comparison_cell_count": 10,
        "simulation_count": 0,
        "renderer_version": PANEL_RENDERER_VERSION,
        "panel_size_px": PANEL_SIZE_PX,
    }
    series_id = stable_id("phase-art-series", run_identity)
    payload = _ValidatedPayload(
        run_identity=run_identity,
        files={
            "comparison.png": rendered.comparison_png,
            "comparison-ledger.json": ledger,
        },
        payload_order=("comparison.png", "comparison-ledger.json"),
    )
    return series_id, payload


def write_series_sheet_bundle(
    output_root: str | Path,
    *,
    recipe_id: str,
    rendered: RenderedSeriesSheet,
) -> SeriesSheetBundleResult:
    """Preflight and atomically publish one content-identified series sheet."""
    series_id, payload = _validated_series_payload(
        recipe_id=recipe_id,
        rendered=rendered,
    )
    path, manifest_sha256 = _publish_validated_payload(
        output_root,
        run_id=series_id,
        payload=payload,
    )
    return SeriesSheetBundleResult(
        series_id=series_id,
        path=path,
        comparison_sheet=path / "comparison.png",
        cell_order=rendered.cell_order,
        manifest_sha256=manifest_sha256,
    )


__all__ = [
    "CELL_ORDER",
    "PANEL_RENDERER_VERSION",
    "PANEL_SIZE_PX",
    "RenderedSeriesSheet",
    "SeriesSheetBundleResult",
    "SeriesSheetCell",
    "render_series_sheet",
    "write_series_sheet_bundle",
]
