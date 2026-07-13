"""Contact sheets whose labels live outside the scientific image panels."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class ContactSheetItem:
    candidate_id: str
    label: str
    raw: np.ndarray
    processed: np.ndarray


def _preview(image: np.ndarray, shape: tuple[int, int]) -> Image.Image:
    array = np.asarray(image)
    if array.ndim != 2 or array.dtype != np.uint8:
        raise ValueError("contact-sheet panels must be two-dimensional uint8 previews")
    target_height, target_width = shape
    return Image.fromarray(array, mode="L").resize(
        (target_width, target_height), resample=Image.Resampling.LANCZOS
    )


def write_contact_sheet(
    path: str | Path,
    items: Sequence[ContactSheetItem],
    *,
    columns: int,
    panel_shape: tuple[int, int],
) -> dict[str, object]:
    """Write paired raw/processed panels with a non-overlapping label footer."""
    if not items:
        raise ValueError("contact sheet requires at least one item")
    if columns <= 0:
        raise ValueError("contact sheet columns must be positive")
    panel_height, panel_width = panel_shape
    if panel_height <= 0 or panel_width <= 0:
        raise ValueError("contact sheet panel shape must be positive")

    gap = 4
    padding = 8
    label_height = 52
    card_width = panel_width * 2 + gap
    card_height = panel_height + label_height
    rows = math.ceil(len(items) / columns)
    sheet = Image.new(
        "L",
        (columns * card_width + (columns + 1) * padding,
         rows * card_height + (rows + 1) * padding),
        color=18,
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=14)
    small_font = ImageFont.load_default(size=12)
    for index, item in enumerate(items):
        row, column = divmod(index, columns)
        x = padding + column * (card_width + padding)
        y = padding + row * (card_height + padding)
        sheet.paste(_preview(item.raw, panel_shape), (x, y))
        sheet.paste(_preview(item.processed, panel_shape), (x + panel_width + gap, y))
        label_y = y + panel_height
        draw.rectangle((x, label_y, x + card_width, y + card_height), fill=32)
        first, second = item.label.split("\n", maxsplit=1)
        draw.text((x + 5, label_y + 4), first, font=font, fill=245)
        draw.text((x + 5, label_y + 27), second, font=small_font, fill=210)
        draw.text((x + card_width - 105, label_y + 4), "raw | processed", font=small_font, fill=180)

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=False)
    return {
        "schema_version": 1,
        "candidate_order": [item.candidate_id for item in items],
        "panels": ["raw", "processed"],
        "labels": [item.label.replace("\n", " | ") for item in items],
        "columns": columns,
        "rows": rows,
        "panel_shape": list(panel_shape),
        "pixel_shape": [sheet.height, sheet.width],
        "label_height_px": label_height,
        "label_placement": "footer outside image panels",
    }
