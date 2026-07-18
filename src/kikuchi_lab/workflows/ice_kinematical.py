"""Public workflow for the bounded Ice Ih kinematical source master."""

from __future__ import annotations

from pathlib import Path

from kikuchi_lab.kinematical.contracts import KinematicalSimulation
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_master
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.reflectors.recipe import load_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


def simulate_ice_kinematical(recipe_path: str | Path) -> KinematicalSimulation:
    """Load one closed recipe and return its project-owned Ice source product."""
    recipe_file = Path(recipe_path).resolve()
    recipe = load_kinematical_recipe(recipe_file)
    source = load_structure_record((recipe_file.parent / recipe.source_record).resolve())
    reflector_recipe = load_reflector_recipe(
        (recipe_file.parent / recipe.reflector_recipe).resolve()
    )
    if Path(reflector_recipe.source_record).as_posix() != "phases/ice-ih/source.yml":
        raise ValueError("bounded Ice kinematical master requires the tracked Ice source")
    return simulate_kinematical_master(source, recipe, reflector_recipe)
