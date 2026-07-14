"""Small deterministic fixtures for spherical-intensity mapping tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from kikuchi_lab.kinematical import (
    KinematicalArrayProduct,
    KinematicalSimulation,
    load_kinematical_recipe,
)
from kikuchi_lab.sources.structure import StructureRecord, load_structure_record
from kikuchi_lab.spherical_intensity import (
    SphericalIntensityBuild,
    SphericalIntensityRecipe,
    build_spherical_intensity,
    load_spherical_intensity_recipe,
)


ROOT = Path(__file__).parents[1]
SPHERICAL_RECIPE = ROOT / "recipes/spherical/forsterite-s2-intensity.yml"
KINEMATICAL_RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"
SOURCE = ROOT / "phases/forsterite/source.yml"


def fixture_source() -> StructureRecord:
    return load_structure_record(SOURCE)


def centrosymmetric_source() -> StructureRecord:
    return fixture_source()


def noncentrosymmetric_source() -> StructureRecord:
    return replace(
        fixture_source(),
        name="synthetic-noncentrosymmetric",
        space_group_number=1,
    )


def spherical_recipe(*, half_size: int = 2) -> SphericalIntensityRecipe:
    recipe = load_spherical_intensity_recipe(SPHERICAL_RECIPE, profile="smoke")
    return replace(recipe, profile=replace(recipe.profile, half_size=half_size))


def symmetric_master(*, half_size: int = 2) -> np.ndarray:
    coordinate = np.linspace(-1.0, 1.0, 2 * half_size + 1, dtype=np.float32)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    intensity = x_grid * x_grid + 2.0 * y_grid * y_grid + 1.0
    return np.stack([intensity, intensity]).astype(np.float32)


def synthetic_simulation(
    master: np.ndarray,
    *,
    hemisphere_order: list[str] | None = None,
    row_axis: str = "Y ascending -1 to +1",
    column_axis: str = "X ascending -1 to +1",
    grid_formula: str = "coordinate[k] = -1 + 2*k/(N-1)",
    frame: str = "standard-Pnma direct and reciprocal Cartesian frames",
    handedness: str = "right-handed",
) -> KinematicalSimulation:
    energy_kev = load_kinematical_recipe(KINEMATICAL_RECIPE).energy_kev
    stereo = KinematicalArrayProduct.from_array(
        "master-stereographic",
        master,
        metadata={
            "projection": "stereographic",
            "hemisphere": "both",
            "energy_kev": energy_kev,
        },
    )
    lambert = KinematicalArrayProduct.from_array(
        "master-lambert",
        master,
        metadata={"projection": "lambert", "hemisphere": "both"},
    )
    detector = KinematicalArrayProduct.from_array(
        "detector",
        master[0],
        metadata={"projection": "gnomonic", "hemisphere": "upper"},
    )
    return KinematicalSimulation(
        master_stereographic=stereo,
        master_lambert=lambert,
        detector=detector,
        reflector_catalog={},
        projection_ledger={
            "frames": {"crystal": frame, "handedness": handedness},
            "projections": {
                "stereographic": {
                    "hemisphere": "both",
                    "hemisphere_order": hemisphere_order or ["upper", "lower"],
                    "row_axis": row_axis,
                    "column_axis": column_axis,
                    "grid_formula": grid_formula,
                }
            },
        },
    )


def small_spherical_build(*, half_size: int = 2) -> SphericalIntensityBuild:
    return build_spherical_intensity(
        synthetic_simulation(symmetric_master(half_size=half_size)),
        fixture_source(),
        spherical_recipe(half_size=half_size),
    )
