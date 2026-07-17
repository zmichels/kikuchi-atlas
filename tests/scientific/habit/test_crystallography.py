from dataclasses import replace

import numpy as np
import pytest

from kikuchi_lab.habit.crystallography import expand_habit_planes
from kikuchi_lab.habit.recipes import load_habit_recipe


def test_quartz_expansion_is_in_explicit_mtex_compatible_crystal_frame():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    phase, planes = expand_habit_planes(recipe)

    assert phase.space_group_number == 154
    assert phase.point_group == "32"
    assert phase.frame == "X||a*, Y||cross(c,a*), Z||c"
    assert len(planes) == 30
    assert {label: sum(p.family_label == label for p in planes) for label in "mrz"} == {
        "m": 6,
        "r": 6,
        "z": 6,
    }
    m_normals = np.array([p.normal for p in planes if p.family_label == "m"])
    assert np.max(np.abs(m_normals[:, 2])) <= 1e-12
    assert any(
        np.allclose(normal, [1.0, 0.0, 0.0], atol=1e-12)
        for normal in m_normals
    )
    assert all(np.linalg.norm(p.normal) == pytest.approx(1.0) for p in planes)


def test_expansion_keeps_positive_and_negative_rhombohedra_distinct():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    r = {tuple(np.round(p.normal, 10)) for p in planes if p.family_label == "r"}
    z = {tuple(np.round(p.normal, 10)) for p in planes if p.family_label == "z"}
    assert r.isdisjoint(z)


def test_expansion_rejects_zero_reciprocal_normal():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    invalid_face = replace(recipe.faces[0], family=(0, 0, 0, 0))
    invalid = replace(recipe, faces=(invalid_face, *recipe.faces[1:]))
    with pytest.raises(ValueError, match="zero reciprocal-plane normal"):
        expand_habit_planes(invalid)


def test_expansion_rejects_declared_space_group_mismatch():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    invalid = replace(recipe, phase=replace(recipe.phase, space_group_number=152))
    with pytest.raises(ValueError, match="space group disagrees"):
        expand_habit_planes(invalid)
