"""Recipe-driven Ice near-depth rendering workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.near_depth.bundle import write_near_depth_bundle
from kikuchi_lab.near_depth.overlap import compute_overlap_field
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe
from kikuchi_lab.near_depth.render import render_near_depth, render_quiet_control
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


@dataclass(frozen=True)
class NearDepthRunResult:
    run_id: str
    path: Path
    treatment_recipe_id: str
    base_recipe_id: str
    figure_names: tuple[str, ...]
    manifest_sha256: str


def render_kinematical_depth(
    *,
    recipe_path: str | Path,
    output_root: str | Path,
    figure_size_px: int | None = None,
) -> NearDepthRunResult:
    """Execute a verified base simulation and publish its depth derivative."""
    treatment_file = Path(recipe_path).resolve()
    treatment = load_near_depth_recipe(treatment_file)
    base_path = (treatment_file.parent / treatment.source_kinematical_recipe).resolve()
    base = load_kinematical_recipe(base_path)
    if base.recipe_id != treatment.expected_kinematical_recipe_id:
        raise ValueError(
            "near-depth expected base recipe ID does not match the referenced recipe"
        )
    source_path = (base_path.parent / base.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    simulation, context = simulate_kinematical_arrays(source, base)
    size = int(simulation.master_stereographic.intensity.shape[-1])
    overlap = compute_overlap_field(
        context.master_simulator.reflectors,
        size=size,
        relative_factor=treatment.overlap_relative_factor,
        weight_exponent=treatment.weight_exponent,
        normalization_percentile=treatment.normalization_percentile,
    )
    effective_size = treatment.figure_size_px if figure_size_px is None else figure_size_px
    quiet = render_quiet_control(
        context,
        simulation,
        base,
        figure_size_px=effective_size,
    )
    render = render_near_depth(
        context,
        simulation,
        base,
        treatment,
        overlap,
        quiet,
        figure_size_px=effective_size,
    )
    bundle = write_near_depth_bundle(
        output_root,
        render,
        overlap,
        simulation,
        treatment,
        base,
        source,
    )
    return NearDepthRunResult(
        run_id=bundle.run_id,
        path=bundle.path,
        treatment_recipe_id=treatment.recipe_id,
        base_recipe_id=base.recipe_id,
        figure_names=tuple(sorted(render.figures)),
        manifest_sha256=bundle.manifest_sha256,
    )


__all__ = ["NearDepthRunResult", "render_kinematical_depth"]
