"""Strict validation and deterministic export for spherical relief meshes."""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass, replace
from functools import lru_cache
from numbers import Real
from pathlib import Path

import numpy as np
import trimesh

from matplotlib import colormaps
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.globe_mesh import (
    GlobeGeometrySpec,
    ReliefMeshValidation,
    validate_globe_mesh,
)

from .mapping import ReliefGeometry
from .recipes import ReliefFDMContext
from .topology import IcosphereTopology, build_icosphere

_MIN_TRIANGLE_AREA_MM2 = 1e-12
_RADIAL_RANGE_TOLERANCE_MM = 1e-10
_FDM_FEATURE_FLOOR_MM = 0.8
_DIRECTION_NORM_TOLERANCE = 1e-12
_RADIAL_REPRESENTATION_TOLERANCE_MM = 1e-10
_CANONICAL_SUBDIVISIONS = 7
_CANONICAL_BASE_RADIUS_MM = 40.0
_CANONICAL_MAXIMUM_RELIEF_MM = 1.2

RELIEF_STL_SERIALIZATION_CONTRACT = "trimesh-binary-stl/process-false/v1"
RELIEF_FIELD_NPZ_SERIALIZATION_CONTRACT = "zip-stored-npy/fixed-order-1980-epoch-mode-0600/v1"
RELIEF_PREVIEW_RENDER_CONTRACT = "matplotlib-figure-canvas-agg/900x900-rgba/v1"
RELIEF_PREVIEW_STYLE_CONTRACT = "gray-relief-fixed-view-light-inset/v1"
RELIEF_VALIDATION_JSON_SCHEMA = "kikuchi.relief-mesh-validation/v1"

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
    norms = np.linalg.norm(directions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=_DIRECTION_NORM_TOLERANCE):
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
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"relief-topology-sha256-{digest}"


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
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"relief-geometry-sha256-{digest}"


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
    slopes = np.degrees(np.arctan(np.abs(radii[edges[:, 1]] - radii[edges[:, 0]]) / arc_lengths))
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


def _legacy_validate_relief_mesh(
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
    if (
        isinstance(geometry.base_radius_mm, bool)
        or isinstance(geometry.maximum_relief_mm, bool)
        or not np.isfinite((geometry.base_radius_mm, geometry.maximum_relief_mm)).all()
        or geometry.base_radius_mm <= 0.0
        or geometry.maximum_relief_mm <= 0.0
    ):
        raise ValueError("relief mesh validation failed: positive finite configured dimensions")

    radii = np.linalg.norm(vertices, axis=1)
    representation_failures: list[str] = []
    if np.any(radii_ledger <= 0.0):
        representation_failures.append("positive radii_mm")
    if np.any(radii_ledger < geometry.base_radius_mm - _RADIAL_RANGE_TOLERANCE_MM) or np.any(
        radii_ledger
        > geometry.base_radius_mm + geometry.maximum_relief_mm + _RADIAL_RANGE_TOLERANCE_MM
    ):
        representation_failures.append("configured radial range")
    if np.any(radii < geometry.base_radius_mm - _RADIAL_RANGE_TOLERANCE_MM) or np.any(
        radii > geometry.base_radius_mm + geometry.maximum_relief_mm + _RADIAL_RANGE_TOLERANCE_MM
    ):
        representation_failures.append("actual vertex radial range")
    if not np.allclose(
        radii,
        radii_ledger,
        rtol=0.0,
        atol=_RADIAL_REPRESENTATION_TOLERANCE_MM,
    ) or not np.allclose(
        vertices,
        geometry.directions * radii_ledger[:, None],
        rtol=0.0,
        atol=_RADIAL_REPRESENTATION_TOLERANCE_MM,
    ):
        representation_failures.append("radial representation")
    if np.any(filtered < 0.0) or np.any(filtered > 1.0):
        representation_failures.append("filtered values in [0, 1]")
    expected_radii = geometry.base_radius_mm + geometry.maximum_relief_mm * filtered
    if not np.allclose(
        radii_ledger,
        expected_radii,
        rtol=0.0,
        atol=_RADIAL_REPRESENTATION_TOLERANCE_MM,
    ):
        representation_failures.append(
            "filtered values consistent with configured radius displacement"
        )
    if representation_failures:
        raise ValueError("relief mesh validation failed: " + ", ".join(representation_failures))

    inspected = _trimesh(geometry)
    duplicate_count = duplicate_triangle_count(geometry.faces)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= _MIN_TRIANGLE_AREA_MM2))
    certificate = _radial_certificate(geometry)
    certificate_tolerance = 1e-12 * geometry.base_radius_mm**3
    failures: list[str] = []
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
        topology_fingerprint=topology_fingerprint,
        geometry_fingerprint=_geometry_fingerprint(geometry, topology_fingerprint),
        self_intersection_contract="positive-radial-bijection-over-canonical-icosphere",
        warnings=_relief_fdm_warnings(geometry, inspected, fdm_context),
    )


def validate_relief_mesh(
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    fdm_context: ReliefFDMContext | None,
) -> ReliefMeshValidation:
    """Compatibility adapter for the generic globe mesh proof."""
    if (
        isinstance(geometry.base_radius_mm, bool)
        or isinstance(geometry.maximum_relief_mm, bool)
        or not np.isfinite((geometry.base_radius_mm, geometry.maximum_relief_mm)).all()
        or geometry.base_radius_mm <= 0.0
        or geometry.maximum_relief_mm <= 0.0
    ):
        raise ValueError("relief mesh validation failed: positive finite configured dimensions")
    validation = validate_globe_mesh(
        geometry,
        topology,
        GlobeGeometrySpec(
            geometry.base_radius_mm * 2.0,
            geometry.maximum_relief_mm,
            topology.subdivisions,
        ),
    )
    return replace(
        validation,
        warnings=_relief_fdm_warnings(geometry, _trimesh(geometry), fdm_context),
    )


@lru_cache(maxsize=1)
def _approved_topology() -> IcosphereTopology:
    return build_icosphere(_CANONICAL_SUBDIVISIONS)


def validate_canonical_relief_mesh(
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    fdm_context: ReliefFDMContext | None,
) -> ReliefMeshValidation:
    """Accept only the approved full-resolution printable relief contract."""
    if topology.subdivisions != _CANONICAL_SUBDIVISIONS:
        raise ValueError("publishable relief requires the approved subdivision-7 topology")
    approved = _approved_topology()
    if (
        topology.topology_id != approved.topology_id
        or not np.array_equal(topology.directions, approved.directions)
        or not np.array_equal(topology.faces, approved.faces)
    ):
        raise ValueError("publishable relief differs from the approved canonical topology")
    if (
        geometry.base_radius_mm != _CANONICAL_BASE_RADIUS_MM
        or geometry.maximum_relief_mm != _CANONICAL_MAXIMUM_RELIEF_MM
    ):
        raise ValueError("publishable relief requires 40.0 mm base and 1.2 mm maximum relief")
    validation = validate_globe_mesh(
        geometry,
        topology,
        GlobeGeometrySpec(80.0, 1.2, _CANONICAL_SUBDIVISIONS),
    )
    return replace(
        validation,
        warnings=_relief_fdm_warnings(geometry, _trimesh(geometry), fdm_context),
    )


def _verify_accepted_validation(
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    validation: ReliefMeshValidation,
) -> ReliefMeshValidation:
    current = validate_canonical_relief_mesh(geometry, topology, fdm_context=None)
    if (
        not isinstance(validation, ReliefMeshValidation)
        or not validation.passed
        or validation.topology_fingerprint != current.topology_fingerprint
        or validation.geometry_fingerprint != current.geometry_fingerprint
    ):
        raise ValueError("accepted validation fingerprint does not match supplied relief mesh")
    return current


def relief_stl_bytes(
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    validation: ReliefMeshValidation,
) -> bytes:
    """Return deterministic binary STL bytes for a validated relief mesh."""
    _verify_accepted_validation(geometry, topology, validation)
    payload = _trimesh(geometry).export(file_type="stl")
    if not isinstance(payload, bytes):
        raise TypeError("Trimesh STL export did not return bytes")
    return payload


def _validate_field_artifact(
    artifact: ReliefFieldArtifact,
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
) -> None:
    if not isinstance(artifact, ReliefFieldArtifact):
        raise TypeError("artifact must be a ReliefFieldArtifact")
    if (
        not isinstance(artifact.directions, np.ndarray)
        or artifact.directions.dtype != np.float64
        or artifact.directions.ndim != 2
        or artifact.directions.shape[1:] != (3,)
    ):
        raise ValueError("field artifact directions has wrong dtype or shape")
    count = artifact.directions.shape[0]
    if not isinstance(artifact.faces, np.ndarray) or artifact.faces.ndim != 2:
        raise ValueError("field artifact faces has wrong dtype or shape")
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
        if array.flags.writeable:
            raise ValueError(f"field artifact {name} must be read-only")
        if not array.flags.owndata:
            raise ValueError(f"field artifact {name} must own its data")
        if not array.flags.c_contiguous:
            raise ValueError(f"field artifact {name} must be C-contiguous")
        if not np.isfinite(array).all():
            raise ValueError(f"field artifact {name} must be finite")
    if not np.array_equal(artifact.directions, topology.directions):
        raise ValueError("field artifact canonical directions are misaligned")
    if not np.array_equal(artifact.faces, topology.faces):
        raise ValueError("field artifact faces differ from canonical topology")
    if not np.array_equal(artifact.radii_mm, geometry.radii_mm):
        raise ValueError("field artifact radii_mm differ from canonical geometry")
    if not np.array_equal(artifact.filtered, geometry.filtered_values):
        raise ValueError("field artifact filtered values differ from canonical geometry")
    if not np.isin(artifact.hemisphere, (-1, 1)).all():
        raise ValueError("field artifact hemisphere values must be -1 or 1")
    expected_hemisphere = np.where(artifact.directions[:, 2] >= 0.0, 1, -1)
    if not np.array_equal(artifact.hemisphere, expected_hemisphere):
        raise ValueError("field artifact hemisphere alignment differs from directions")
    direction_norms = np.linalg.norm(artifact.directions, axis=1)
    if not np.allclose(direction_norms, 1.0, rtol=0.0, atol=_DIRECTION_NORM_TOLERANCE):
        raise ValueError("field artifact directions must be finite unit vectors")
    if np.any(artifact.source_rows < 0):
        raise ValueError("field artifact source_rows must be nonnegative")
    if np.any(artifact.source_columns < 0):
        raise ValueError("field artifact source_columns must be nonnegative")
    if np.any(artifact.weights < 0.0):
        raise ValueError("field artifact weights must be nonnegative")
    if not np.allclose(artifact.weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("field artifact weights rows must sum to 1")
    if np.any(artifact.mapped < 0.0) or np.any(artifact.mapped > 1.0):
        raise ValueError("field artifact mapped values must lie in [0, 1]")
    if np.any(artifact.filtered < 0.0) or np.any(artifact.filtered > 1.0):
        raise ValueError("field artifact filtered values must lie in [0, 1]")
    if np.any(artifact.faces < 0) or np.any(artifact.faces >= count):
        raise ValueError("field artifact faces are not aligned to directions")


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, np.ascontiguousarray(array), allow_pickle=False)
    return stream.getvalue()


def relief_field_npz_bytes(
    artifact: ReliefFieldArtifact,
    geometry: ReliefGeometry,
    topology: IcosphereTopology,
    validation: ReliefMeshValidation,
) -> bytes:
    """Return a deterministic fixed-inventory uncompressed NPZ field ledger."""
    _validate_field_artifact(artifact, geometry, topology)
    _verify_accepted_validation(geometry, topology, validation)
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
    topology: IcosphereTopology,
    validation: ReliefMeshValidation,
    *,
    lower_percentile: float,
    upper_percentile: float,
    gamma: float,
    filter_fwhm_mm: float,
) -> None:
    """Write the accepted full-resolution relief mesh as a fixed RGBA PNG."""
    parameters = (lower_percentile, upper_percentile, gamma, filter_fwhm_mm)
    if any(
        isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) for value in parameters
    ):
        raise ValueError("relief preview parameters are invalid")
    if (
        not np.isfinite(parameters).all()
        or not 0.0 <= lower_percentile < upper_percentile <= 100.0
        or gamma <= 0.0
        or filter_fwhm_mm <= 0.0
    ):
        raise ValueError("relief preview parameters are invalid")
    current_validation = _verify_accepted_validation(geometry, topology, validation)
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
    triangles = vertices[faces]
    face_values = filtered[faces].mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    light = np.array([0.35, -0.45, 0.82], dtype=np.float64)
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0.0, 1.0)
    rgba = colormaps["gray"](face_values)
    rgba[:, :3] *= shade[:, None]

    figure = Figure(figsize=(9, 9), dpi=100, facecolor="white")
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="3d")
    axes.add_collection3d(Poly3DCollection(triangles, facecolors=rgba, linewidths=0))
    radius = geometry.base_radius_mm + geometry.maximum_relief_mm
    axes.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(-radius, radius))
    axes.set_box_aspect((1, 1, 1))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    inset = (
        f"base radius: {geometry.base_radius_mm:.3f} mm\n"
        f"observed relief: "
        f"{current_validation.maximum_radius_mm - current_validation.minimum_radius_mm:.3f} mm\n"
        f"mapping: p{lower_percentile:g}-p{upper_percentile:g}, gamma {gamma:g}\n"
        f"filter FWHM: {filter_fwhm_mm:.3f} mm"
    )
    figure.text(0.025, 0.025, inset, ha="left", va="bottom", family="monospace")
    canvas.print_png(
        Path(path),
        metadata={"Software": "kikuchi-lab"},
    )
    figure.clear()
