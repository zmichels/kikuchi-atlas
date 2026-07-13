"""Contact sheets whose labels live outside the scientific image panels."""

from __future__ import annotations

import math
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version


_DISPLAY_POLICY = (
    "Previews use independent robust display mappings for structural comparison only."
)


def _fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    return ImageFont.load_default(size=14), ImageFont.load_default(size=12)


def _font_contract() -> dict[str, object]:
    primary, secondary = _fonts()
    sample = "".join(chr(codepoint) for codepoint in range(32, 127))
    atlas = Image.new("L", (1024, 48), color=0)
    draw = ImageDraw.Draw(atlas)
    draw.text((0, 0), sample, font=primary, fill=255)
    draw.text((0, 24), sample, font=secondary, fill=255)
    return {
        "provider": "pillow-load-default",
        "pillow_version": pillow_version,
        "family_style": list(primary.getname()),
        "sizes_px": {"primary": 14, "secondary": 12},
        "glyph_set": "ascii-32-126",
        "glyph_atlas_sha256": hashlib.sha256(atlas.tobytes()).hexdigest(),
    }


def contact_sheet_rendering_contract(
    *,
    columns: int,
    panel_shape: tuple[int, int],
    processed_variant: dict[str, str],
) -> dict[str, object]:
    """Return every rendering choice that can affect proof identity."""
    if columns <= 0:
        raise ValueError("contact sheet columns must be positive")
    panel_height, panel_width = panel_shape
    if panel_height <= 0 or panel_width <= 0:
        raise ValueError("contact sheet panel shape must be positive")
    panel_gap = 4
    label_height = 52
    return {
        "schema_version": 3,
        "renderer": {"name": "kikuchi-lab-contact-sheet", "version": 3},
        "grid": {"columns": columns},
        "panel": {
            "shape": list(panel_shape),
            "panels": ["raw", "processed"],
            "processed_variant": processed_variant["name"],
            "processing_recipe_id": processed_variant["recipe_id"],
        },
        "layout": {
            "panel_gap_px": panel_gap,
            "outer_padding_px": 8,
            "banner_height_px": 58,
            "label_height_px": label_height,
            "card_shape": [label_height + panel_height, panel_width * 2 + panel_gap],
        },
        "colors": {
            "sheet_background": 18,
            "banner_background": 8,
            "label_background": 32,
            "banner_text": 255,
            "display_policy_text": 190,
            "candidate_primary_text": 245,
            "candidate_secondary_text": 210,
            "panel_label_text": 180,
        },
        "fonts": _font_contract(),
        "text_templates": {
            "quality_banner": (
                "PROOF-GRADE / NOT FINAL QUALITY | orientation comparison | "
                "processed: {processed_name} [{processed_short_id}]"
            ),
            "display_policy": _DISPLAY_POLICY,
            "panel_label": "raw | {processed_name} [{processed_short_id}]",
            "candidate_primary": "{candidate_id}  {zone_axis_label}  phi1={phi1_deg:.3f} deg",
            "candidate_secondary": (
                "Bunge Euler=({phi1_deg:.3f}, {phi_deg:.3f}, {phi2_deg:.3f}) deg"
            ),
        },
        "label_policy": {
            "placement": "footer outside image panels",
            "panel_labels": "paired raw and processed label in footer",
            "candidate_labels": "two-line orientation label in footer",
            "ascii_only": True,
        },
    }


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
    rendering_contract: dict[str, object],
    processed_variant: dict[str, str],
    quality_banner: dict[str, object],
) -> dict[str, object]:
    """Write paired raw/processed panels with a non-overlapping label footer."""
    if not items:
        raise ValueError("contact sheet requires at least one item")
    grid = rendering_contract["grid"]
    panel = rendering_contract["panel"]
    layout = rendering_contract["layout"]
    colors = rendering_contract["colors"]
    templates = rendering_contract["text_templates"]
    assert isinstance(grid, dict) and isinstance(panel, dict)
    assert isinstance(layout, dict) and isinstance(colors, dict)
    assert isinstance(templates, dict)
    columns = int(grid["columns"])
    panel_shape = tuple(int(value) for value in panel["shape"])
    panel_height, panel_width = panel_shape
    gap = int(layout["panel_gap_px"])
    padding = int(layout["outer_padding_px"])
    banner_height = int(layout["banner_height_px"])
    label_height = int(layout["label_height_px"])
    card_height, card_width = (int(value) for value in layout["card_shape"])
    rows = math.ceil(len(items) / columns)
    sheet = Image.new(
        "L",
        (columns * card_width + (columns + 1) * padding,
         banner_height + rows * card_height + (rows + 1) * padding),
        color=int(colors["sheet_background"]),
    )
    draw = ImageDraw.Draw(sheet)
    font, small_font = _fonts()
    banner_text = str(quality_banner["text"])
    draw.rectangle((0, 0, sheet.width, banner_height), fill=int(colors["banner_background"]))
    draw.text((padding, 7), banner_text, font=font, fill=int(colors["banner_text"]))
    draw.text(
        (padding, 32),
        str(templates["display_policy"]),
        font=small_font,
        fill=int(colors["display_policy_text"]),
    )
    for index, item in enumerate(items):
        row, column = divmod(index, columns)
        x = padding + column * (card_width + padding)
        y = banner_height + padding + row * (card_height + padding)
        sheet.paste(_preview(item.raw, panel_shape), (x, y))
        sheet.paste(_preview(item.processed, panel_shape), (x + panel_width + gap, y))
        label_y = y + panel_height
        draw.rectangle(
            (x, label_y, x + card_width, y + card_height),
            fill=int(colors["label_background"]),
        )
        first, second = item.label.split("\n", maxsplit=1)
        draw.text(
            (x + 5, label_y + 4), first, font=font,
            fill=int(colors["candidate_primary_text"]),
        )
        draw.text(
            (x + 5, label_y + 27), second, font=small_font,
            fill=int(colors["candidate_secondary_text"]),
        )
        panel_text = str(templates["panel_label"]).format(
            processed_name=processed_variant["name"],
            processed_short_id=processed_variant["short_id"],
        )
        panel_text_width = draw.textlength(panel_text, font=small_font)
        draw.text(
            (x + card_width - panel_text_width - 5, label_y + 4),
            panel_text,
            font=small_font,
            fill=int(colors["panel_label_text"]),
        )

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=False)
    rendered_text = [banner_text, *[item.label.replace("\n", " | ") for item in items]]
    return {
        "schema_version": 3,
        "rendering_contract": rendering_contract,
        "candidate_order": [item.candidate_id for item in items],
        "panels": ["raw", "processed"],
        "labels": [item.label.replace("\n", " | ") for item in items],
        "processed_variant": processed_variant,
        "quality_banner": quality_banner,
        "rendered_text": rendered_text,
        "columns": columns,
        "rows": rows,
        "panel_shape": list(panel_shape),
        "pixel_shape": [sheet.height, sheet.width],
        "label_height_px": label_height,
        "label_placement": "footer outside image panels",
        "banner_height_px": banner_height,
    }
