from dataclasses import replace

import numpy as np
import pytest

from kikuchi_lab.habit.crystallography import ExpandedPlane, expand_habit_planes
from kikuchi_lab.habit.geometry import (
    orient_and_scale_habit,
    solve_convex_habit,
    triangulate_habit,
)
from kikuchi_lab.habit.recipes import load_habit_recipe


def _plane(label: str, normal: tuple[float, float, float]) -> ExpandedPlane:
    return ExpandedPlane(label, label, (1, 0, 0), 0, normal, 1.0)


def _box_planes(
    x_distance: float = 1.0,
    y_distance: float = 1.0,
    z_distance: float = 1.0,
) -> tuple[ExpandedPlane, ...]:
    return tuple(
        replace(_plane(label, normal), relative_distance=distance)
        for label, normal, distance in (
            ("+x", (1, 0, 0), x_distance),
            ("-x", (-1, 0, 0), x_distance),
            ("+y", (0, 1, 0), y_distance),
            ("-y", (0, -1, 0), y_distance),
            ("+z", (0, 0, 1), z_distance),
            ("-z", (0, 0, -1), z_distance),
        )
    )


def test_cube_has_ordered_labeled_faces_and_deterministic_triangles():
    polygon = solve_convex_habit(_box_planes())
    triangle = triangulate_habit(polygon)

    assert polygon.vertices.shape == (8, 3)
    assert len(polygon.faces) == 6
    assert polygon.inactive_plane_ids == ()
    assert tuple(face.plane_id for face in polygon.faces) == (
        "+x",
        "-x",
        "+y",
        "-y",
        "+z",
        "-z",
    )
    assert all(face.vertex_indices[0] == min(face.vertex_indices) for face in polygon.faces)
    assert triangle.triangles.shape == (12, 3)
    assert np.array_equal(triangle.triangles, triangulate_habit(polygon).triangles)
    assert np.array_equal(
        triangle.triangle_face_indices,
        np.repeat(np.arange(6, dtype=np.int64), 2),
    )
    for triangle_indices, face_index in zip(
        triangle.triangles, triangle.triangle_face_indices, strict=True
    ):
        a, b, c = polygon.vertices[triangle_indices]
        assert np.dot(np.cross(b - a, c - a), polygon.faces[face_index].normal) > 0


def test_quartz_matches_reference_topology_before_parity_metrics():
    recipe = load_habit_recipe("recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    polygon = solve_convex_habit(planes)
    scaled = orient_and_scale_habit(
        polygon, recipe.orientation_matrix, recipe.maximum_dimension_mm
    )

    assert polygon.vertices.shape == (32, 3)
    assert len(polygon.faces) == 18
    assert len(polygon.inactive_plane_ids) == 12
    assert np.ptp(scaled.vertices, axis=0).max() == pytest.approx(60.0, abs=1e-8)


def test_solver_rejects_unbounded_slab():
    with pytest.raises(ValueError, match="stable bounded solid"):
        solve_convex_habit((_plane("+x", (1, 0, 0)), _plane("-x", (-1, 0, 0))))


def test_solver_records_duplicate_plane_as_inactive():
    cube = _box_planes()
    duplicate = replace(cube[0], plane_id="duplicate-+x")

    mesh = solve_convex_habit((*cube, duplicate))

    assert "duplicate-+x" in mesh.inactive_plane_ids
    assert len(mesh.faces) == 6


def test_orientation_swaps_rectangular_x_y_extents_before_normalization():
    rectangle = solve_convex_habit(_box_planes(3.0, 2.0, 1.0))
    rotation = (
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )

    scaled = orient_and_scale_habit(rectangle, rotation, 12.0)

    assert np.ptp(scaled.vertices, axis=0) == pytest.approx((8.0, 12.0, 4.0))
    assert np.ptp(scaled.vertices, axis=0).max() == pytest.approx(12.0)
    assert np.mean(scaled.vertices, axis=0) == pytest.approx((0.0, 0.0, 0.0))
    assert tuple(face.plane_id for face in scaled.faces) == tuple(
        face.plane_id for face in rectangle.faces
    )

