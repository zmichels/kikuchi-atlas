"""Strict validation and deterministic export for spherical relief meshes."""

from __future__ import annotations

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

from kikuchi_lab.globe_mesh import (
    GlobeGeometrySpec,
    ReliefMeshValidation,
    validate_globe_mesh,
)

from .mapping import ReliefGeometry
from .recipes import ReliefFDMContext
from .topology import IcosphereTopology, build_icosphere

_FDM_FEATURE_FLOOR_MM = 0.8
_DIRECTION_NORM_TOLERANCE = 1e-12
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


def _edges(faces: np.ndarray) -> np.ndarray:
    array = np.asarray(faces, dtype=np.int64)
    edges = np.concatenate((array[:, :2], array[:, 1:], array[:, ::2]), axis=0)
    return np.sort(edges, axis=1)


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
