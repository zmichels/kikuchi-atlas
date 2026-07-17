"""Non-mutating validation and export for printable habit meshes."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import trimesh
from matplotlib import colormaps
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from kikuchi_lab.habit.geometry import LabeledPolygonMesh, TriangleMesh
from kikuchi_lab.habit.recipes import FDMContext
from kikuchi_lab.model.identity import plain_data

_MIN_TRIANGLE_AREA_MM2 = 1e-12
_DOWNWARD_FACE_THRESHOLD_DEGREES = 90.0


@dataclass(frozen=True)
class MeshValidation:
    passed: bool
    watertight: bool
    winding_consistent: bool
    body_count: int
    convex: bool
    volume: float
    surface_area: float
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    maximum_dimension_mm: float
    degenerate_triangle_count: int
    duplicate_triangle_count: int
    self_intersection_contract: str
    warnings: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def _trimesh(mesh: TriangleMesh) -> trimesh.Trimesh:
    return trimesh.Trimesh(
        vertices=np.array(mesh.vertices, dtype=np.float64, copy=True),
        faces=np.array(mesh.triangles, dtype=np.int64, copy=True),
        process=False,
        validate=False,
    )


def _duplicate_triangle_count(triangles: np.ndarray) -> int:
    canonical = np.sort(np.asarray(triangles, dtype=np.int64), axis=1)
    return int(len(canonical) - len(np.unique(canonical, axis=0)))


def _mesh_failures(
    inspected: trimesh.Trimesh, duplicate_count: int, degenerate_count: int
) -> list[str]:
    failures: list[str] = []
    if not inspected.is_watertight:
        failures.append("watertight")
    if not inspected.is_winding_consistent:
        failures.append("winding")
    if inspected.body_count != 1:
        failures.append("one connected body")
    if not inspected.is_convex:
        failures.append("convex")
    if not inspected.is_volume or not math.isfinite(inspected.volume) or inspected.volume <= 0:
        failures.append("positive volume")
    if duplicate_count:
        failures.append("duplicate triangles")
    if degenerate_count:
        failures.append("degenerate triangles")
    return failures


def _assert_triangle_face_provenance(mesh: TriangleMesh, polygon: LabeledPolygonMesh) -> None:
    if len(mesh.triangle_face_indices) < len(mesh.triangles):
        raise ValueError("triangle face provenance is missing a source polygon")
    for triangle_id, triangle in enumerate(mesh.triangles):
        face_index = int(mesh.triangle_face_indices[triangle_id])
        if face_index < 0 or face_index >= len(polygon.faces):
            raise ValueError(f"triangle {triangle_id} source polygon index {face_index} is invalid")
        face = polygon.faces[face_index]
        triangle_vertices = tuple(int(index) for index in triangle)
        if not set(triangle_vertices).issubset(face.vertex_indices):
            raise ValueError(
                f"triangle {triangle_id} vertices do not belong to source polygon {face.plane_id}"
            )
        if not np.array_equal(
            np.asarray(mesh.vertices)[triangle], np.asarray(polygon.vertices)[triangle]
        ):
            raise ValueError(
                f"triangle {triangle_id} vertex coordinates differ from source polygon "
                f"{face.plane_id}"
            )
        a, b, c = np.asarray(mesh.vertices)[triangle]
        if float(np.dot(np.cross(b - a, c - a), face.normal)) <= 0.0:
            raise ValueError(
                f"triangle {triangle_id} does not point along source polygon "
                f"{face.plane_id} outward normal"
            )


def _edge_warnings(polygon: LabeledPolygonMesh, fdm_context: FDMContext) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    for face in polygon.faces:
        ring = face.vertex_indices
        for left, right in zip(ring, (*ring[1:], ring[0]), strict=True):
            length = float(np.linalg.norm(polygon.vertices[right] - polygon.vertices[left]))
            if length < fdm_context.nozzle_width_mm:
                low, high = sorted((left, right))
                warnings.append(
                    {
                        "code": "fdm_short_edge",
                        "face_id": face.plane_id,
                        "edge_id": f"{face.plane_id}:v{low}-v{high}",
                        "measured_mm": length,
                        "threshold": {
                            "comparison": "less-than",
                            "value_mm": fdm_context.nozzle_width_mm,
                        },
                    }
                )
    return warnings


def _triangle_altitude_warnings(
    mesh: TriangleMesh,
    polygon: LabeledPolygonMesh,
    inspected: trimesh.Trimesh,
    fdm_context: FDMContext,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    vertices = np.asarray(mesh.vertices)
    for triangle_id, (triangle, area) in enumerate(
        zip(mesh.triangles, inspected.area_faces, strict=True)
    ):
        points = vertices[triangle]
        longest_edge = max(
            float(np.linalg.norm(points[(index + 1) % 3] - points[index])) for index in range(3)
        )
        altitude = 0.0 if longest_edge == 0.0 else float(2.0 * area / longest_edge)
        if altitude < fdm_context.layer_height_mm:
            face = polygon.faces[int(mesh.triangle_face_indices[triangle_id])]
            warnings.append(
                {
                    "code": "fdm_low_triangle_altitude",
                    "face_id": face.plane_id,
                    "triangle_id": triangle_id,
                    "measured_mm": altitude,
                    "threshold": {
                        "comparison": "less-than",
                        "value_mm": fdm_context.layer_height_mm,
                    },
                }
            )
    return warnings


def _downward_face_warnings(
    polygon: LabeledPolygonMesh,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    for face in polygon.faces:
        normal = np.asarray(face.normal, dtype=float)
        cosine = float(normal[2] / np.linalg.norm(normal))
        angle = math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))
        if angle > _DOWNWARD_FACE_THRESHOLD_DEGREES:
            warnings.append(
                {
                    "code": "fdm_downward_face",
                    "face_id": face.plane_id,
                    "measured_degrees_from_build_up": angle,
                    "threshold": {
                        "comparison": "greater-than",
                        "value_degrees_from_build_up": _DOWNWARD_FACE_THRESHOLD_DEGREES,
                    },
                }
            )
    return warnings


def _fdm_warnings(
    inspected: trimesh.Trimesh,
    mesh: TriangleMesh,
    polygon: LabeledPolygonMesh,
    fdm_context: FDMContext | None,
) -> tuple[dict[str, object], ...]:
    if fdm_context is None:
        return ()
    return tuple(
        [
            *_edge_warnings(polygon, fdm_context),
            *_triangle_altitude_warnings(mesh, polygon, inspected, fdm_context),
            *_downward_face_warnings(polygon),
        ]
    )


def validate_triangle_mesh(
    mesh: TriangleMesh,
    polygon: LabeledPolygonMesh,
    fdm_context: FDMContext | None,
) -> MeshValidation:
    """Prove the canonical mesh contract without repairing or mutating inputs."""

    inspected = _trimesh(mesh)
    duplicate_count = _duplicate_triangle_count(mesh.triangles)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= _MIN_TRIANGLE_AREA_MM2))
    provenance_error: ValueError | None = None
    try:
        _assert_triangle_face_provenance(mesh, polygon)
    except ValueError as error:
        provenance_error = error
    failures = _mesh_failures(inspected, duplicate_count, degenerate_count)
    if failures:
        raise ValueError("mesh validation failed: " + ", ".join(failures))
    if len(mesh.triangle_face_indices) != len(mesh.triangles):
        raise ValueError("triangle face provenance requires one source polygon per triangle")
    if provenance_error is not None:
        raise provenance_error
    bounds = np.asarray(inspected.bounds, dtype=float)
    return MeshValidation(
        passed=True,
        watertight=True,
        winding_consistent=True,
        body_count=1,
        convex=True,
        volume=float(inspected.volume),
        surface_area=float(inspected.area),
        bounds_mm=(tuple(bounds[0]), tuple(bounds[1])),
        maximum_dimension_mm=float(inspected.extents.max()),
        degenerate_triangle_count=0,
        duplicate_triangle_count=0,
        self_intersection_contract="convex-watertight-volume-proof",
        warnings=_fdm_warnings(inspected, mesh, polygon, fdm_context),
    )


def stl_bytes(mesh: TriangleMesh) -> bytes:
    """Return deterministic binary STL bytes for a canonical triangle mesh."""

    inspected = _trimesh(mesh)
    duplicate_count = _duplicate_triangle_count(mesh.triangles)
    degenerate_count = int(np.count_nonzero(inspected.area_faces <= _MIN_TRIANGLE_AREA_MM2))
    failures = _mesh_failures(inspected, duplicate_count, degenerate_count)
    if failures:
        raise ValueError("mesh validation failed: " + ", ".join(failures))
    payload = inspected.export(file_type="stl")
    if not isinstance(payload, bytes):
        raise TypeError("Trimesh STL export did not return bytes")
    return payload


def write_habit_preview(path: str | Path, polygon: LabeledPolygonMesh) -> None:
    """Write a deterministic fixed-view RGBA PNG of the labeled polygon mesh."""

    labels = sorted({face.family_label for face in polygon.faces})
    palette = colormaps["tab20"]
    colors = {label: palette(index / max(len(labels), 1)) for index, label in enumerate(labels)}
    figure = Figure(figsize=(9, 9), dpi=100, facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="3d")
    polygons = [polygon.vertices[np.asarray(face.vertex_indices)] for face in polygon.faces]
    collection = Poly3DCollection(
        polygons,
        facecolors=[colors[face.family_label] for face in polygon.faces],
        edgecolors="black",
        linewidths=0.8,
    )
    axes.add_collection3d(collection)
    minimum = np.min(polygon.vertices, axis=0)
    maximum = np.max(polygon.vertices, axis=0)
    center = (minimum + maximum) / 2.0
    half_span = float(np.max(maximum - minimum)) / 2.0
    for setter, midpoint in zip((axes.set_xlim, axes.set_ylim, axes.set_zlim), center, strict=True):
        setter(midpoint - half_span, midpoint + half_span)
    axes.set_box_aspect((1.0, 1.0, 1.0))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    axes.legend(
        handles=[
            Patch(facecolor=colors[label], edgecolor="black", label=label) for label in labels
        ],
        loc="upper right",
        title="Face family",
        framealpha=1.0,
    )
    figure.savefig(
        Path(path),
        format="png",
        dpi=100,
        transparent=False,
        metadata={"Software": "kikuchi-lab"},
    )
