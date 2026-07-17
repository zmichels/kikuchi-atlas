import hashlib
import io
from dataclasses import replace
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pytest
import trimesh

from kikuchi_lab.habit.crystallography import ExpandedPlane
from kikuchi_lab.habit.geometry import (
    LabeledPolygonMesh,
    PolygonFace,
    TriangleMesh,
    solve_convex_habit,
    triangulate_habit,
)
from kikuchi_lab.habit.mesh import stl_bytes, validate_triangle_mesh, write_habit_preview
from kikuchi_lab.habit.recipes import FDMContext


def _plane(label: str, normal: tuple[float, float, float]) -> ExpandedPlane:
    return ExpandedPlane(label, label, (1, 0, 0), 0, normal, 1.0)


def _box_planes() -> tuple[ExpandedPlane, ...]:
    return tuple(
        _plane(label, normal)
        for label, normal in (
            ("+x", (1, 0, 0)),
            ("-x", (-1, 0, 0)),
            ("+y", (0, 1, 0)),
            ("-y", (0, -1, 0)),
            ("+z", (0, 0, 1)),
            ("-z", (0, 0, -1)),
        )
    )


def _concave_prism() -> tuple[LabeledPolygonMesh, TriangleMesh]:
    vertices = np.array(
        [
            (0.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
            (2.0, 1.0, 0.0),
            (1.0, 1.0, 0.0),
            (1.0, 2.0, 0.0),
            (0.0, 2.0, 0.0),
            (0.0, 0.0, 1.0),
            (2.0, 0.0, 1.0),
            (2.0, 1.0, 1.0),
            (1.0, 1.0, 1.0),
            (1.0, 2.0, 1.0),
            (0.0, 2.0, 1.0),
        ]
    )
    faces = [
        PolygonFace("bottom", "body", (0, 0, -1), 0, (0.0, 0.0, -1.0), 0.0, (0, 5, 4, 3, 2, 1)),
        PolygonFace("top", "body", (0, 0, 1), 0, (0.0, 0.0, 1.0), 1.0, (6, 7, 8, 9, 10, 11)),
    ]
    triangles = [
        (0, 3, 1),
        (1, 3, 2),
        (0, 5, 3),
        (3, 5, 4),
        (6, 7, 9),
        (7, 8, 9),
        (6, 9, 11),
        (9, 10, 11),
    ]
    owners = [0] * 4 + [1] * 4
    ring = (0, 1, 2, 3, 4, 5)
    for edge_index, (left, right) in enumerate(zip(ring, (*ring[1:], ring[0]), strict=True)):
        edge = vertices[right] - vertices[left]
        normal = (float(edge[1]), float(-edge[0]), 0.0)
        magnitude = float(np.linalg.norm(normal))
        normal = tuple(value / magnitude for value in normal)
        faces.append(
            PolygonFace(
                f"side-{edge_index}",
                "body",
                (edge_index, 0, 0),
                edge_index,
                normal,
                0.0,
                (left, right, right + 6, left + 6),
            )
        )
        triangles.extend(((left, right, right + 6), (left, right + 6, left + 6)))
        owners.extend((edge_index + 2, edge_index + 2))
    polygon = LabeledPolygonMesh(vertices, tuple(faces), ())
    mesh = TriangleMesh(vertices, np.asarray(triangles), np.asarray(owners))
    return polygon, mesh


@pytest.fixture
def cube_polygon():
    return solve_convex_habit(_box_planes())


@pytest.fixture
def cube_triangles(cube_polygon):
    return triangulate_habit(cube_polygon)


def test_cube_validation_and_stl_export_do_not_mutate_geometry(cube_polygon, cube_triangles):
    before_vertices = cube_triangles.vertices.copy()
    before_faces = cube_triangles.triangles.copy()
    report = validate_triangle_mesh(cube_triangles, cube_polygon, fdm_context=None)
    payload = stl_bytes(cube_triangles)

    assert report.passed is True
    assert report.watertight is True
    assert report.winding_consistent is True
    assert report.body_count == 1
    assert report.convex is True
    assert report.volume == pytest.approx(8.0)
    assert report.surface_area == pytest.approx(24.0)
    assert report.bounds_mm == ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0))
    assert report.maximum_dimension_mm == pytest.approx(2.0)
    assert report.self_intersection_contract == "convex-watertight-volume-proof"
    assert report.to_dict()["warnings"] == []
    assert np.array_equal(cube_triangles.vertices, before_vertices)
    assert np.array_equal(cube_triangles.triangles, before_faces)
    assert payload == stl_bytes(cube_triangles)
    loaded = trimesh.load_mesh(file_obj=io.BytesIO(payload), file_type="stl", process=True)
    assert loaded.is_volume


def test_validation_rejects_missing_triangle_without_repair(cube_polygon, cube_triangles):
    broken = replace(cube_triangles, triangles=cube_triangles.triangles[:-1])
    before_vertices = broken.vertices.copy()
    before_faces = broken.triangles.copy()

    with pytest.raises(ValueError, match="watertight"):
        validate_triangle_mesh(broken, cube_polygon, fdm_context=None)

    assert np.array_equal(broken.vertices, before_vertices)
    assert np.array_equal(broken.triangles, before_faces)
    with pytest.raises(ValueError, match="watertight"):
        stl_bytes(broken)


def test_validation_rejects_duplicate_and_degenerate_triangles(cube_polygon, cube_triangles):
    duplicate = np.vstack((cube_triangles.triangles, cube_triangles.triangles[0]))
    duplicate_owners = np.append(
        cube_triangles.triangle_face_indices,
        cube_triangles.triangle_face_indices[0],
    )
    duplicate_mesh = TriangleMesh(
        cube_triangles.vertices,
        duplicate,
        duplicate_owners,
    )
    with pytest.raises(ValueError, match="duplicate triangles"):
        validate_triangle_mesh(duplicate_mesh, cube_polygon, fdm_context=None)

    degenerate = cube_triangles.triangles.copy()
    degenerate[0] = (degenerate[0, 0], degenerate[0, 0], degenerate[0, 2])
    degenerate_mesh = replace(cube_triangles, triangles=degenerate)
    with pytest.raises(ValueError, match="degenerate triangles"):
        validate_triangle_mesh(degenerate_mesh, cube_polygon, fdm_context=None)


def test_validation_rejects_multiple_closed_bodies_without_mutation(cube_polygon, cube_triangles):
    vertex_count = len(cube_triangles.vertices)
    vertices = np.vstack((cube_triangles.vertices, cube_triangles.vertices + (4.0, 0.0, 0.0)))
    triangles = np.vstack((cube_triangles.triangles, cube_triangles.triangles + vertex_count))
    owners = np.concatenate(
        (cube_triangles.triangle_face_indices, cube_triangles.triangle_face_indices)
    )
    multiple = TriangleMesh(vertices, triangles, owners)
    before_vertices = multiple.vertices.copy()
    before_triangles = multiple.triangles.copy()
    inspected = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)
    assert inspected.is_watertight
    assert inspected.is_winding_consistent
    assert inspected.body_count == 2

    with pytest.raises(ValueError, match="one connected body"):
        validate_triangle_mesh(multiple, cube_polygon, fdm_context=None)

    assert np.array_equal(multiple.vertices, before_vertices)
    assert np.array_equal(multiple.triangles, before_triangles)


def test_validation_rejects_closed_nonconvex_body_without_mutation():
    polygon, mesh = _concave_prism()
    before_vertices = mesh.vertices.copy()
    before_triangles = mesh.triangles.copy()
    inspected = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.triangles, process=False)
    assert inspected.is_watertight
    assert inspected.is_winding_consistent
    assert inspected.body_count == 1
    assert inspected.volume > 0.0
    assert not inspected.is_convex

    with pytest.raises(ValueError, match="convex"):
        validate_triangle_mesh(mesh, polygon, fdm_context=None)

    assert np.array_equal(mesh.vertices, before_vertices)
    assert np.array_equal(mesh.triangles, before_triangles)


def test_validation_rejects_non_positive_closed_volume_without_mutation(
    cube_polygon, cube_triangles
):
    inward = replace(cube_triangles, triangles=cube_triangles.triangles[:, ::-1])
    before_vertices = inward.vertices.copy()
    before_triangles = inward.triangles.copy()
    inspected = trimesh.Trimesh(vertices=inward.vertices, faces=inward.triangles, process=False)
    assert inspected.is_watertight
    assert inspected.is_winding_consistent
    assert inspected.body_count == 1
    assert inspected.volume < 0.0

    with pytest.raises(ValueError, match="positive volume"):
        validate_triangle_mesh(inward, cube_polygon, fdm_context=None)

    assert np.array_equal(inward.vertices, before_vertices)
    assert np.array_equal(inward.triangles, before_triangles)


def test_validation_rejects_triangle_face_provenance_mismatch(cube_polygon, cube_triangles):
    owners = cube_triangles.triangle_face_indices.copy()
    owners[0] = 1
    mismatched = replace(cube_triangles, triangle_face_indices=owners)

    with pytest.raises(ValueError, match="source polygon"):
        validate_triangle_mesh(mismatched, cube_polygon, fdm_context=None)


def test_validation_rejects_extra_triangle_face_provenance(cube_polygon, cube_triangles):
    owners = np.append(cube_triangles.triangle_face_indices, 0)
    mismatched = replace(cube_triangles, triangle_face_indices=owners)

    with pytest.raises(ValueError, match="one source polygon per triangle"):
        validate_triangle_mesh(mismatched, cube_polygon, fdm_context=None)


def test_validation_rejects_triangle_vertex_coordinates_outside_source_polygon(
    cube_polygon, cube_triangles
):
    translated = replace(cube_triangles, vertices=cube_triangles.vertices + 10.0)

    with pytest.raises(ValueError, match="vertex coordinates"):
        validate_triangle_mesh(translated, cube_polygon, fdm_context=None)


def test_validation_rejects_inward_triangle_provenance(cube_polygon, cube_triangles):
    faces = list(cube_polygon.faces)
    faces[0] = replace(faces[0], normal=tuple(-value for value in faces[0].normal))
    conflicting_polygon = replace(cube_polygon, faces=tuple(faces))

    with pytest.raises(ValueError, match="outward normal"):
        validate_triangle_mesh(cube_triangles, conflicting_polygon, fdm_context=None)


def test_fdm_warnings_are_advisory_and_identify_features(cube_polygon, cube_triangles):
    before = cube_triangles.vertices.copy()
    report = validate_triangle_mesh(
        cube_triangles,
        cube_polygon,
        fdm_context=FDMContext(nozzle_width_mm=3.0, layer_height_mm=3.0),
    )

    assert report.passed is True
    assert np.array_equal(cube_triangles.vertices, before)
    assert report.warnings
    assert all("threshold" in warning for warning in report.warnings)
    assert any("edge_id" in warning and "face_id" in warning for warning in report.warnings)
    assert any("triangle_id" in warning and "face_id" in warning for warning in report.warnings)
    assert any(
        warning.get("face_id") == "-z" and warning["code"] == "fdm_downward_face"
        for warning in report.warnings
    )


def test_preview_is_deterministic_rgba_png(tmp_path: Path, cube_polygon):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    write_habit_preview(first, cube_polygon)
    write_habit_preview(second, cube_polygon)
    assert (
        hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    )
    assert iio.imread(first).shape == (900, 900, 4)
