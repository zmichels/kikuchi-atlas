"""Atomic publication workflow for the recovered Ice Ih reflector catalog."""

from __future__ import annotations

from pathlib import Path

from kikuchi_lab.reflectors import ReflectorRecipe, load_reflector_recipe
from kikuchi_lab.reflectors.bundle import ReflectorCatalogBuildResult
from kikuchi_lab.workflows.reflector_catalog import build_reflector_catalog_bundle


def _require_recovered_ice_policy(recipe: ReflectorRecipe) -> None:
    """Keep the bounded Ice workflow fixed while ReflectorRecipe stays phase-neutral."""
    expected = {
        "source_record": "phases/ice-ih/source.yml",
        "source_master_relative_factor": 0.03,
        "selection_relative_factor": 0.22,
        "weight_exponent": 2.0,
        "eligibility_min_weight": 0.08,
        "tie_policy": "keep_equal_weights_together",
        "cohort_count": 4,
    }
    for field, value in expected.items():
        if getattr(recipe, field) != value:
            raise ValueError(f"bounded Ice reflector workflow requires {field}={value!r}")


def build_ice_reflector_catalog(
    recipe_path: str | Path, output_root: str | Path
) -> ReflectorCatalogBuildResult:
    """Build a content-addressed, no-clobber Ice reflector catalog bundle."""
    recipe = load_reflector_recipe(recipe_path)
    _require_recovered_ice_policy(recipe)
    return build_reflector_catalog_bundle(recipe_path, output_root)
