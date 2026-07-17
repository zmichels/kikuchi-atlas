"""Order-independent parity checks against plain MTEX polygon ledgers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import directed_hausdorff

from kikuchi_lab.habit.geometry import LabeledPolygonMesh
from kikuchi_lab.model.identity import plain_data


PARITY_TOLERANCES = {
    "vertex_hausdorff": 1e-7,
    "relative_volume_difference": 1e-6,
    "maximum_face_normal_angle_rad": 1e-7,
}
_LEDGER_SCHEMA = "kikuchi.mtex-habit-reference/v1"
_CRYSTAL_FRAME = "X||a*, Y||cross(c,a*), Z||c"


@dataclass(frozen=True)
class MTEXParityReport:
    passed: bool
    mtex_version: str
    python_vertex_count: int
    mtex_vertex_count: int
    python_face_count: int
    mtex_face_count: int
    visible_family_labels: tuple[str, ...]
    vertex_hausdorff: float
    relative_volume_difference: float
    maximum_face_normal_angle_rad: float
    tolerances: Mapping[str, float]

    def to_dict(self) -> dict[str, object]:
        return plain_data(asdict(self))


def _load_and_validate_ledger(path: str | Path) -> dict[str, object]:
    ledger_path = Path(path)
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid MTEX reference ledger: {ledger_path}") from error
    if not isinstance(ledger, dict) or ledger.get("schema") != _LEDGER_SCHEMA:
        raise ValueError(f"MTEX reference ledger must use {_LEDGER_SCHEMA}")
    if ledger.get("frame") != _CRYSTAL_FRAME:
        raise ValueError(f"MTEX reference ledger must use frame {_CRYSTAL_FRAME}")
    mtex = ledger.get("mtex")
    if not isinstance(mtex, dict) or not isinstance(mtex.get("version"), str):
        raise ValueError("MTEX reference ledger must name its MTEX version")

    vertices = np.asarray(ledger.get("vertices"), dtype=float)
    if vertices.ndim != 2 or vertices.shape[1:] != (3,) or len(vertices) < 4:
        raise ValueError("MTEX reference ledger vertices must be an N-by-3 array")
    if not np.isfinite(vertices).all():
        raise ValueError("MTEX reference ledger vertices must be finite")

    faces = ledger.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("MTEX reference ledger must contain visible polygon faces")
    for face in faces:
        if not isinstance(face, dict):
            raise ValueError("MTEX reference ledger faces must be objects")
        indices = face.get("vertex_indices")
        normal = np.asarray(face.get("normal"), dtype=float)
        label = face.get("family_label")
        if not isinstance(indices, list) or len(indices) < 3:
            raise ValueError("MTEX reference ledger contains an empty visible face")
        if any(not isinstance(index, int) or index < 0 or index >= len(vertices) for index in indices):
            raise ValueError("MTEX reference ledger face has an invalid vertex index")
        if normal.shape != (3,) or not np.isfinite(normal).all() or np.linalg.norm(normal) <= 0:
            raise ValueError("MTEX reference ledger face normals must be finite and nonzero")
        if not isinstance(label, str) or not label:
            raise ValueError("MTEX reference ledger faces must have family labels")
    return ledger


def _unit_extent(vertices: np.ndarray) -> np.ndarray:
    values = np.asarray(vertices, dtype=np.float64)
    if values.ndim != 2 or values.shape[1:] != (3,) or not np.isfinite(values).all():
        raise ValueError("parity vertices must be a finite N-by-3 array")
    low = values.min(axis=0)
    high = values.max(axis=0)
    extent = float(np.max(high - low))
    if not np.isfinite(extent) or extent <= 0.0:
        raise ValueError("parity geometry must have positive axis-aligned extent")
    return (values - (low + high) / 2.0) / extent


def _polygon_cycle_volume(vertices: np.ndarray, cycles: list[tuple[int, ...]]) -> float:
    center = vertices.mean(axis=0)
    volume = 0.0
    for cycle in cycles:
        anchor = vertices[cycle[0]] - center
        for left, right in zip(cycle[1:], cycle[2:], strict=False):
            b = vertices[left] - center
            c = vertices[right] - center
            volume += abs(float(np.dot(anchor, np.cross(b, c)))) / 6.0
    return volume


def _polygon_volume_with_vertices(
    polygon: LabeledPolygonMesh, vertices: np.ndarray
) -> float:
    return _polygon_cycle_volume(
        vertices, [tuple(face.vertex_indices) for face in polygon.faces]
    )


def _ledger_polygon_volume(
    ledger: dict[str, object], *, vertices: np.ndarray
) -> float:
    faces = ledger["faces"]
    assert isinstance(faces, list)
    return _polygon_cycle_volume(
        vertices,
        [tuple(int(index) for index in face["vertex_indices"]) for face in faces],
    )


def _unit_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1)
    return values / norms[:, None]


def _match_labeled_face_normals(
    polygon: LabeledPolygonMesh, ledger: dict[str, object]
) -> tuple[float, set[str]]:
    faces = ledger["faces"]
    assert isinstance(faces, list)
    python_counts = Counter(face.family_label for face in polygon.faces)
    mtex_counts = Counter(str(face["family_label"]) for face in faces)
    labels = set(python_counts) | set(mtex_counts)
    if python_counts != mtex_counts:
        return float("inf"), labels

    maximum_angle = 0.0
    for label in sorted(labels):
        python_normals = _unit_rows(
            np.asarray(
                [face.normal for face in polygon.faces if face.family_label == label],
                dtype=np.float64,
            )
        )
        mtex_normals = _unit_rows(
            np.asarray(
                [face["normal"] for face in faces if face["family_label"] == label],
                dtype=np.float64,
            )
        )
        dots = np.clip(python_normals @ mtex_normals.T, -1.0, 1.0)
        python_ids, mtex_ids = linear_sum_assignment(1.0 - dots)
        angles = np.arccos(dots[python_ids, mtex_ids])
        maximum_angle = max(maximum_angle, float(angles.max(initial=0.0)))
    return maximum_angle, labels


def _parity_failures(
    polygon: LabeledPolygonMesh,
    ledger: dict[str, object],
    labels: set[str],
    vertex_hausdorff: float,
    volume_difference: float,
    normal_angle: float,
) -> list[str]:
    failures: list[str] = []
    if len(polygon.vertices) != len(ledger["vertices"]):
        failures.append("vertex_count")
    if len(polygon.faces) != len(ledger["faces"]):
        failures.append("face_count")
    python_labels = Counter(face.family_label for face in polygon.faces)
    ledger_labels = Counter(face["family_label"] for face in ledger["faces"])
    if python_labels != ledger_labels or labels != set(python_labels):
        failures.append("visible_family_labels")
    if vertex_hausdorff > PARITY_TOLERANCES["vertex_hausdorff"]:
        failures.append("vertex_hausdorff")
    if volume_difference > PARITY_TOLERANCES["relative_volume_difference"]:
        failures.append("relative_volume_difference")
    if normal_angle > PARITY_TOLERANCES["maximum_face_normal_angle_rad"]:
        failures.append("maximum_face_normal_angle_rad")
    return failures


def compare_mtex_reference(
    polygon: LabeledPolygonMesh, ledger_path: str | Path
) -> MTEXParityReport:
    """Compare labeled polygons in the fixed crystal frame without fitting rotation."""

    ledger = _load_and_validate_ledger(ledger_path)
    python_vertices = _unit_extent(polygon.vertices)
    mtex_vertices = _unit_extent(np.asarray(ledger["vertices"], dtype=float))
    vertex_hausdorff = max(
        directed_hausdorff(python_vertices, mtex_vertices)[0],
        directed_hausdorff(mtex_vertices, python_vertices)[0],
    )
    python_volume = _polygon_volume_with_vertices(polygon, python_vertices)
    mtex_volume = _ledger_polygon_volume(ledger, vertices=mtex_vertices)
    volume_difference = abs(python_volume - mtex_volume) / max(
        python_volume, mtex_volume
    )
    normal_angle, labels = _match_labeled_face_normals(polygon, ledger)
    failures = _parity_failures(
        polygon,
        ledger,
        labels,
        vertex_hausdorff,
        volume_difference,
        normal_angle,
    )
    if failures:
        raise ValueError("MTEX parity failed: " + ", ".join(failures))
    mtex = ledger["mtex"]
    assert isinstance(mtex, dict)
    return MTEXParityReport(
        passed=True,
        mtex_version=str(mtex["version"]),
        python_vertex_count=len(python_vertices),
        mtex_vertex_count=len(mtex_vertices),
        python_face_count=len(polygon.faces),
        mtex_face_count=len(ledger["faces"]),
        visible_family_labels=tuple(sorted(labels)),
        vertex_hausdorff=float(vertex_hausdorff),
        relative_volume_difference=float(volume_difference),
        maximum_face_normal_angle_rad=float(normal_angle),
        tolerances=dict(PARITY_TOLERANCES),
    )
