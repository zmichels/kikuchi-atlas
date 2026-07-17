"""Strict validation and deterministic export for spherical relief meshes."""

from __future__ import annotations

import io
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from kikuchi_lab.model.identity import plain_data

from .mapping import ReliefGeometry
from .recipes import ReliefFDMContext
from .topology import IcosphereTopology

_MIN_TRIANGLE_AREA_MM2 = 1e-12
_RADIAL_RANGE_TOLERANCE_MM = 1e-10
_FDM_FEATURE_FLOOR_MM = 0.8

FIELD_ARRAY_ORDER = (
    "directions",
    "hemisphere",
    "source_rows",
    "source_columns",
    "weights",
    "sampled_raw",
    "mapped",
    "filtered",
    "radii_mm",
    "faces",
)


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
    self_intersection_contract: str
    warnings: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


@dataclass(frozen=True)
class ReliefFieldArtifact:
    directions: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray
    sampled_raw: np.ndarray
    mapped: np.ndarray
    filtered: np.ndarray
    radii_mm: np.ndarray
    faces: np.ndarray


def _trimesh(geometry: ReliefGeometry) -> trimesh.Trimesh:
    return trimesh.Trimesh(
        vertices=np.array(geometry.vertices, dtype=np.float64, copy=True),
        faces=np.array(geometry.faces, dtype=np.int64, copy=True),
        process=False,
        validate=False,
    )


def _canonical_faces(faces: np.ndarray) -> np.ndarray:
    return np.sort(np.asarray(faces, dtype=np.int64), axis=1)


def duplicate_triangle_count(faces: np.ndarray) -> int:
    canonical = _canonical_faces(faces)
    return int(len(canonical) - len(np.unique(canonical, axis=0)))


def _edges(faces: np.ndarray) -> np.ndarray:
    array = np.asarray(faces, dtype=np.int64)
    edges = np.concatenate((array[:, :2], array[:, 1:], array[:, ::2]), axis=0)
    return np.sort(edges, axis=1)


def unique_edge_count(faces: np.ndarray) -> int:
    return int(len(np.unique(_edges(faces), axis=0)))


def _canonical_topology_failures(topology: IcosphereTopology) -> tuple[list[str], int]:
    faces = np.asarray(topology.faces)
    directions = np.asarray(topology.directions)
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
    used = set(int(index) for index in np.unique(faces))
    visited: set[int] = set()
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


def _relief_fdm_warnings(
    geometry: ReliefGeometry,
    inspected: trimesh.Trimesh,
    fdm_context: ReliefFDMContext | None,
) -> tuple[dict[str, object], ...]:
    if fdm_context is None:
        return ()

    vertices = np.array(geometry.vertices, dtype=np.float64, copy=True)
    directions = np.array(geometry.directions, dtype=np.float64, copy=True)
    radii = np.linalg.norm(vertices, axis=1)
    edges = np.unique(_edges(geometry.faces), axis=0)
    edge_vectors = vertices[edges[:, 1]] - vertices[edges[:, 0]]
    edge_lengths = np.linalg.norm(edge_vectors, axis=1)

    triangles = vertices[geometry.faces]
    triangle_edges = np.stack(
        (
            triangles[:, 1] - triangles[:, 0],
            triangles[:, 2] - triangles[:, 1],
            triangles[:, 0] - triangles[:, 2],
        ),
        axis=1,
    )
    longest_edges = np.linalg.norm(triangle_edges, axis=2).max(axis=1)
    altitudes = 2.0 * np.asarray(inspected.area_faces) / longest_edges

    dot = np.einsum("ij,ij->i", directions[edges[:, 0]], directions[edges[:, 1]])
    arc_lengths = geometry.base_radius_mm * np.arccos(np.clip(dot, -1.0, 1.0))
    slopes = np.degrees(
        np.arctan(np.abs(radii[edges[:, 1]] - radii[edges[:, 0]]) / arc_lengths)
    )
    face_normals = np.array(inspected.face_normals, dtype=np.float64, copy=True)
    downward_fraction = float(np.count_nonzero(face_normals[:, 2] < 0.0) / len(face_normals))
    return (
        {"code": "fdm_minimum_edge", "measured_mm": float(edge_lengths.min())},
        {
            "code": "fdm_minimum_triangle_altitude",
            "measured_mm": float(altitudes.min()),
        },
        {
            "code": "fdm_maximum_local_relief_slope",
            "measured_degrees": float(slopes.max()),
        },
        {
            "code": "fdm_radial_dynamic_range",
            "measured_mm": float(radii.max() - radii.min()),
        },
        {
            "code": "fdm_downward_face_fraction",
            "measured_fraction": downward_fraction,
        },
        {"code": "fdm_feature_floor", "configured_mm": _FDM_FEATURE_FLOOR_MM},
    )


def validate_relief_mesh(
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    fdm_context: ReliefFDMContext | None,
) -> ReliefMeshValidation:
    """Validate an unchanged canonical radial mesh without repairing it."""
    if geometry.topology_id != topology.topology_id:
        raise ValueError("relief mesh topology identity differs from canonical topology")
    if not np.array_equal(geometry.faces, topology.faces) or not np.array_equal(
        geometry.directions, topology.directions
    ):
        raise ValueError("relief mesh changed canonical topology")

    topology_failures, euler = _canonical_topology_failures(topology)
    if topology_failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(topology_failures))

    vertices = np.asarray(geometry.vertices)
    if vertices.shape != topology.directions.shape or not np.isfinite(vertices).all():
        raise ValueError("relief mesh validation failed: finite vertices")

    inspected = _trimesh(geometry)
    radii = np.linalg.norm(vertices, axis=1)
    duplicate_count = duplicate_triangle_count(geometry.faces)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= _MIN_TRIANGLE_AREA_MM2))
    certificate = _radial_certificate(geometry)
    certificate_tolerance = 1e-12 * geometry.base_radius_mm**3
    failures: list[str] = []
    if np.any(radii < geometry.base_radius_mm - _RADIAL_RANGE_TOLERANCE_MM) or np.any(
        radii
        > geometry.base_radius_mm
        + geometry.maximum_relief_mm
        + _RADIAL_RANGE_TOLERANCE_MM
    ):
        failures.append("configured radial range")
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
    return ReliefMeshValidation(
        passed=True,
        watertight=True,
        winding_consistent=True,
        body_count=1,
        euler_characteristic=2,
        positive_volume=True,
        volume_mm3=float(inspected.volume),
        surface_area_mm2=float(inspected.area),
        bounds_mm=(tuple(bounds[0]), tuple(bounds[1])),
        minimum_radius_mm=float(radii.min()),
        maximum_radius_mm=float(radii.max()),
        degenerate_triangle_count=0,
        duplicate_triangle_count=0,
        radial_certificate_minimum=float(certificate.min()),
        radial_certificate_tolerance=float(certificate_tolerance),
        self_intersection_contract="positive-radial-bijection-over-canonical-icosphere",
        warnings=_relief_fdm_warnings(geometry, inspected, fdm_context),
    )


def relief_stl_bytes(geometry: ReliefGeometry, topology: IcosphereTopology) -> bytes:
    """Return deterministic binary STL bytes for a validated relief mesh."""
    validate_relief_mesh(geometry, topology, fdm_context=None)
    payload = _trimesh(geometry).export(file_type="stl")
    if not isinstance(payload, bytes):
        raise TypeError("Trimesh STL export did not return bytes")
    return payload


def _validate_field_artifact(artifact: ReliefFieldArtifact) -> None:
    if not isinstance(artifact, ReliefFieldArtifact):
        raise TypeError("artifact must be a ReliefFieldArtifact")
    count = len(artifact.directions)
    expected = {
        "directions": (np.dtype(np.float64), (count, 3)),
        "hemisphere": (np.dtype(np.int8), (count,)),
        "source_rows": (np.dtype(np.int32), (count, 4)),
        "source_columns": (np.dtype(np.int32), (count, 4)),
        "weights": (np.dtype(np.float64), (count, 4)),
        "sampled_raw": (np.dtype(np.float64), (count,)),
        "mapped": (np.dtype(np.float64), (count,)),
        "filtered": (np.dtype(np.float64), (count,)),
        "radii_mm": (np.dtype(np.float64), (count,)),
        "faces": (np.dtype(np.int64), (len(artifact.faces), 3)),
    }
    for name in FIELD_ARRAY_ORDER:
        array = getattr(artifact, name)
        dtype, shape = expected[name]
        if not isinstance(array, np.ndarray) or array.dtype != dtype or array.shape != shape:
            raise ValueError(f"field artifact {name} has wrong dtype or shape")
        if not np.isfinite(array).all():
            raise ValueError(f"field artifact {name} must be finite")
    if not np.isin(artifact.hemisphere, (-1, 1)).all():
        raise ValueError("field artifact hemisphere values must be -1 or 1")
    if np.any(artifact.faces < 0) or np.any(artifact.faces >= count):
        raise ValueError("field artifact faces are not aligned to directions")


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, np.ascontiguousarray(array), allow_pickle=False)
    return stream.getvalue()


def relief_field_npz_bytes(artifact: ReliefFieldArtifact) -> bytes:
    """Return a deterministic fixed-inventory uncompressed NPZ field ledger."""
    _validate_field_artifact(artifact)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in FIELD_ARRAY_ORDER:
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, _npy_bytes(getattr(artifact, name)))
    return stream.getvalue()


def write_relief_preview(
    path: Path,
    geometry: ReliefGeometry,
    validation: ReliefMeshValidation,
    *,
    lower_percentile: float,
    upper_percentile: float,
    gamma: float,
    filter_fwhm_mm: float,
) -> None:
    """Write the accepted full-resolution relief mesh as a fixed RGBA PNG."""
    if not validation.passed:
        raise ValueError("relief preview requires an accepted mesh")
    vertices = np.array(geometry.vertices, dtype=np.float64, copy=True)
    faces = np.array(geometry.faces, dtype=np.int64, copy=True)
    filtered = np.array(geometry.filtered_values, dtype=np.float64, copy=True)
    if (
        vertices.ndim != 2
        or vertices.shape[1:] != (3,)
        or faces.ndim != 2
        or faces.shape[1:] != (3,)
        or filtered.shape != (len(vertices),)
        or not np.isfinite(vertices).all()
        or not np.isfinite(filtered).all()
    ):
        raise ValueError("relief preview geometry is invalid")
    radii = np.linalg.norm(vertices, axis=1)
    if not np.isclose(radii.min(), validation.minimum_radius_mm) or not np.isclose(
        radii.max(), validation.maximum_radius_mm
    ):
        raise ValueError("relief preview geometry differs from accepted mesh")

    triangles = vertices[faces]
    face_values = filtered[faces].mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    light = np.array([0.35, -0.45, 0.82], dtype=np.float64)
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0.0, 1.0)
    rgba = plt.get_cmap("gray")(face_values)
    rgba[:, :3] *= shade[:, None]

    figure = plt.figure(figsize=(9, 9), dpi=100, facecolor="white")
    axes = figure.add_subplot(111, projection="3d")
    axes.add_collection3d(Poly3DCollection(triangles, facecolors=rgba, linewidths=0))
    radius = geometry.base_radius_mm + geometry.maximum_relief_mm
    axes.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(-radius, radius))
    axes.set_box_aspect((1, 1, 1))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    inset = (
        f"base radius: {geometry.base_radius_mm:.3f} mm\n"
        f"observed relief: {validation.maximum_radius_mm - validation.minimum_radius_mm:.3f} mm\n"
        f"mapping: p{lower_percentile:g}-p{upper_percentile:g}, gamma {gamma:g}\n"
        f"filter FWHM: {filter_fwhm_mm:.3f} mm"
    )
    figure.text(0.025, 0.025, inset, ha="left", va="bottom", family="monospace")
    figure.savefig(
        Path(path),
        format="png",
        dpi=100,
        facecolor="white",
        transparent=False,
        metadata={"Software": "kikuchi-lab"},
    )
    plt.close(figure)
