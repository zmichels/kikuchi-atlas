"""Strict loading for version-controlled near-depth treatment recipes."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import yaml

from .contracts import NearDepthTreatmentRecipe, StrokeStyle


_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_kinematical_recipe",
    "expected_kinematical_recipe_id",
    "overlap",
    "optical_depth",
    "center",
    "boundary",
    "figure_size_px",
    "background_color",
}
_OVERLAP_FIELDS = {
    "relative_factor",
    "weight_exponent",
    "normalization_percentile",
}
_OPTICAL_DEPTH_FIELDS = {"gain", "luminance_ceiling"}
_STROKE_FIELDS = {
    "relative_factor",
    "width_pt",
    "alpha",
    "casing_width_pt",
    "casing_alpha",
}
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _mapping(value: Any, field: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"near-depth recipe {field} fields differ from the schema")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"near-depth recipe {field} must be non-empty text")
    return value


def _relative_path(value: Any, field: str) -> str:
    result = _text(value, field)
    if Path(result).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", result):
        raise ValueError(f"near-depth recipe {field} must be a relative path")
    return result


def _real(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"near-depth recipe {field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"near-depth recipe {field} must be finite")
    return result


def _positive(value: Any, field: str) -> float:
    result = _real(value, field)
    if result <= 0:
        raise ValueError(f"near-depth recipe {field} must be positive")
    return result


def _unit_interval(value: Any, field: str) -> float:
    result = _real(value, field)
    if not 0 <= result <= 1:
        raise ValueError(f"near-depth recipe {field} must be in [0, 1]")
    return result


def _relative_factor(value: Any, field: str) -> float:
    result = _positive(value, field)
    if result > 1:
        raise ValueError(f"near-depth recipe {field} must be in (0, 1]")
    return result


def _stroke(value: Any, field: str) -> StrokeStyle:
    raw = _mapping(value, field, _STROKE_FIELDS)
    width = _positive(raw["width_pt"], f"{field}.width_pt")
    casing_width = _positive(raw["casing_width_pt"], f"{field}.casing_width_pt")
    if casing_width < width:
        raise ValueError(f"near-depth recipe {field}.casing_width_pt must cover width_pt")
    return StrokeStyle(
        relative_factor=_relative_factor(
            raw["relative_factor"], f"{field}.relative_factor"
        ),
        width_pt=width,
        alpha=_unit_interval(raw["alpha"], f"{field}.alpha"),
        casing_width_pt=casing_width,
        casing_alpha=_unit_interval(raw["casing_alpha"], f"{field}.casing_alpha"),
    )


def load_near_depth_recipe(path: str | Path) -> NearDepthTreatmentRecipe:
    """Load and validate one version-1 near-depth treatment recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("near-depth recipe YAML is invalid") from None
    root = _mapping(payload, "top-level", _TOP_LEVEL_FIELDS)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("near-depth recipe schema_version must be integer 1")

    overlap = _mapping(root["overlap"], "overlap", _OVERLAP_FIELDS)
    percentile = _positive(
        overlap["normalization_percentile"], "overlap.normalization_percentile"
    )
    if percentile > 100:
        raise ValueError(
            "near-depth recipe overlap.normalization_percentile must be in (0, 100]"
        )

    optical = _mapping(root["optical_depth"], "optical_depth", _OPTICAL_DEPTH_FIELDS)
    ceiling = _real(optical["luminance_ceiling"], "optical_depth.luminance_ceiling")
    if not 0 < ceiling < 1:
        raise ValueError(
            "near-depth recipe optical_depth.luminance_ceiling must be in (0, 1)"
        )

    figure_size = root["figure_size_px"]
    if type(figure_size) is not int or figure_size <= 0:
        raise ValueError("near-depth recipe figure_size_px must be a positive integer")
    background = _text(root["background_color"], "background_color")
    if _HEX_COLOR.fullmatch(background) is None:
        raise ValueError("near-depth recipe background_color must be #RRGGBB")

    return NearDepthTreatmentRecipe(
        schema_version=1,
        name=_text(root["name"], "name"),
        source_kinematical_recipe=_relative_path(
            root["source_kinematical_recipe"], "source_kinematical_recipe"
        ),
        expected_kinematical_recipe_id=_text(
            root["expected_kinematical_recipe_id"],
            "expected_kinematical_recipe_id",
        ),
        overlap_relative_factor=_relative_factor(
            overlap["relative_factor"], "overlap.relative_factor"
        ),
        weight_exponent=_positive(
            overlap["weight_exponent"], "overlap.weight_exponent"
        ),
        normalization_percentile=percentile,
        optical_depth_gain=_positive(optical["gain"], "optical_depth.gain"),
        luminance_ceiling=ceiling,
        center=_stroke(root["center"], "center"),
        boundary=_stroke(root["boundary"], "boundary"),
        figure_size_px=figure_size,
        background_color=background.lower(),
    )


__all__ = ["load_near_depth_recipe"]
