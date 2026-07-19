from __future__ import annotations

import numpy as np

from kikuchi_lab.reflector_globe.recipes import load_reflector_ridge_recipe
from kikuchi_lab.reflector_globe.smooth_strips import build_smooth_strip_mesh
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember


def test_smooth_strip_mesh_builds_closed_swept_ridge_shells() -> None:
    recipe = load_reflector_ridge_recipe("recipes/globes/ice-ih-reflector-ridges.yml")
    member = ReflectorMember(
        hkl=(0, 0, 1),
        normal_crystal=np.array([0.0, 0.0, 1.0]),
        dspacing_angstrom=2.0,
        bragg_half_width_rad=0.01,
        structure_factor_abs=1.0,
        normalized_weight=1.0,
        eligible=True,
        cohort=4,
    )
    catalog = ReflectorCatalog(
        source_structure_id="synthetic",
        source_structure_sha256="0" * 64,
        energy_kev=20.0,
        reflection_recipe_id="synthetic-recipe",
        selection={},
        members=(member,),
    )

    result = build_smooth_strip_mesh(
        catalog,
        recipe,
        base_subdivisions=2,
        angular_segments=72,
        cross_segments=7,
    )

    assert result.strip_count == 1
    assert result.mesh.is_watertight
    assert result.mesh.body_count == 2
    assert result.mesh.bounds[0].min() >= -43.0
    assert result.mesh.bounds[1].max() <= 43.0
