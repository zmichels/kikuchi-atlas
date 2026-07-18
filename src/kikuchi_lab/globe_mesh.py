"""Source-agnostic construction and validation for radial globe meshes."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

import numpy as np
import trimesh

from kikuchi_lab.model.identity import canonical_json, plain_data

if TYPE_CHECKING:
    from kikuchi_lab.relief.topology import IcosphereTopology

_MIN_TRIANGLE_AREA_MM2 = 1e-12
_RADIAL_RANGE_TOLERANCE_MM = 1e-10
_DIRECTION_NORM_TOLERANCE = 1e-12
_RADIAL_REPRESENTATION_TOLERANCE_MM = 1e-10


def _is_topology(value: object) -> bool:
    """Avoid importing the relief package while its compatibility facade loads."""
    from kikuchi_lab.relief.topology import IcosphereTopology

    return isinstance(value, IcosphereTopology)


def _immutable_int_array(value: object, *, width: int | None = None) -> np.ndarray:
    converted = np.array(value, dtype=np.int64, order="C", copy=True)
    if width is not None:
        converted = converted.reshape(-1, width)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.int64).reshape(converted.shape)


def _immutable_float_array(value: object) -> np.ndarray:
    converted = np.array(value, dtype=np.float64, order="C", copy=True).reshape(-1)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.float64)


def _immutable_float_matrix(value: object, *, width: int) -> np.ndarray:
    converted = np.array(value, dtype=np.float64, order="C", copy=True).reshape(-1, width)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.float64).reshape(converted.shape)


def _positive_finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{field} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return number


@dataclass(frozen=True)
class GlobeGeometrySpec:
    """Physical dimensions and topology resolution for a radial globe."""

    base_diameter_mm: float
    maximum_relief_mm: float
    subdivisions: int

    def __post_init__(self) -> None:
        _positive_finite_number(self.base_diameter_mm, field="base diameter")
        _positive_finite_number(self.maximum_relief_mm, field="maximum relief")
        if (
            isinstance(self.subdivisions, bool)
            or not isinstance(self.subdivisions, int)
            or self.subdivisions < 0
        ):
            raise ValueError("subdivisions must be a nonnegative integer")


@dataclass(frozen=True)
class ReliefGeometry:
    topology_id: str
    directions: np.ndarray
    faces: np.ndarray
    filtered_values: np.ndarray
    radii_mm: np.ndarray
    vertices: np.ndarray
    base_radius_mm: float
    maximum_relief_mm: float


@dataclass(frozen=True)
class ReliefMeshValidation:
    passed: bool
    watertight: bool
    winding_consistent: bool
    body_count: int
    euler_characteristic: int
    positive_volume: bool
    volume_mm3: float
    surface_area_mm2: float
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    minimum_radius_mm: float
    maximum_radius_mm: float
    degenerate_triangle_count: int
    duplicate_triangle_count: int
    radial_certificate_minimum: float
    radial_certificate_tolerance: float
    topology_fingerprint: str
    geometry_fingerprint: str
    self_intersection_contract: str
    warnings: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def build_radial_geometry(
    topology: IcosphereTopology, normalized_values: object, spec: GlobeGeometrySpec
) -> ReliefGeometry:
    """Displace a copied unit-sphere topology radially for any valid globe spec."""
    if not _is_topology(topology):
        raise TypeError("topology must be an IcosphereTopology")
    if not isinstance(spec, GlobeGeometrySpec):
        raise TypeError("spec must be a GlobeGeometrySpec")
    if topology.subdivisions != spec.subdivisions:
        raise ValueError("topology subdivisions must match globe geometry spec")
    try:
        values = np.asarray(normalized_values, dtype=np.float64).reshape(-1)
    except (TypeError, ValueError) as error:
        raise ValueError("normalized values must be finite and align with topology") from error
    if len(values) != len(topology.directions) or not np.isfinite(values).all():
        raise ValueError("normalized values must be finite and align with topology")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("normalized values must lie in [0, 1]")
    directions = _immutable_float_matrix(topology.directions, width=3)
    faces = _immutable_int_array(topology.faces, width=3)
    if not np.array_equal(faces, topology.faces):
        raise ValueError("globe faces must exactly preserve topology")
    base_radius = float(spec.base_diameter_mm) / 2.0
    radii = base_radius + float(spec.maximum_relief_mm) * values
    return ReliefGeometry(
        topology_id=topology.topology_id,
        directions=directions,
        faces=faces,
        filtered_values=_immutable_float_array(values),
        radii_mm=_immutable_float_array(radii),
        vertices=_immutable_float_matrix(directions * radii[:, None], width=3),
        base_radius_mm=base_radius,
        maximum_relief_mm=float(spec.maximum_relief_mm),
    )


def _trimesh(geometry: ReliefGeometry) -> trimesh.Trimesh:
    return trimesh.Trimesh(
        vertices=np.array(geometry.vertices, dtype=np.float64, copy=True),
        faces=np.array(geometry.faces, dtype=np.int64, copy=True),
        process=False,
        validate=False,
    )


def _edges(faces: np.ndarray) -> np.ndarray:
    array = np.asarray(faces, dtype=np.int64)
    edges = np.concatenate((array[:, :2], array[:, 1:], array[:, ::2]), axis=0)
    return np.sort(edges, axis=1)


def duplicate_triangle_count(faces: np.ndarray) -> int:
    canonical = np.sort(np.asarray(faces, dtype=np.int64), axis=1)
    return int(len(canonical) - len(np.unique(canonical, axis=0)))


def unique_edge_count(faces: np.ndarray) -> int:
    return int(len(np.unique(_edges(faces), axis=0)))


def _topology_failures(topology: IcosphereTopology) -> tuple[list[str], int]:
    faces, directions = np.asarray(topology.faces), np.asarray(topology.directions)
    failures: list[str] = []
    if (
        faces.ndim != 2
        or faces.shape[1:] != (3,)
        or faces.dtype != np.int64
        or directions.ndim != 2
        or directions.shape[1:] != (3,)
        or directions.dtype != np.float64
        or not np.isfinite(directions).all()
        or np.any(faces < 0)
        or np.any(faces >= len(directions))
    ):
        return ["canonical topology arrays"], 0
    if not np.allclose(
        np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=_DIRECTION_NORM_TOLERANCE
    ):
        failures.append("finite unit directions")
    duplicate_count = duplicate_triangle_count(faces)
    if duplicate_count:
        failures.append("triangle uniqueness")
    edges, incidence = np.unique(_edges(faces), axis=0, return_counts=True)
    if np.any(incidence != 2):
        failures.append("edge incidence exactly two")
    adjacency = [set() for _ in range(len(directions))]
    for left, right in edges:
        adjacency[int(left)].add(int(right))
        adjacency[int(right)].add(int(left))
    used, visited = set(int(index) for index in np.unique(faces)), set()
    if used:
        pending = [next(iter(used))]
        while pending:
            vertex = pending.pop()
            if vertex in visited:
                continue
            visited.add(vertex)
            pending.extend(adjacency[vertex] - visited)
    if visited != used or len(used) != len(directions):
        failures.append("one connected component")
    euler = len(directions) - len(edges) + len(faces)
    if euler != 2:
        failures.append("Euler characteristic 2")
    return failures, int(euler)


def _radial_certificate(geometry: ReliefGeometry) -> np.ndarray:
    a, b, c = np.moveaxis(np.asarray(geometry.vertices)[geometry.faces], 1, 0)
    return np.einsum("ij,ij->i", np.cross(b - a, c - a), a)


def _array_sha256(array: np.ndarray) -> str:
    value = np.asarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(value.shape).encode("ascii"))
    digest.update(np.ascontiguousarray(value).tobytes(order="C"))
    return digest.hexdigest()


def _topology_fingerprint(topology: IcosphereTopology) -> str:
    payload = {
        "topology_id": topology.topology_id,
        "subdivisions": topology.subdivisions,
        "directions_sha256": _array_sha256(topology.directions),
        "faces_sha256": _array_sha256(topology.faces),
    }
    return (
        "relief-topology-sha256-"
        + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    )


def _geometry_fingerprint(geometry: ReliefGeometry, topology_fingerprint: str) -> str:
    payload = {
        "topology_fingerprint": topology_fingerprint,
        "topology_id": geometry.topology_id,
        "base_radius_mm": geometry.base_radius_mm,
        "maximum_relief_mm": geometry.maximum_relief_mm,
        "directions_sha256": _array_sha256(geometry.directions),
        "faces_sha256": _array_sha256(geometry.faces),
        "filtered_values_sha256": _array_sha256(geometry.filtered_values),
        "radii_mm_sha256": _array_sha256(geometry.radii_mm),
        "vertices_sha256": _array_sha256(geometry.vertices),
    }
    return (
        "relief-geometry-sha256-"
        + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    )


def validate_globe_mesh(
    geometry: ReliefGeometry, topology: IcosphereTopology, spec: GlobeGeometrySpec
) -> ReliefMeshValidation:
    """Validate a radial globe mesh against an explicit, source-neutral spec."""
    if not isinstance(geometry, ReliefGeometry):
        raise TypeError("geometry must be a ReliefGeometry")
    if not _is_topology(topology):
        raise TypeError("topology must be an IcosphereTopology")
    if not isinstance(spec, GlobeGeometrySpec):
        raise TypeError("spec must be a GlobeGeometrySpec")
    if topology.subdivisions != spec.subdivisions:
        raise ValueError("topology subdivisions must match globe geometry spec")
    if geometry.topology_id != topology.topology_id:
        raise ValueError("relief mesh topology identity differs from canonical topology")
    if not np.array_equal(geometry.faces, topology.faces) or not np.array_equal(
        geometry.directions, topology.directions
    ):
        raise ValueError("relief mesh changed canonical topology")
    topology_failures, euler = _topology_failures(topology)
    if topology_failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(topology_failures))
    count = len(topology.directions)
    vertices = np.asarray(geometry.vertices)
    radii_ledger = np.asarray(geometry.radii_mm)
    filtered = np.asarray(geometry.filtered_values)
    if vertices.shape != (count, 3) or not np.isfinite(vertices).all():
        raise ValueError("relief mesh validation failed: finite vertices")
    if radii_ledger.shape != (count,) or not np.isfinite(radii_ledger).all():
        raise ValueError("relief mesh validation failed: finite aligned radii_mm")
    if filtered.shape != (count,) or not np.isfinite(filtered).all():
        raise ValueError("relief mesh validation failed: finite aligned filtered values")
    base_radius, relief = float(spec.base_diameter_mm) / 2.0, float(spec.maximum_relief_mm)
    if geometry.base_radius_mm != base_radius or geometry.maximum_relief_mm != relief:
        raise ValueError(
            "relief mesh validation failed: configured dimensions differ from globe geometry spec"
        )
    radii = np.linalg.norm(vertices, axis=1)
    failures: list[str] = []
    if np.any(radii_ledger <= 0.0):
        failures.append("positive radii_mm")
    if np.any(radii_ledger < base_radius - _RADIAL_RANGE_TOLERANCE_MM) or np.any(
        radii_ledger > base_radius + relief + _RADIAL_RANGE_TOLERANCE_MM
    ):
        failures.append("configured radial range")
    if np.any(radii < base_radius - _RADIAL_RANGE_TOLERANCE_MM) or np.any(
        radii > base_radius + relief + _RADIAL_RANGE_TOLERANCE_MM
    ):
        failures.append("actual vertex radial range")
    if not np.allclose(
        radii, radii_ledger, rtol=0.0, atol=_RADIAL_REPRESENTATION_TOLERANCE_MM
    ) or not np.allclose(
        vertices,
        geometry.directions * radii_ledger[:, None],
        rtol=0.0,
        atol=_RADIAL_REPRESENTATION_TOLERANCE_MM,
    ):
        failures.append("radial representation")
    if np.any(filtered < 0.0) or np.any(filtered > 1.0):
        failures.append("filtered values in [0, 1]")
    if not np.allclose(
        radii_ledger,
        base_radius + relief * filtered,
        rtol=0.0,
        atol=_RADIAL_REPRESENTATION_TOLERANCE_MM,
    ):
        failures.append("filtered values consistent with configured radius displacement")
    if failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(failures))
    inspected = _trimesh(geometry)
    duplicate_count = duplicate_triangle_count(geometry.faces)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= _MIN_TRIANGLE_AREA_MM2))
    certificate = _radial_certificate(geometry)
    certificate_tolerance = 1e-12 * base_radius**3
    failures = []
    if not inspected.is_watertight:
        failures.append("watertight")
    if not inspected.is_winding_consistent:
        failures.append("winding")
    if inspected.body_count != 1:
        failures.append("one connected body")
    if not inspected.is_volume or not np.isfinite(inspected.volume) or inspected.volume <= 0:
        failures.append("positive volume")
    if euler != 2:
        failures.append("Euler characteristic 2")
    if duplicate_count:
        failures.append("duplicate triangles")
    if degenerate_count:
        failures.append("degenerate triangles")
    if not np.isfinite(certificate).all() or np.any(certificate <= certificate_tolerance):
        failures.append("radial projection")
    if failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(failures))
    bounds = np.asarray(inspected.bounds, dtype=np.float64)
    topology_fingerprint = _topology_fingerprint(topology)
    return ReliefMeshValidation(
        True,
        True,
        True,
        1,
        2,
        True,
        float(inspected.volume),
        float(inspected.area),
        (tuple(bounds[0]), tuple(bounds[1])),
        float(radii.min()),
        float(radii.max()),
        0,
        0,
        float(certificate.min()),
        float(certificate_tolerance),
        topology_fingerprint,
        _geometry_fingerprint(geometry, topology_fingerprint),
        "positive-radial-bijection-over-canonical-icosphere",
        (),
    )
