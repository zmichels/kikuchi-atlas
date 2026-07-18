from __future__ import annotations

from pathlib import Path

import numpy as np

from kikuchi_lab.reflectors.catalog import build_reflector_catalog
from kikuchi_lab.reflectors.recipe import load_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


def test_member_normals_are_crystal_frame_unit_vectors() -> None:
    source = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_reflector_recipe(ROOT / "recipes/reflectors/ice-ih-catalog.yml")

    catalog = build_reflector_catalog(source, recipe)

    assert np.allclose(
        [np.linalg.norm(member.normal_crystal) for member in catalog.members],
        1.0,
        atol=5e-13,
    )
