"""Recipe-driven standalone kinematical rendering workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.kinematical.bundle import write_kinematical_bundle
from kikuchi_lab.kinematical.kikuchipy_adapter import execute_kinematical
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


@dataclass(frozen=True)
class KinematicalRunResult:
    run_id: str
    path: Path
    recipe_id: str
    master_reflector_count: int
    figure_names: tuple[str, ...]


def render_kinematical(*, recipe_path: str | Path, output_root: str | Path) -> KinematicalRunResult:
    """Execute a verified kinematical recipe and publish its canonical bundle."""
    recipe_file = Path(recipe_path).resolve()
    recipe = load_kinematical_recipe(recipe_file)
    source_path = (recipe_file.parent / recipe.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    execution = execute_kinematical(source, recipe)
    bundle = write_kinematical_bundle(Path(output_root), execution, recipe, source)
    return KinematicalRunResult(
        run_id=bundle.run_id,
        path=bundle.path,
        recipe_id=recipe.recipe_id,
        master_reflector_count=int(
            execution.simulation.reflector_catalog["master"]["retained_count"]
        ),
        figure_names=tuple(sorted(execution.figures)),
    )


__all__ = ["KinematicalRunResult", "render_kinematical"]
