"""Deterministic labeled convex geometry for expanded crystal-habit planes."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.spatial import HalfspaceIntersection, QhullError

from kikuchi_lab.habit.crystallography import ExpandedPlane


@dataclass(frozen=True)
class PolygonFace:
    plane_id: str
    family_label: str
    family_indices: tuple[int, ...]
    symmetry_index: int
    normal: tuple[float, float, float]
    support_distance: float
    vertex_indices: tuple[int, ...]


@dataclass(frozen=True)
class LabeledPolygonMesh:
    vertices: np.ndarray
    faces: tuple[PolygonFace, ...]
    inactive_plane_ids: tuple[str, ...]


@dataclass(frozen=True)
class TriangleMesh:
    vertices: np.ndarray
    triangles: np.ndarray
    triangle_face_indices: np.ndarray


def _immutable_vertices(vertices: np.ndarray) -> np.ndarray:
    immutable = np.array(vertices, dtype=np.float64, copy=True)
    immutable.setflags(write=False)
    return immutable


def _immutable_int_array(
    values: object, *, width: int | None
) -> np.ndarray:
    immutable = np.asarray(values, dtype=np.int64)
    if width is not None:
        immutable = immutable.reshape(-1, width)
    else:
        immutable = immutable.reshape(-1)
    immutable = np.array(immutable, copy=True)
    immutable.setflags(write=False)
    return immutable


def _normalized_halfspace(plane: ExpandedPlane) -> tuple[np.ndarray, float]:
    normal = np.asarray(plane.normal, dtype=np.float64)
    magnitude = float(np.linalg.norm(normal))
    distance = float(plane.relative_distance)
    if (
        normal.shape != (3,)
        or not np.isfinite(normal).all()
        or not np.isfinite(magnitude)
        or magnitude <= 0.0
        or not np.isfinite(distance)
        or distance <= 0.0
    ):
        raise ValueError("habit planes require finite normals and positive support distances")
    return normal / magnitude, distance / magnitude


def _deduplicate_halfspaces(
    planes: tuple[ExpandedPlane, ...], relative_tolerance: float
) -> tuple[tuple[ExpandedPlane, ...], tuple[str, ...]]:
    groups: list[list[ExpandedPlane]] = []
    representatives: list[tuple[np.ndarray, float]] = []
    for plane in planes:
        normal, distance = _normalized_halfspace(plane)
        matching_index = next(
            (
                index
                for index, (existing_normal, existing_distance) in enumerate(
                    representatives
                )
                if np.allclose(
                    normal,
                    existing_normal,
                    atol=relative_tolerance,
                    rtol=relative_tolerance,
                )
                and np.isclose(
                    distance,
                    existing_distance,
                    atol=relative_tolerance
                    * max(abs(distance), abs(existing_distance), 1.0),
                    rtol=0.0,
                )
            ),
            None,
        )
        if matching_index is None:
            groups.append([plane])
            representatives.append((normal, distance))
        else:
            groups[matching_index].append(plane)

    selected: list[ExpandedPlane] = []
    duplicate_ids: list[str] = []
    for group in groups:
        ordered = sorted(group, key=lambda plane: plane.plane_id)
        selected.append(ordered[0])
        duplicate_ids.extend(plane.plane_id for plane in ordered[1:])
    return tuple(selected), tuple(duplicate_ids)


def _deduplicate_vertices(vertices: np.ndarray, relative_tolerance: float) -> np.ndarray:
    candidates = np.asarray(vertices, dtype=np.float64).reshape(-1, 3)
    if not np.isfinite(candidates).all():
        raise ValueError("habit planes do not define one stable bounded solid")
    scale = max(float(np.linalg.norm(candidates, axis=1).max(initial=0.0)), 1.0)
    tolerance = relative_tolerance * scale
    unique: list[np.ndarray] = []
    for candidate in sorted(candidates, key=lambda vertex: tuple(vertex)):
        if not any(
            np.allclose(candidate, existing, atol=tolerance, rtol=0.0)
            for existing in unique
        ):
            unique.append(candidate)
    return np.asarray(unique, dtype=np.float64).reshape(-1, 3)


def _counterclockwise_face_order(
    vertices: np.ndarray, members: np.ndarray, normal: np.ndarray
) -> tuple[int, ...]:
    face_vertices = vertices[members]
    centroid = face_vertices.mean(axis=0)
    unit_normal = normal / np.linalg.norm(normal)
    reference = np.eye(3)[int(np.argmin(np.abs(unit_normal)))]
    first_axis = np.cross(unit_normal, reference)
    first_axis /= np.linalg.norm(first_axis)
    second_axis = np.cross(unit_normal, first_axis)
    centered = face_vertices - centroid
    angles = np.arctan2(centered @ second_axis, centered @ first_axis)
    ordered = [int(index) for index in members[np.argsort(angles, kind="stable")]]

    anchor_position = ordered.index(min(ordered))
    ordered = ordered[anchor_position:] + ordered[:anchor_position]
    cross_sum = sum(
        (
            np.cross(vertices[left] - centroid, vertices[right] - centroid)
            for left, right in zip(ordered, ordered[1:] + ordered[:1], strict=True)
        ),
        start=np.zeros(3),
    )
    if np.dot(cross_sum, unit_normal) < 0.0:
        ordered = [ordered[0], *reversed(ordered[1:])]
    return tuple(ordered)


def _polygon_face(plane: ExpandedPlane, ordered: tuple[int, ...]) -> PolygonFace:
    return PolygonFace(
        plane_id=plane.plane_id,
        family_label=plane.family_label,
        family_indices=plane.family_indices,
        symmetry_index=plane.symmetry_index,
        normal=plane.normal,
        support_distance=plane.relative_distance,
        vertex_indices=ordered,
    )


def solve_convex_habit(
    planes: tuple[ExpandedPlane, ...], *, relative_tolerance: float = 1e-9
) -> LabeledPolygonMesh:
    """Intersect expanded planes and reconstruct their visible labeled polygons."""

    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0.0:
        raise ValueError("relative_tolerance must be a positive finite number")
    unique_planes, duplicate_ids = _deduplicate_halfspaces(
        planes, relative_tolerance
    )
    halfspaces = np.array(
        [(*plane.normal, -plane.relative_distance) for plane in unique_planes],
        dtype=np.float64,
    )
    try:
        raw_vertices = HalfspaceIntersection(
            halfspaces, np.zeros(3, dtype=np.float64)
        ).intersections
    except (QhullError, ValueError) as error:
        raise ValueError(
            "habit planes do not define one stable bounded solid"
        ) from error

    vertices = _deduplicate_vertices(raw_vertices, relative_tolerance)
    faces: list[PolygonFace] = []
    inactive: list[str] = []
    scale = max(float(np.linalg.norm(vertices, axis=1).max(initial=0.0)), 1.0)
    tolerance = relative_tolerance * scale
    for plane in unique_planes:
        normal = np.asarray(plane.normal, dtype=np.float64)
        members = np.flatnonzero(
            np.abs(vertices @ normal - plane.relative_distance) <= tolerance
        )
        if len(members) < 3:
            inactive.append(plane.plane_id)
            continue
        ordered = _counterclockwise_face_order(vertices, members, normal)
        faces.append(_polygon_face(plane, ordered))
    if not faces:
        raise ValueError("habit intersection has no visible polygon faces")
    return LabeledPolygonMesh(
        vertices=_immutable_vertices(vertices),
        faces=tuple(faces),
        inactive_plane_ids=tuple((*duplicate_ids, *inactive)),
    )


def orient_and_scale_habit(
    mesh: LabeledPolygonMesh,
    orientation_matrix: tuple[tuple[float, float, float], ...],
    maximum_dimension_mm: float,
) -> LabeledPolygonMesh:
    """Apply the recipe orientation, center, and normalize the maximum extent."""

    rotation = np.asarray(orientation_matrix, dtype=np.float64)
    oriented = mesh.vertices @ rotation.T
    extent = float(np.ptp(oriented, axis=0).max())
    if not np.isfinite(extent) or extent <= 0.0:
        raise ValueError("habit has no positive finite axis-aligned extent")
    center = (oriented.min(axis=0) + oriented.max(axis=0)) / 2.0
    centered = oriented - center
    factor = maximum_dimension_mm / extent
    rotated_faces: list[PolygonFace] = []
    for face in mesh.faces:
        normal = rotation @ np.asarray(face.normal, dtype=np.float64)
        rotated_faces.append(
            replace(
                face,
                normal=tuple(float(value) for value in normal),
                support_distance=float(
                    factor
                    * (face.support_distance - float(np.dot(normal, center)))
                ),
            )
        )
    return replace(
        mesh,
        vertices=_immutable_vertices(centered * factor),
        faces=tuple(rotated_faces),
    )


def triangulate_habit(mesh: LabeledPolygonMesh) -> TriangleMesh:
    """Triangulate every polygon as a deterministic outward-facing fan."""

    triangles: list[tuple[int, int, int]] = []
    owners: list[int] = []
    for face_index, face in enumerate(mesh.faces):
        anchor, *ring = face.vertex_indices
        for left, right in zip(ring, ring[1:], strict=False):
            triangle = (anchor, left, right)
            if (
                np.dot(
                    np.cross(
                        mesh.vertices[left] - mesh.vertices[anchor],
                        mesh.vertices[right] - mesh.vertices[anchor],
                    ),
                    face.normal,
                )
                < 0.0
            ):
                triangle = (anchor, right, left)
            triangles.append(triangle)
            owners.append(face_index)
    return TriangleMesh(
        vertices=_immutable_vertices(mesh.vertices),
        triangles=_immutable_int_array(triangles, width=3),
        triangle_face_indices=_immutable_int_array(owners, width=None),
    )

