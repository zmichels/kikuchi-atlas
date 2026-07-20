"""Public workflow for the bounded Ice Ih kinematical source master."""

from __future__ import annotations

from pathlib import Path

from kikuchi_lab.kinematical.contracts import KinematicalSimulation
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.sources.structure import StructureRecord, load_structure_record


_REPOSITORY_ROOT = Path(__file__).parents[3]
_TRACKED_ICE_SOURCE = (_REPOSITORY_ROOT / "phases/ice-ih/source.yml").resolve()
_ICE_IDENTIFIER = "COD-1572233-O-sublattice"
_ICE_SHA256 = "4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81"
_ICE_SPACE_GROUP_NUMBER = 194
_ICE_SETTING = "P 63/m m c"
_ICE_MODEL_SCOPE = "average oxygen sublattice only"
_ICE_OMITTED_SOURCE_SITES = ["H1a", "H1b"]


def _require_tracked_ice_source(source: StructureRecord) -> None:
    """Reject lookalikes: this bounded workflow has one recovered Ice source."""
    if source.record_path != _TRACKED_ICE_SOURCE:
        raise ValueError("bounded Ice kinematical master requires Task 1's tracked Ice source")
    if (
        source.identifier != _ICE_IDENTIFIER
        or source.sha256 != _ICE_SHA256
        or source.space_group_number != _ICE_SPACE_GROUP_NUMBER
        or source.setting != _ICE_SETTING
        or source.simulation_setting.get("model_scope") != _ICE_MODEL_SCOPE
        or source.simulation_setting.get("omitted_source_sites") != _ICE_OMITTED_SOURCE_SITES
    ):
        raise ValueError("tracked Ice source does not match the recovered Task 1 constraints")


def simulate_ice_kinematical(recipe_path: str | Path) -> KinematicalSimulation:
    """Load one closed recipe and return its project-owned Ice source product."""
    recipe_file = Path(recipe_path).resolve()
    recipe = load_kinematical_recipe(recipe_file)
    source = load_structure_record((recipe_file.parent / recipe.source_record).resolve())
    _require_tracked_ice_source(source)
    simulation, _context = simulate_kinematical_arrays(source, recipe)
    return simulation
