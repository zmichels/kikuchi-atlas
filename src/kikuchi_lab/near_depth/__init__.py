"""Crisp, presentation-only depth treatment for kinematical masters."""

from .contracts import NearDepthTreatmentRecipe, StrokeStyle
from .recipe import load_near_depth_recipe

__all__ = [
    "NearDepthTreatmentRecipe",
    "StrokeStyle",
    "load_near_depth_recipe",
]
