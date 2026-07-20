"""Bounded smoke-before-review workflow for the oriented Ice spherical proof."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from kikuchi_lab.kinematical.contracts import KinematicalRecipe
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe
from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.spherical_intensity.contracts import SphericalIntensityRecipe
from kikuchi_lab.spherical_intensity.mapping import build_spherical_intensity
from kikuchi_lab.spherical_intensity.orientation import (
    OrientedProfileName,
    OrientedSphericalRecipe,
    load_oriented_spherical_recipe,
)
from kikuchi_lab.spherical_intensity.oriented_bundle import (
    write_oriented_spherical_bundle,
)
from kikuchi_lab.spherical_intensity.oriented_render import render_oriented_spherical
from kikuchi_lab.spherical_intensity.presentation import build_presentation_source
from kikuchi_lab.spherical_intensity.recipe import load_spherical_intensity_recipe
from kikuchi_lab.spherical_intensity.rotation import rotate_spherical_field


_PROFILE_NAMES = {"smoke", "review"}


class OrientedSphericalTimeoutError(RuntimeError):
    """Raised when an oriented spherical profile exceeds its approved deadline."""


@dataclass(frozen=True)
class OrientedSphericalProfileResult:
    """Published result from one bounded oriented spherical profile."""

    profile: OrientedProfileName
    run_id: str
    path: Path
    source_half_size: int
    figure_names: Sequence[str]
    manifest_sha256: str
    elapsed_seconds: float


@dataclass(frozen=True)
class OrientedSphericalRunResult:
    """Smoke result and optional review result from one auditable request."""

    smoke: OrientedSphericalProfileResult
    review: OrientedSphericalProfileResult | None


def _deadline(started: float, timeout_seconds: int, stage: str) -> Callable[[], None]:
    def check() -> None:
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise OrientedSphericalTimeoutError(
                f"oriented spherical {stage} exceeded {timeout_seconds} seconds"
            )

    return check


def _log_stage(
    *,
    started: float,
    profile_name: OrientedProfileName,
    stage: str,
    check_deadline: Callable[[], None],
) -> None:
    check_deadline()
    elapsed = time.monotonic() - started
    print(
        f"oriented-spherical profile={profile_name} stage={stage} elapsed_seconds={elapsed:.6f}",
        file=sys.stderr,
        flush=True,
    )


def _materialize_source_recipes(
    oriented_path: Path,
    oriented: OrientedSphericalRecipe,
) -> tuple[SphericalIntensityRecipe, KinematicalRecipe, Path, Path]:
    spherical_path = (oriented_path.parent / oriented.source_spherical_recipe).resolve()
    source_profile_name = "smoke" if oriented.profile.name == "smoke" else "acceptance"
    source_recipe = load_spherical_intensity_recipe(
        spherical_path,
        profile=source_profile_name,
    )
    source_recipe = replace(
        source_recipe,
        profile=replace(
            source_recipe.profile,
            half_size=oriented.profile.source_half_size,
            timeout_seconds=oriented.profile.timeout_seconds,
        ),
    )
    base_path = (spherical_path.parent / source_recipe.source_kinematical_recipe).resolve()
    base = load_kinematical_recipe(base_path)
    if base.hemisphere != "both":
        raise ValueError("oriented source master must contain both hemispheres")
    base = replace(
        base,
        orientation=Orientation((0.0, 0.0, 0.0)),
        half_size=oriented.profile.source_half_size,
        figure_size_px=oriented.profile.figure_size_px,
    )
    return source_recipe, base, spherical_path, base_path


def _run_profile(
    *,
    recipe_path: Path,
    output_root: Path,
    profile_name: OrientedProfileName,
) -> OrientedSphericalProfileResult:
    started = time.monotonic()
    oriented_recipe = load_oriented_spherical_recipe(recipe_path, profile=profile_name)
    check = _deadline(started, oriented_recipe.profile.timeout_seconds, profile_name)
    source_recipe, base, _, base_path = _materialize_source_recipes(
        recipe_path,
        oriented_recipe,
    )
    source_path = (base_path.parent / base.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)

    _log_stage(
        started=started,
        profile_name=profile_name,
        stage="simulation",
        check_deadline=check,
    )
    simulation, context = simulate_kinematical_arrays(source, base)

    _log_stage(
        started=started,
        profile_name=profile_name,
        stage="s2_mapping",
        check_deadline=check,
    )
    build = build_spherical_intensity(simulation, source, source_recipe)
    identity = rotate_spherical_field(build.field, Orientation((0.0, 0.0, 0.0)))
    oriented = rotate_spherical_field(build.field, oriented_recipe.orientation)

    _log_stage(
        started=started,
        profile_name=profile_name,
        stage="presentation",
        check_deadline=check,
    )
    treatment_path = (recipe_path.parent / oriented_recipe.presentation_recipe).resolve()
    treatment = load_near_depth_recipe(treatment_path)
    if treatment.expected_kinematical_recipe_id != load_kinematical_recipe(base_path).recipe_id:
        raise ValueError("presentation recipe does not identify the tracked Ice base recipe")
    presentation = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base,
        treatment,
    )

    _log_stage(
        started=started,
        profile_name=profile_name,
        stage="figures",
        check_deadline=check,
    )
    render = render_oriented_spherical(
        presentation,
        oriented_recipe,
        check_deadline=check,
    )

    _log_stage(
        started=started,
        profile_name=profile_name,
        stage="publication",
        check_deadline=check,
    )
    bundle = write_oriented_spherical_bundle(
        output_root,
        source_build=build,
        identity_field=identity,
        oriented_field=oriented,
        render=render,
        oriented_recipe=oriented_recipe,
        source_recipe=source_recipe,
        presentation_recipe=treatment,
        presentation_source=presentation,
        source=source,
        stage_timing={"elapsed_seconds": time.monotonic() - started},
    )
    return OrientedSphericalProfileResult(
        profile=profile_name,
        run_id=bundle.run_id,
        path=bundle.path,
        source_half_size=oriented_recipe.profile.source_half_size,
        figure_names=tuple(sorted(render.figures)),
        manifest_sha256=bundle.manifest_sha256,
        elapsed_seconds=time.monotonic() - started,
    )


def render_oriented_spherical_master(
    *,
    recipe_path: str | Path,
    output_root: str | Path,
    profile: OrientedProfileName,
) -> OrientedSphericalRunResult:
    """Publish smoke first, followed by review only when explicitly requested."""
    if profile not in _PROFILE_NAMES:
        raise ValueError("oriented profile must be smoke or review")
    recipe_file = Path(recipe_path).resolve()
    root = Path(output_root).resolve()
    smoke = _run_profile(
        recipe_path=recipe_file,
        output_root=root / "smoke",
        profile_name="smoke",
    )
    if profile == "smoke":
        return OrientedSphericalRunResult(smoke=smoke, review=None)
    review = _run_profile(
        recipe_path=recipe_file,
        output_root=root / "review",
        profile_name="review",
    )
    return OrientedSphericalRunResult(smoke=smoke, review=review)


__all__ = [
    "OrientedSphericalProfileResult",
    "OrientedSphericalRunResult",
    "OrientedSphericalTimeoutError",
    "render_oriented_spherical_master",
]
