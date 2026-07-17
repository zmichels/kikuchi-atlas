"""Deterministic project-owned geodesic sphere topology."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from kikuchi_lab.model.identity import stable_id

_PHI = (1.0 + np.sqrt(5.0)) / 2.0
_SEED_VERTICES = np.array(
    [
        (-1, _PHI, 0),
        (1, _PHI, 0),
        (-1, -_PHI, 0),
        (1, -_PHI, 0),
        (0, -1, _PHI),
        (0, 1, _PHI),
        (0, -1, -_PHI),
        (0, 1, -_PHI),
        (_PHI, 0, -1),
        (_PHI, 0, 1),
        (-_PHI, 0, -1),
        (-_PHI, 0, 1),
    ],
    dtype=np.float64,
)
_SEED_FACES = np.array(
    [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),
        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),
        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),
        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ],
    dtype=np.int64,
)


@dataclass(frozen=True)
class IcosphereTopology:
    """Immutable vertices, faces, and provenance identity for one icosphere."""

    topology_id: str
    subdivisions: int
    directions: np.ndarray
    faces: np.ndarray


def _unit(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


def _immutable_float_array(value: object, *, width: int) -> np.ndarray:
    converted = np.array(value, dtype=np.float64, order="C", copy=True).reshape(-1, width)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.float64).reshape(converted.shape)


def _immutable_int_array(value: object, *, width: int) -> np.ndarray:
    converted = np.array(value, dtype=np.int64, order="C", copy=True).reshape(-1, width)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.int64).reshape(converted.shape)


def _sha256_array(value: np.ndarray) -> str:
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


_NORMALIZED_SEED = np.array([_unit(row) for row in _SEED_VERTICES], dtype=np.float64)
_SEED_TRIANGLES = _NORMALIZED_SEED[_SEED_FACES]
_SEED_A, _SEED_B, _SEED_C = _SEED_TRIANGLES.transpose(1, 0, 2)
if not np.all(
    np.einsum(
        "ij,ij->i",
        np.cross(_SEED_B - _SEED_A, _SEED_C - _SEED_A),
        _SEED_A,
    )
    > 0
):
    raise RuntimeError("fixed icosahedron seed faces must have outward orientation")


def build_icosphere(subdivisions: int) -> IcosphereTopology:
    """Build the fixed-seed icosphere using deterministic midpoint insertion."""
    if (
        isinstance(subdivisions, bool)
        or not isinstance(subdivisions, int)
        or not 0 <= subdivisions <= 7
    ):
        raise ValueError("subdivisions must be an integer in [0, 7]")

    vertices = [_unit(row) for row in _SEED_VERTICES]
    faces = [tuple(int(value) for value in face) for face in _SEED_FACES]
    for _ in range(subdivisions):
        midpoints: dict[tuple[int, int], int] = {}

        def midpoint(left: int, right: int) -> int:
            key = tuple(sorted((left, right)))
            if key not in midpoints:
                midpoints[key] = len(vertices)
                vertices.append(_unit(vertices[left] + vertices[right]))
            return midpoints[key]

        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
        faces = refined

    direction_array = _immutable_float_array(vertices, width=3)
    face_array = _immutable_int_array(faces, width=3)
    identity = {
        "contract": "fixed-icosahedron-sorted-edge-midpoint/v1",
        "subdivisions": subdivisions,
        "directions_sha256": _sha256_array(direction_array),
        "faces_sha256": _sha256_array(face_array),
    }
    return IcosphereTopology(
        stable_id("icosphere", identity), subdivisions, direction_array, face_array
    )
