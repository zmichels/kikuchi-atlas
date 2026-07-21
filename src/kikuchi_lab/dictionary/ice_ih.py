"""Fast, inspectable Ice Ih spherical candidate-cache primitives.

The cache is deliberately canonical rather than detector projected.  It turns
the checked two-hemisphere Ice Ih kinematical master into a symmetry-reduced
matrix of normalized spherical signals, suitable for fast cosine candidate
search.  A detector-to-sphere adapter is intentionally outside this module:
observed detector preprocessing and geometry must be declared by its caller.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
from uuid import uuid4

import numpy as np
from orix.quaternion import symmetry
from orix.sampling import get_sample_fundamental, sample_S2

from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id


_UNIT_TOLERANCE = 5.0e-13
_MIN_GRID_RESOLUTION_DEGREES = 0.1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@dataclass(frozen=True)
class CandidateMatch:
    """One ranked normalized-cosine match in a candidate cache."""

    entry_index: int
    score: float


@dataclass(frozen=True)
class IceIhCandidateDictionaryResult:
    """Identity and path of one atomically published Ice Ih candidate dictionary."""

    dictionary_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class IceIhCandidateDictionaryVerification:
    """Result of independently checking an Ice Ih candidate dictionary package."""

    dictionary_id: str
    path: Path
    entry_count: int
    expected_top_entry_index: int


@dataclass(frozen=True)
class CandidateRefinement:
    """Best local full-master refinement about one coarse candidate."""

    quaternion_wxyz: tuple[float, float, float, float]
    score: float
    local_entry_count: int


@dataclass(frozen=True)
class SyntheticRecovery:
    """Deterministic held-out synthetic coarse-to-refined recovery evidence."""

    reference_entry_index: int
    coarse_entry_index: int
    coarse_score: float
    coarse_error_degrees: float
    refined_quaternion_wxyz: tuple[float, float, float, float]
    refined_score: float
    refined_error_degrees: float
    local_entry_count: int
    held_out_quaternion_wxyz: tuple[float, float, float, float]


def _positive_resolution(value: float, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result < _MIN_GRID_RESOLUTION_DEGREES:
        raise ValueError(f"{name} must be at least {_MIN_GRID_RESOLUTION_DEGREES} degrees")
    return result


def _unit_vectors(value: object, *, name: str) -> np.ndarray:
    vectors = np.asarray(value, dtype=np.float64)
    if vectors.ndim != 2 or vectors.shape[1] != 3 or len(vectors) == 0:
        raise ValueError(f"{name} must be a non-empty (N, 3) array")
    if not np.all(np.isfinite(vectors)):
        raise ValueError(f"{name} must contain finite values")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError(f"{name} must contain unit vectors")
    return np.ascontiguousarray(vectors, dtype=np.float64)


def _unit_quaternions_wxyz(value: object) -> np.ndarray:
    quaternions = np.asarray(value, dtype=np.float64)
    if quaternions.ndim != 2 or quaternions.shape[1] != 4 or len(quaternions) == 0:
        raise ValueError("quaternions_wxyz must be a non-empty (N, 4) array")
    if not np.all(np.isfinite(quaternions)):
        raise ValueError("quaternions_wxyz must contain finite values")
    norms = np.linalg.norm(quaternions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError("quaternions_wxyz must be normalized")
    if np.any(quaternions[:, 0] < 0.0):
        raise ValueError("quaternions_wxyz must use a non-negative scalar component")
    return np.ascontiguousarray(quaternions, dtype=np.float64)


def _master(value: object) -> np.ndarray:
    master = np.asarray(value, dtype=np.float64)
    if (
        master.ndim != 3
        or master.shape[0] != 2
        or master.shape[1] != master.shape[2]
        or master.shape[1] < 3
    ):
        raise ValueError("master must have finite shape (2, N, N) with N >= 3")
    if not np.all(np.isfinite(master)):
        raise ValueError("master must contain finite values")
    return np.ascontiguousarray(master, dtype=np.float64)


def ice_ih_so3_orientations(resolution_degrees: float) -> np.ndarray:
    """Return a deterministic `6/mmm` fundamental-zone active wxyz grid.

    Orix stores rotations as scalar-first quaternions.  The cubochoric sampler
    is explicit here because it produces a symmetry-reduced *volume* sample;
    an Euler mesh would bias the sampling density and obscure its provenance.
    """
    resolution = _positive_resolution(resolution_degrees, name="orientation resolution")
    rotations = get_sample_fundamental(
        resolution=resolution,
        point_group=symmetry.D6h,
        method="cubochoric",
    )
    quaternions = np.asarray(rotations.data, dtype=np.float64).reshape(-1, 4)
    # q and -q represent the same rotation; the package uses w >= 0.
    quaternions[quaternions[:, 0] < 0.0] *= -1.0
    return _unit_quaternions_wxyz(quaternions)


def ice_ih_s2_directions(resolution_degrees: float) -> np.ndarray:
    """Return a deterministic, full-sphere spherified-cube sampling grid."""
    resolution = _positive_resolution(resolution_degrees, name="direction resolution")
    vectors = np.asarray(
        sample_S2(resolution, method="spherified_cube_edge").data,
        dtype=np.float64,
    ).reshape(-1, 3)
    return _unit_vectors(vectors, name="S2 directions")


def quaternion_rotation_matrices(quaternions_wxyz: object) -> np.ndarray:
    """Return active crystal-to-sample matrices for scalar-first quaternions."""
    quaternions = _unit_quaternions_wxyz(quaternions_wxyz)
    w, x, y, z = quaternions.T
    matrices = np.stack(
        (
            1.0 - 2.0 * (y * y + z * z),
            2.0 * (x * y - z * w),
            2.0 * (x * z + y * w),
            2.0 * (x * y + z * w),
            1.0 - 2.0 * (x * x + z * z),
            2.0 * (y * z - x * w),
            2.0 * (x * z - y * w),
            2.0 * (y * z + x * w),
            1.0 - 2.0 * (x * x + y * y),
        ),
        axis=1,
    ).reshape(-1, 3, 3)
    identity = np.eye(3, dtype=np.float64)
    if not np.allclose(
        matrices.transpose(0, 2, 1) @ matrices, identity, rtol=0.0, atol=_UNIT_TOLERANCE
    ):
        raise ValueError("quaternion rotations must be orthonormal")
    if not np.allclose(np.linalg.det(matrices), 1.0, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError("quaternion rotations must be right-handed")
    return np.ascontiguousarray(matrices, dtype=np.float64)


def quaternion_from_rotation_vectors_degrees(rotation_vectors_degrees: object) -> np.ndarray:
    """Convert right-handed rotation vectors in degrees to active wxyz quaternions."""
    vectors = np.asarray(rotation_vectors_degrees, dtype=np.float64)
    if vectors.ndim != 2 or vectors.shape[1] != 3 or len(vectors) == 0:
        raise ValueError("rotation_vectors_degrees must be a non-empty (N, 3) array")
    if not np.all(np.isfinite(vectors)):
        raise ValueError("rotation_vectors_degrees must contain finite values")
    angles = np.linalg.norm(vectors, axis=1)
    half_angles = np.radians(angles) / 2.0
    scale = np.zeros_like(angles)
    nonzero = angles > np.finfo(np.float64).eps
    scale[nonzero] = np.sin(half_angles[nonzero]) / angles[nonzero]
    quaternions = np.column_stack((np.cos(half_angles), vectors * scale[:, None]))
    quaternions[quaternions[:, 0] < 0.0] *= -1.0
    return _unit_quaternions_wxyz(quaternions)


def compose_quaternions_wxyz(left: object, right: object) -> np.ndarray:
    """Compose active rotations as ``left * right`` with NumPy broadcasting."""
    lhs = _unit_quaternions_wxyz(left)
    rhs = _unit_quaternions_wxyz(right)
    try:
        lhs, rhs = np.broadcast_arrays(lhs, rhs)
    except ValueError as error:
        raise ValueError(
            "left and right quaternion arrays must have broadcast-compatible shapes"
        ) from error
    w1, x1, y1, z1 = lhs.T
    w2, x2, y2, z2 = rhs.T
    composed = np.column_stack(
        (
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )
    )
    composed[composed[:, 0] < 0.0] *= -1.0
    return _unit_quaternions_wxyz(composed)


def quaternion_misorientation_degrees(left: object, right: object) -> float:
    """Return the sign-invariant angular separation of two active quaternions.

    This diagnostic intentionally does not quotient by crystal symmetry: callers
    use it to compare the known synthetic orientation with nearby candidates in
    one already selected local neighborhood.
    """
    lhs = _unit_quaternions_wxyz(np.asarray(left, dtype=np.float64).reshape(1, 4))[0]
    rhs = _unit_quaternions_wxyz(np.asarray(right, dtype=np.float64).reshape(1, 4))[0]
    dot = min(1.0, max(-1.0, abs(float(np.dot(lhs, rhs)))))
    return float(np.degrees(2.0 * np.arccos(dot)))


def sample_stereographic_master(master: object, directions: object) -> np.ndarray:
    """Bilinearly sample raw upper/lower Ice master values at S2 directions.

    The master uses a unit stereographic disk.  The upper plane owns the
    equator, matching the published Ice field contract.  Invalid square-grid
    corners carry zero interpolation weight rather than becoming phantom master
    samples near the circular boundary.
    """
    planes = _master(master)
    vectors = _unit_vectors(directions, name="directions")
    size = planes.shape[1]
    q = vectors[:, :2] / (1.0 + np.abs(vectors[:, 2, None]))
    coordinates = np.clip((q + 1.0) * (size - 1) / 2.0, 0.0, size - 1)
    col, row = coordinates.T
    r0 = np.floor(row).astype(np.intp)
    c0 = np.floor(col).astype(np.intp)
    r1 = np.minimum(r0 + 1, size - 1)
    c1 = np.minimum(c0 + 1, size - 1)
    dr = row - r0
    dc = col - c0

    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    valid = (
        coordinate[:, None] ** 2 + coordinate[None, :] ** 2 <= 1.0 + 32.0 * np.finfo(np.float64).eps
    )
    upper = vectors[:, 2] >= 0.0

    def corner(rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
        return np.where(upper, planes[0, rows, columns], planes[1, rows, columns])

    w00 = (1.0 - dr) * (1.0 - dc) * valid[r0, c0]
    w10 = dr * (1.0 - dc) * valid[r1, c0]
    w01 = (1.0 - dr) * dc * valid[r0, c1]
    w11 = dr * dc * valid[r1, c1]
    total = w00 + w10 + w01 + w11
    if np.any(total <= 0.0):
        raise ValueError("directions do not map to valid stereographic master samples")
    values = (
        w00 * corner(r0, c0) + w10 * corner(r1, c0) + w01 * corner(r0, c1) + w11 * corner(r1, c1)
    ) / total
    return np.ascontiguousarray(values, dtype=np.float64)


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    centered = values - np.mean(values, axis=1, keepdims=True)
    norms = np.linalg.norm(centered, axis=1)
    if np.any(~np.isfinite(norms)) or np.any(norms <= np.finfo(np.float64).eps):
        raise ValueError("candidate rows must have non-zero-variance signal")
    return np.ascontiguousarray(centered / norms[:, None], dtype=np.float32)


def build_candidate_matrix(
    master: object,
    quaternions_wxyz: object,
    directions: object,
    *,
    batch_size: int = 256,
) -> np.ndarray:
    """Build L2-normalized candidate rows using `I_sample(s)=I_crystal(R^-1 s)`.

    The implementation evaluates the inverse pullback as row vectors
    ``s @ R_cs``.  It neither applies a visual tone map nor smooths the master.
    """
    planes = _master(master)
    quaternions = _unit_quaternions_wxyz(quaternions_wxyz)
    samples = _unit_vectors(directions, name="directions")
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    matrices = quaternion_rotation_matrices(quaternions)
    result = np.empty((len(quaternions), len(samples)), dtype=np.float32)
    for start in range(0, len(quaternions), batch_size):
        stop = min(start + batch_size, len(quaternions))
        # R_cs maps column crystal vectors to sample vectors. For row samples,
        # the inverse pullback into crystal coordinates is s_row @ R_cs.
        crystal_directions = np.einsum("mj,bjk->bmk", samples, matrices[start:stop])
        raw = sample_stereographic_master(
            planes,
            crystal_directions.reshape(-1, 3),
        ).reshape(stop - start, len(samples))
        result[start:stop] = _normalize_rows(raw)
    return result


def _normalize_observed_signal(value: object, count: int) -> np.ndarray:
    observed = np.asarray(value, dtype=np.float64)
    if observed.shape != (count,) or not np.all(np.isfinite(observed)):
        raise ValueError(
            "observed signal must be a finite one-dimensional array matching cache width"
        )
    centered = observed - float(np.mean(observed))
    norm = float(np.linalg.norm(centered))
    if norm <= np.finfo(np.float64).eps:
        raise ValueError("observed signal must have non-zero variance")
    return np.ascontiguousarray(centered / norm, dtype=np.float32)


def rank_candidate_matrix(
    candidate_matrix: object,
    observed_signal: object,
    *,
    top_k: int = 8,
) -> tuple[CandidateMatch, ...]:
    """Rank an observed spherical signal with normalized cosine similarity."""
    cache = np.asarray(candidate_matrix, dtype=np.float32)
    if (
        cache.ndim != 2
        or cache.shape[0] == 0
        or cache.shape[1] == 0
        or not np.all(np.isfinite(cache))
    ):
        raise ValueError("candidate matrix must be a finite non-empty two-dimensional array")
    if type(top_k) is not int or not 1 <= top_k <= cache.shape[0]:
        raise ValueError("top_k must be a positive integer no greater than cache row count")
    row_norms = np.linalg.norm(cache.astype(np.float64), axis=1)
    if not np.allclose(row_norms, 1.0, rtol=0.0, atol=2e-6):
        raise ValueError("candidate matrix rows must already be L2-normalized")
    observed = _normalize_observed_signal(observed_signal, cache.shape[1])
    scores = np.asarray(cache @ observed, dtype=np.float64)
    ordered = np.lexsort((np.arange(len(scores)), -scores))[:top_k]
    return tuple(CandidateMatch(int(index), float(scores[index])) for index in ordered)


def local_refine_candidate(
    master: object,
    center_quaternion_wxyz: object,
    directions: object,
    observed_signal: object,
    *,
    half_width_degrees: float,
    step_degrees: float,
) -> CandidateRefinement:
    """Refine one coarse candidate on a full-master local SO(3) rotation-vector grid."""
    half_width = _positive_resolution(half_width_degrees, name="local half width")
    step = _positive_resolution(step_degrees, name="local step")
    if step > half_width:
        raise ValueError("local step must not exceed local half width")
    center = _unit_quaternions_wxyz(
        np.asarray(center_quaternion_wxyz, dtype=np.float64).reshape(1, 4)
    )
    coordinates = np.arange(-half_width, half_width + step * 0.5, step, dtype=np.float64)
    local_vectors = np.stack(
        np.meshgrid(coordinates, coordinates, coordinates, indexing="ij"), axis=-1
    ).reshape(-1, 3)
    deltas = quaternion_from_rotation_vectors_degrees(local_vectors)
    candidates = compose_quaternions_wxyz(np.repeat(center, len(deltas), axis=0), deltas)
    matrix = build_candidate_matrix(master, candidates, directions)
    best = rank_candidate_matrix(matrix, observed_signal, top_k=1)[0]
    quaternion = tuple(float(value) for value in candidates[best.entry_index])
    return CandidateRefinement(
        quaternion_wxyz=quaternion,
        score=best.score,
        local_entry_count=len(candidates),
    )


def run_synthetic_recovery(
    master: object,
    quaternions_wxyz: object,
    directions: object,
    candidate_matrix: object,
    *,
    held_out_rotation_vector_degrees: object,
    local_half_width_degrees: float = 5.0,
    local_step_degrees: float = 1.0,
) -> SyntheticRecovery:
    """Recover a deliberately off-grid synthetic orientation through both levels.

    The reference orientation is the cache entry nearest identity. The held-out
    orientation is generated by composing the declared small rotation vector;
    it is never inserted in the coarse cache. This is an integrity and frame
    proof, not an acquired-pattern accuracy result.
    """
    quaternions = _unit_quaternions_wxyz(quaternions_wxyz)
    samples = _unit_vectors(directions, name="directions")
    cache = np.asarray(candidate_matrix, dtype=np.float32)
    if cache.shape != (len(quaternions), len(samples)):
        raise ValueError("candidate matrix shape must match supplied quaternions and directions")
    vector = np.asarray(held_out_rotation_vector_degrees, dtype=np.float64).reshape(1, 3)
    delta = quaternion_from_rotation_vectors_degrees(vector)
    if quaternion_misorientation_degrees(delta[0], (1.0, 0.0, 0.0, 0.0)) <= 0.0:
        raise ValueError("held_out_rotation_vector_degrees must be non-zero")
    reference_index = int(np.argmax(quaternions[:, 0]))
    held_out = compose_quaternions_wxyz(quaternions[reference_index : reference_index + 1], delta)[
        0
    ]
    observed = build_candidate_matrix(master, held_out[None, :], samples)[0]
    coarse = rank_candidate_matrix(cache, observed, top_k=1)[0]
    refined = local_refine_candidate(
        master,
        quaternions[coarse.entry_index],
        samples,
        observed,
        half_width_degrees=local_half_width_degrees,
        step_degrees=local_step_degrees,
    )
    coarse_error = quaternion_misorientation_degrees(quaternions[coarse.entry_index], held_out)
    refined_error = quaternion_misorientation_degrees(refined.quaternion_wxyz, held_out)
    if not refined_error < coarse_error:
        raise ValueError("local refinement did not improve the held-out angular diagnostic")
    return SyntheticRecovery(
        reference_entry_index=reference_index,
        coarse_entry_index=coarse.entry_index,
        coarse_score=coarse.score,
        coarse_error_degrees=coarse_error,
        refined_quaternion_wxyz=refined.quaternion_wxyz,
        refined_score=refined.score,
        refined_error_degrees=refined_error,
        local_entry_count=refined.local_entry_count,
        held_out_quaternion_wxyz=tuple(float(value) for value in held_out),
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: object) -> None:
    _write_bytes(path, canonical_json(value).encode("utf-8"))


def _write_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.save(handle, np.ascontiguousarray(value), allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_tree(root: Path) -> None:
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _plain_mapping(value: Mapping[str, object], *, name: str) -> dict[str, object]:
    plain = plain_data(value)
    if not isinstance(plain, dict):
        raise TypeError(f"{name} must be a mapping")

    def reject_absolute_paths(item: object, location: str) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                reject_absolute_paths(child, f"{location}.{key}")
        elif isinstance(item, (list, tuple)):
            for index, child in enumerate(item):
                reject_absolute_paths(child, f"{location}[{index}]")
        elif isinstance(item, str) and (
            item.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", item)
        ):
            raise ValueError(f"{location} must not contain an absolute local path")

    reject_absolute_paths(plain, name)
    return plain


def _required_source(value: Mapping[str, object]) -> dict[str, object]:
    source = _plain_mapping(value, name="source")
    expected = {
        "phase_source_id",
        "phase_source_sha256",
        "phase_source_uri",
        "structural_citation",
        "kinematical_recipe_id",
        "master_product_id",
        "energy_kev",
    }
    if set(source) != expected:
        raise ValueError("source fields differ from the Ice Ih candidate dictionary contract")
    for name in expected - {"energy_kev", "phase_source_sha256"}:
        if not isinstance(source[name], str) or not source[name].strip():
            raise ValueError(f"source.{name} must be non-empty text")
    if not isinstance(source["phase_source_sha256"], str) or not _SHA256.fullmatch(
        source["phase_source_sha256"]
    ):
        raise ValueError("source.phase_source_sha256 must be a lower-case SHA-256 digest")
    energy = source["energy_kev"]
    if isinstance(energy, bool) or not isinstance(energy, (int, float)) or float(energy) <= 0.0:
        raise ValueError("source.energy_kev must be positive")
    return source


def _file_inventory(root: Path) -> list[dict[str, object]]:
    roles = {
        "master/ice-ih-master-stereographic.npy": "spherical_signal",
        "cache/candidate-matrix.npy": "spherical_signal",
        "cache/directions.npy": "metadata",
        "cache/quaternions-wxyz.npy": "metadata",
        "entries.csv": "entries",
        "README.md": "documentation",
        "CITATION.cff": "documentation",
        "LICENSE": "documentation",
    }
    inventory: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in {"dictionary.manifest.json", "checksums.json"}:
            continue
        record: dict[str, object] = {
            "path": relative,
            "role": roles.get(
                relative, "validation" if relative.startswith("validation/") else "metadata"
            ),
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
            "format": {
                ".npy": "npy",
                ".csv": "csv",
                ".json": "json",
                ".md": "markdown",
                ".cff": "cff",
            }.get(path.suffix, "text"),
        }
        if path.suffix == ".npy":
            array = np.load(path, allow_pickle=False, mmap_mode="r")
            record["shape"] = list(array.shape)
            record["dtype"] = array.dtype.str
        inventory.append(record)
    return inventory


def _checksums(root: Path) -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "checksums.json":
            continue
        files[relative] = {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
    return {"schema_version": 1, "excludes": ["checksums.json"], "files": files}


def _write_entries(path: Path, quaternions: np.ndarray) -> None:
    rows = [
        "entry_index,entry_id,q_w,q_x,q_y,q_z,rotation_direction,quaternion_convention,frame_handedness"
    ]
    for index, quaternion in enumerate(quaternions):
        components = ",".join(format(float(value), ".17g") for value in quaternion)
        rows.append(
            f"{index},ICEIH-{index:05d},{components},crystal-to-sample,active-wxyz,right-handed"
        )
    _write_bytes(path, ("\n".join(rows) + "\n").encode("utf-8"))


def _write_readme(path: Path, *, dictionary_id: str) -> None:
    _write_bytes(
        path,
        (
            "# Ice Ih spherical candidate dictionary\n\n"
            f"Resource ID: `{dictionary_id}`.\n\n"
            "This resource supports fast spherical candidate search for Ice Ih's average "
            "oxygen sublattice in P 63/m m c (No. 194). It pairs a symmetry-reduced coarse "
            "SO(3) cache with the full canonical stereographic master for later local refinement.\n\n"
            "## Matching\n\n"
            "`cache/candidate-matrix.npy` contains row mean-centered, L2-normalized canonical "
            "signals. A caller must first produce an observed spherical signal on the exact "
            "published `cache/directions.npy` grid, then apply the same mean-center/L2 "
            "normalization and use normalized cosine similarity.\n\n"
            "## Boundaries\n\n"
            "This is a kinematical oxygen-sublattice resource, not a calibrated detector-pattern "
            "library or acquired-EBSD indexing benchmark. It excludes hydrogen disorder/order, "
            "Ice Ic and stacking disorder, amorphous ice, high-pressure ice polymorphs, and "
            "unnamed detector preprocessing.\n"
        ).encode("utf-8"),
    )


def _write_citation(path: Path, *, citation: str) -> None:
    escaped = citation.replace("\n", " ").replace('"', "'")
    _write_bytes(
        path,
        (
            "cff-version: 1.2.0\n"
            'title: "Ice Ih spherical candidate dictionary"\n'
            "type: dataset\n"
            "message: Cite the structural source and this generated dictionary resource.\n"
            "references:\n"
            f'  - type: article\n    title: "{escaped}"\n'
        ).encode("utf-8"),
    )


def _write_license(path: Path) -> None:
    _write_bytes(
        path,
        (
            "SPDX-License-Identifier: CC-BY-4.0\n\n"
            "This project-owned generated dictionary resource is distributed under CC BY 4.0.\n"
            "The structural-source citation and provenance are retained in the manifest.\n"
        ).encode("utf-8"),
    )


def _synthetic_recovery_configuration(
    value: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if value is None:
        return None
    configuration = _plain_mapping(value, name="synthetic_recovery")
    expected = {
        "held_out_rotation_vector_degrees",
        "local_half_width_degrees",
        "local_step_degrees",
    }
    if set(configuration) != expected:
        raise ValueError("synthetic_recovery fields differ from the Ice Ih dictionary contract")
    vector = np.asarray(configuration["held_out_rotation_vector_degrees"], dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)) or np.linalg.norm(vector) <= 0.0:
        raise ValueError("synthetic_recovery.held_out_rotation_vector_degrees must be non-zero")
    half_width = _positive_resolution(
        configuration["local_half_width_degrees"], name="synthetic recovery local half width"
    )
    step = _positive_resolution(
        configuration["local_step_degrees"], name="synthetic recovery local step"
    )
    if step > half_width:
        raise ValueError("synthetic recovery local step must not exceed local half width")
    return {
        "held_out_rotation_vector_degrees": [float(component) for component in vector],
        "local_half_width_degrees": half_width,
        "local_step_degrees": step,
    }


def _recovery_record(recovery: SyntheticRecovery) -> dict[str, object]:
    return {
        "reference_entry_index": recovery.reference_entry_index,
        "coarse_entry_index": recovery.coarse_entry_index,
        "coarse_score": recovery.coarse_score,
        "coarse_error_degrees": recovery.coarse_error_degrees,
        "refined_quaternion_wxyz": list(recovery.refined_quaternion_wxyz),
        "refined_score": recovery.refined_score,
        "refined_error_degrees": recovery.refined_error_degrees,
        "local_entry_count": recovery.local_entry_count,
        "held_out_quaternion_wxyz": list(recovery.held_out_quaternion_wxyz),
    }


def _write_validation(
    root: Path,
    candidate_matrix: np.ndarray,
    *,
    master: np.ndarray,
    quaternions: np.ndarray,
    directions: np.ndarray,
    synthetic_recovery: Mapping[str, object] | None,
) -> dict[str, object]:
    if synthetic_recovery is None:
        observed_fixture = "validation/observed-cache-entry-000000.npy"
        expected_results = "validation/expected-ranking.json"
        _write_npy(root / observed_fixture, candidate_matrix[0])
        _write_json(
            root / expected_results,
            {
                "schema_version": 1,
                "observed_signal": observed_fixture,
                "score_metric": "normalized-cosine",
                "expected_top_entry_index": 0,
            },
        )
        return {
            "observed_fixture": observed_fixture,
            "expected_results": expected_results,
            "kind": "deterministic cache integrity ranking",
        }

    recovery = run_synthetic_recovery(
        master,
        quaternions,
        directions,
        candidate_matrix,
        held_out_rotation_vector_degrees=synthetic_recovery["held_out_rotation_vector_degrees"],
        local_half_width_degrees=float(synthetic_recovery["local_half_width_degrees"]),
        local_step_degrees=float(synthetic_recovery["local_step_degrees"]),
    )
    observed_fixture = "validation/observed-held-out-spherical-signal.npy"
    expected_results = "validation/expected-recovery.json"
    observed = build_candidate_matrix(
        master,
        np.asarray((recovery.held_out_quaternion_wxyz,), dtype=np.float64),
        directions,
    )[0]
    _write_npy(root / observed_fixture, observed)
    _write_json(
        root / expected_results,
        {
            "schema_version": 1,
            "observed_signal": observed_fixture,
            "score_metric": "normalized-cosine",
            "expected_top_entry_index": recovery.coarse_entry_index,
            "configuration": synthetic_recovery,
            "recovery": _recovery_record(recovery),
        },
    )
    return {
        "observed_fixture": observed_fixture,
        "expected_results": expected_results,
        "kind": "held-out synthetic coarse-to-refined recovery",
        "synthetic_recovery": synthetic_recovery,
    }


def publish_ice_ih_candidate_dictionary(
    *,
    output_root: str | Path,
    master: object,
    master_array_sha256: str,
    source: Mapping[str, object],
    recipe: Mapping[str, object],
    dictionary_version: str,
    created_at: str,
    authors: Sequence[str],
    orientation_resolution_degrees: float = 5.0,
    direction_resolution_degrees: float = 5.0,
    synthetic_recovery: Mapping[str, object] | None = None,
) -> IceIhCandidateDictionaryResult:
    """Publish an atomic, verifier-ready Ice Ih spherical candidate package."""
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError(f"dictionary output already exists: {root}")
    if not _SHA256.fullmatch(master_array_sha256):
        raise ValueError("master_array_sha256 must be a lower-case SHA-256 digest")
    if not _SEMVER.fullmatch(dictionary_version):
        raise ValueError("dictionary_version must use a semantic-version-like form")
    if not _UTC.fullmatch(created_at):
        raise ValueError("created_at must be an ISO-8601 UTC timestamp with a Z suffix")
    parsed_source = _required_source(source)
    parsed_recipe = _plain_mapping(recipe, name="recipe")
    parsed_synthetic_recovery = _synthetic_recovery_configuration(synthetic_recovery)
    parsed_master = _master(master)
    actual_master_array_sha256 = _sha256_bytes(
        np.ascontiguousarray(parsed_master, dtype=np.float32).tobytes()
    )
    if actual_master_array_sha256 != master_array_sha256:
        raise ValueError("master array bytes differ from master_array_sha256")
    parsed_authors = tuple(author.strip() for author in authors)
    if not parsed_authors or any(not author for author in parsed_authors):
        raise ValueError("authors must contain one or more non-empty names or organizations")

    orientation_resolution = _positive_resolution(
        orientation_resolution_degrees, name="orientation resolution"
    )
    direction_resolution = _positive_resolution(
        direction_resolution_degrees, name="direction resolution"
    )
    quaternions = ice_ih_so3_orientations(orientation_resolution)
    directions = ice_ih_s2_directions(direction_resolution)
    if len(np.unique(np.round(quaternions, decimals=12), axis=0)) != len(quaternions):
        raise ValueError("orientation sampler emitted duplicate canonical quaternions")
    candidate_matrix = build_candidate_matrix(parsed_master, quaternions, directions)
    dictionary_id = stable_id(
        "ice-ih-spherical-dictionary",
        {
            "dictionary_version": dictionary_version,
            "master_array_sha256": master_array_sha256,
            "phase_source_sha256": parsed_source["phase_source_sha256"],
            "recipe": parsed_recipe,
            "orientation_resolution_degrees": orientation_resolution,
            "direction_resolution_degrees": direction_resolution,
            "quaternions_sha256": _sha256_bytes(quaternions.tobytes()),
            "directions_sha256": _sha256_bytes(directions.tobytes()),
            "synthetic_recovery": parsed_synthetic_recovery,
        },
    )
    staging = root.parent / f".{root.name}.{uuid4().hex}.partial"
    if staging.exists():
        raise FileExistsError(f"dictionary staging path already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        _write_npy(
            staging / "master/ice-ih-master-stereographic.npy", parsed_master.astype(np.float32)
        )
        _write_npy(staging / "cache/candidate-matrix.npy", candidate_matrix)
        _write_npy(staging / "cache/directions.npy", directions)
        _write_npy(staging / "cache/quaternions-wxyz.npy", quaternions)
        _write_entries(staging / "entries.csv", quaternions)
        validation = _write_validation(
            staging,
            candidate_matrix,
            master=parsed_master,
            quaternions=quaternions,
            directions=directions,
            synthetic_recovery=parsed_synthetic_recovery,
        )
        _write_readme(staging / "README.md", dictionary_id=dictionary_id)
        _write_citation(
            staging / "CITATION.cff", citation=str(parsed_source["structural_citation"])
        )
        _write_license(staging / "LICENSE")

        manifest: dict[str, object] = {
            "schema_name": "ebsd-pattern-dictionary",
            "schema_version": "0.1.0",
            "contract": "spherical-dictionary-resource/v1",
            "dictionary_id": dictionary_id,
            "dictionary_version": dictionary_version,
            "representation_kind": "spherical",
            "created_at": created_at,
            "authors": list(parsed_authors),
            "license": "CC-BY-4.0",
            "citation": {
                "preferred_citation": (
                    f"Kikuchi Atlas Ice Ih spherical candidate dictionary v{dictionary_version}"
                ),
                "structural_source": parsed_source["structural_citation"],
                "cff_path": "CITATION.cff",
            },
            "repository": "https://github.com/zmichels/kikuchi-atlas",
            "intended_use": ["candidate_search", "post_acquisition_reindexing"],
            "not_validated_for": [
                "detector-calibrated EBSD indexing accuracy",
                "unnamed detector geometry or preprocessing",
                "hydrogen-resolved Ice Ih structure",
                "Ice Ic, stacking-disordered, amorphous, or high-pressure ice",
            ],
            "phase": {
                "phase_id": "ice-ih-average-oxygen-sublattice",
                "phase_name": "Ice Ih average oxygen sublattice",
                "formula": "O",
                "crystal_system": "hexagonal",
                "point_group": "6/mmm",
                "space_group": {"number": 194, "setting": "P 63/m m c"},
                "lattice_parameters": {
                    "a": 4.3815,
                    "b": 4.3815,
                    "c": 7.183,
                    "alpha": 90.0,
                    "beta": 90.0,
                    "gamma": 120.0,
                    "unit": "angstrom and degrees",
                },
                "symmetry_operators": {
                    "reference": "International Tables setting P 63/m m c (No. 194)",
                    "point_group": "6/mmm",
                },
                "reference_frame": "right-handed crystal Cartesian frame",
                "setting_notes": "Average oxygen sublattice only; disordered hydrogen sites omitted.",
            },
            "source": {
                **parsed_source,
                "master_array_sha256": master_array_sha256,
                "master_path": "master/ice-ih-master-stereographic.npy",
            },
            "recipe": parsed_recipe,
            "orientation_convention": {
                "orientation_representation": "unit_quaternion",
                "quaternion_order": "wxyz",
                "quaternion_sign_rule": "w >= 0",
                "rotation_direction": "crystal-to-sample",
                "rotation_convention": "active right-handed",
                "sampling_domain": "6/mmm fundamental region",
                "sampling_method": "orix cubochoric",
                "nominal_angular_spacing_degrees": orientation_resolution,
                "entry_count": int(len(quaternions)),
                "coverage_validation": {
                    "fundamental_region": "orix D6h cubochoric sampler",
                    "unit_norm_checked": True,
                    "canonical_scalar_rule_checked": "w >= 0",
                    "duplicate_check": "unique after rounding wxyz to 12 decimal places",
                    "unique_entry_count": int(len(quaternions)),
                },
            },
            "entries": {"path": "entries.csv", "count": int(len(quaternions))},
            "representation": {
                "kind": "spherical",
                "canonical_master": "master/ice-ih-master-stereographic.npy",
                "canonical_master_frame": "crystal",
                "sphere_parameterization": "two-hemisphere unit stereographic disk",
                "sphere_frame": "sample",
                "sphere_handedness": "right-handed",
                "hemisphere_or_full_sphere": "full sphere",
                "sphere_axis_labels": ["sample_x", "sample_y", "sample_z"],
                "angular_units": "degrees",
                "sampling_resolution": {
                    "direction_grid": "orix spherified_cube_edge",
                    "direction_frame": "sample",
                    "nominal_spacing_degrees": direction_resolution,
                    "direction_count": int(len(directions)),
                },
                "antipodal_assumption": "none; upper and lower master hemispheres are distinct",
                "interpolation_method": "bilinear; upper owns equator",
            },
            "generation": {
                "generation_method": "kinematical master sampling into a spherical candidate cache",
                "software_name": "Kikuchi Atlas dictionary builder",
                "software_version": "local source-controlled implementation",
                "source_code_commit": "recorded by the consumer release, not inferred at build time",
                "accelerating_voltage_kv": parsed_source["energy_kev"],
                "master_pattern_source": parsed_source["master_product_id"],
                "postprocessing_steps": [
                    "raw master bilinear sampling",
                    "per-row mean centering",
                    "per-row L2 normalization",
                ],
            },
            "candidate_cache": {
                "path": "cache/candidate-matrix.npy",
                "directions_path": "cache/directions.npy",
                "quaternions_path": "cache/quaternions-wxyz.npy",
                "direction_frame": "sample",
                "direction_sampling_method": "orix spherified_cube_edge",
                "nominal_direction_spacing_degrees": direction_resolution,
                "score_metric": "normalized-cosine",
                "preprocessing": "raw master bilinear sample; per-row mean-center; per-row L2 normalize",
                "shape": [int(candidate_matrix.shape[0]), int(candidate_matrix.shape[1])],
                "dtype": candidate_matrix.dtype.str,
                "directions_sha256": _sha256_bytes(directions.tobytes()),
                "quaternions_sha256": _sha256_bytes(quaternions.tobytes()),
            },
            "refinement": {
                "source": "canonical-master-stereographic",
                "status": "coarse-cache foundation; local refinement recipe follows",
            },
            "matching_compatibility": {
                "observed_input": "sample-frame spherical signal on exact cache directions",
                "accepted_observed_signal_dtypes": ["float32", "float64"],
                "detector_pattern_input": "not accepted directly; explicit adapter required",
                "observed_preprocessing": "mean-center and L2-normalize",
                "required_preprocessing": {
                    "mask": "none in canonical comparison; adapter mask must be explicit",
                    "background": "not defined by this resource",
                    "saturation": "not defined by this resource",
                    "normalization": "mean-center and L2-normalize after exact S2 sampling",
                },
                "supported_metrics": ["normalized-cosine"],
                "phase_candidates": ["ice-ih-average-oxygen-sublattice"],
                "multi_phase_matching": False,
                "expected_output": "ranked candidate entry ids with normalized-cosine scores",
                "detector_adapter": "not included; detector geometry and preprocessing must be explicit",
                "required_runtime_geometry": [
                    "projection_model",
                    "pattern_center_convention",
                    "pcx",
                    "pcy",
                    "pcz",
                    "sample_tilt_degrees",
                    "camera_tilt_degrees",
                    "beam_direction",
                    "detector_normal",
                    "detector_pixel_origin",
                    "sample_frame_convention",
                ],
            },
            "validation": validation,
            "claim_boundary": {
                "experimental_ebsd_validated": False,
                "detector_calibrated": False,
                "excluded_materials": [
                    "hydrogen-ordered or hydrogen-disorder-resolved Ice Ih",
                    "Ice Ic and stacking-disordered ice",
                    "amorphous ice",
                    "high-pressure ice polymorphs",
                ],
            },
            "files": _file_inventory(staging),
        }
        manifest_without_hash = dict(manifest)
        manifest["manifest_sha256"] = _sha256_bytes(
            canonical_json(manifest_without_hash).encode("utf-8")
        )
        _write_json(staging / "dictionary.manifest.json", manifest)
        _write_json(staging / "checksums.json", _checksums(staging))
        _fsync_tree(staging)
        os.replace(staging, root)
        parent_descriptor = os.open(root.parent, os.O_RDONLY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except Exception:
        # Preserve partial evidence for diagnosis; callers may choose recovery explicitly.
        raise
    return IceIhCandidateDictionaryResult(
        dictionary_id=dictionary_id,
        path=root,
        manifest_sha256=str(manifest["manifest_sha256"]),
    )


def _package_path(root: Path, relative_path: object, *, name: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError(f"{name} must be non-empty text")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{name} must be a portable package-relative path")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{name} escapes the dictionary package")
    return resolved


def _read_entries(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        "entry_index",
        "entry_id",
        "q_w",
        "q_x",
        "q_y",
        "q_z",
        "rotation_direction",
        "quaternion_convention",
        "frame_handedness",
    }
    if not rows or set(rows[0]) != expected:
        raise ValueError("entries.csv fields differ from the Ice Ih candidate dictionary schema")
    quaternions: list[tuple[float, float, float, float]] = []
    for index, row in enumerate(rows):
        if row["entry_index"] != str(index) or row["entry_id"] != f"ICEIH-{index:05d}":
            raise ValueError("entries.csv identity sequence differs from the cache contract")
        if (
            row["rotation_direction"] != "crystal-to-sample"
            or row["quaternion_convention"] != "active-wxyz"
            or row["frame_handedness"] != "right-handed"
        ):
            raise ValueError("entries.csv orientation convention differs from the cache contract")
        try:
            quaternions.append(tuple(float(row[f"q_{axis}"]) for axis in "wxyz"))
        except (TypeError, ValueError) as error:
            raise ValueError("entries.csv quaternion values must be finite numbers") from error
    return _unit_quaternions_wxyz(np.asarray(quaternions, dtype=np.float64))


def verify_ice_ih_candidate_dictionary(
    path: str | Path,
) -> IceIhCandidateDictionaryVerification:
    """Verify package bytes, conventions, normalized rows, and ranking fixture."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"dictionary package directory does not exist: {root}")
    try:
        manifest = json.loads((root / "dictionary.manifest.json").read_text(encoding="utf-8"))
        checksums = json.loads((root / "checksums.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dictionary manifest or checksums file is unreadable") from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_name") != "ebsd-pattern-dictionary"
        or manifest.get("schema_version") != "0.1.0"
        or manifest.get("representation_kind") != "spherical"
    ):
        raise ValueError("dictionary manifest does not declare the supported spherical contract")
    recorded_manifest_hash = manifest.get("manifest_sha256")
    manifest_without_hash = dict(manifest)
    manifest_without_hash.pop("manifest_sha256", None)
    if not isinstance(recorded_manifest_hash, str) or recorded_manifest_hash != _sha256_bytes(
        canonical_json(manifest_without_hash).encode("utf-8")
    ):
        raise ValueError("dictionary manifest_sha256 differs from canonical manifest content")
    dictionary_id = manifest.get("dictionary_id")
    if not isinstance(dictionary_id, str) or not dictionary_id.startswith(
        "ice-ih-spherical-dictionary-"
    ):
        raise ValueError("dictionary manifest has an invalid Ice Ih dictionary_id")

    if not isinstance(checksums, dict) or checksums.get("excludes") != ["checksums.json"]:
        raise ValueError("checksums.json has an unsupported exclusion policy")
    records = checksums.get("files")
    if not isinstance(records, dict) or not records:
        raise ValueError("checksums.json must contain a non-empty files mapping")
    expected_paths: set[str] = set()
    for relative_path, record in records.items():
        artifact = _package_path(root, relative_path, name="checksums.files path")
        if not isinstance(record, dict) or artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f"checksum artifact is not a regular file: {relative_path}")
        if record.get("bytes") != artifact.stat().st_size or record.get("sha256") != _sha256_file(
            artifact
        ):
            raise ValueError(f"checksum mismatch for {relative_path}")
        expected_paths.add(relative_path)
    actual_paths = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file() and not item.is_symlink() and item.name != "checksums.json"
    }
    if actual_paths != expected_paths:
        raise ValueError("checksums.json does not inventory the exact package file set")

    inventory = manifest.get("files")
    if not isinstance(inventory, list):
        raise ValueError("dictionary manifest must contain a file inventory")
    inventory_paths = {record.get("path") for record in inventory if isinstance(record, dict)}
    if inventory_paths != expected_paths - {"dictionary.manifest.json"}:
        raise ValueError("dictionary manifest file inventory differs from checksums.json")

    source = manifest.get("source")
    cache_info = manifest.get("candidate_cache")
    entries_info = manifest.get("entries")
    validation = manifest.get("validation")
    if not all(isinstance(value, dict) for value in (source, cache_info, entries_info, validation)):
        raise ValueError("dictionary manifest lacks required Ice Ih resource sections")
    master_path = _package_path(root, source.get("master_path"), name="source.master_path")
    master = _master(np.load(master_path, allow_pickle=False, mmap_mode="r"))
    if source.get("master_array_sha256") != _sha256_bytes(master.astype(np.float32).tobytes()):
        raise ValueError("canonical master bytes differ from source.master_array_sha256")
    directions = _unit_vectors(
        np.load(
            _package_path(root, cache_info.get("directions_path"), name="cache directions"),
            allow_pickle=False,
            mmap_mode="r",
        ),
        name="cache directions",
    )
    quaternions = _unit_quaternions_wxyz(
        np.load(
            _package_path(root, cache_info.get("quaternions_path"), name="cache quaternions"),
            allow_pickle=False,
            mmap_mode="r",
        )
    )
    candidate_matrix = np.asarray(
        np.load(
            _package_path(root, cache_info.get("path"), name="candidate cache"),
            allow_pickle=False,
            mmap_mode="r",
        ),
        dtype=np.float32,
    )
    if candidate_matrix.shape != (len(quaternions), len(directions)):
        raise ValueError("candidate cache shape differs from directions or orientation entries")
    if cache_info.get("shape") != list(candidate_matrix.shape):
        raise ValueError("manifest candidate cache shape differs from payload")
    if cache_info.get("directions_sha256") != _sha256_bytes(directions.tobytes()):
        raise ValueError("cache direction hash differs from manifest")
    if cache_info.get("quaternions_sha256") != _sha256_bytes(quaternions.tobytes()):
        raise ValueError("cache quaternion hash differs from manifest")
    entries = _read_entries(_package_path(root, entries_info.get("path"), name="entries path"))
    if entries_info.get("count") != len(entries) or not np.array_equal(entries, quaternions):
        raise ValueError("entries.csv differs from cache quaternions")

    observed_path = _package_path(
        root, validation.get("observed_fixture"), name="validation fixture"
    )
    observed = np.load(observed_path, allow_pickle=False)
    expected_path = _package_path(
        root, validation.get("expected_results"), name="validation results"
    )
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("expected validation result is unreadable") from error
    if not isinstance(expected, dict) or expected.get("schema_version") != 1:
        raise ValueError("expected validation result has an unsupported schema")
    if expected.get("observed_signal") != validation.get("observed_fixture"):
        raise ValueError("expected validation result differs from manifest fixture path")
    if expected.get("score_metric") != "normalized-cosine":
        raise ValueError("expected validation result lacks the declared score metric")
    expected_top = expected.get("expected_top_entry_index")
    if not isinstance(expected_top, int):
        raise ValueError("expected validation result lacks an integer top entry index")
    ranking = rank_candidate_matrix(candidate_matrix, observed, top_k=1)
    if ranking[0].entry_index != expected_top:
        raise ValueError("expected validation ranking differs from recomputed cache ranking")
    validation_kind = validation.get("kind")
    if validation_kind == "deterministic cache integrity ranking":
        if expected_top != 0 or not np.array_equal(observed, candidate_matrix[0]):
            raise ValueError("deterministic cache validation fixture differs from entry zero")
    elif validation_kind == "held-out synthetic coarse-to-refined recovery":
        configuration = expected.get("configuration")
        if not isinstance(configuration, dict):
            raise ValueError("held-out recovery validation lacks a configuration")
        parsed_configuration = _synthetic_recovery_configuration(configuration)
        if (
            parsed_configuration is None
            or validation.get("synthetic_recovery") != parsed_configuration
        ):
            raise ValueError("held-out recovery configuration differs from the manifest")
        recovery = run_synthetic_recovery(
            master,
            quaternions,
            directions,
            candidate_matrix,
            held_out_rotation_vector_degrees=parsed_configuration[
                "held_out_rotation_vector_degrees"
            ],
            local_half_width_degrees=float(parsed_configuration["local_half_width_degrees"]),
            local_step_degrees=float(parsed_configuration["local_step_degrees"]),
        )
        recomputed_observed = build_candidate_matrix(
            master,
            np.asarray((recovery.held_out_quaternion_wxyz,), dtype=np.float64),
            directions,
        )[0]
        if not np.allclose(observed, recomputed_observed, rtol=0.0, atol=2e-6):
            raise ValueError("held-out recovery fixture differs from its declared orientation")
        recorded_recovery = expected.get("recovery")
        if not isinstance(recorded_recovery, dict):
            raise ValueError("held-out recovery validation lacks diagnostics")
        recomputed_recovery = _recovery_record(recovery)
        integer_fields = {
            "reference_entry_index",
            "coarse_entry_index",
            "local_entry_count",
        }
        scalar_fields = {
            "coarse_score",
            "coarse_error_degrees",
            "refined_score",
            "refined_error_degrees",
        }
        vector_fields = {"refined_quaternion_wxyz", "held_out_quaternion_wxyz"}
        expected_fields = integer_fields | scalar_fields | vector_fields
        if set(recorded_recovery) != expected_fields:
            raise ValueError("held-out recovery diagnostics differ from the package contract")
        for field in integer_fields:
            if recorded_recovery[field] != recomputed_recovery[field]:
                raise ValueError(f"held-out recovery integer diagnostic differs: {field}")
        for field in scalar_fields:
            if not np.isclose(recorded_recovery[field], recomputed_recovery[field], atol=2e-8):
                raise ValueError(f"held-out recovery scalar diagnostic differs: {field}")
        for field in vector_fields:
            if not np.allclose(
                recorded_recovery[field], recomputed_recovery[field], rtol=0.0, atol=2e-8
            ):
                raise ValueError(f"held-out recovery orientation diagnostic differs: {field}")
        if recovery.coarse_entry_index != expected_top:
            raise ValueError("held-out recovery coarse result differs from ranking fixture")
        if recovery.refined_error_degrees >= recovery.coarse_error_degrees:
            raise ValueError("held-out recovery does not improve its angular diagnostic")
    else:
        raise ValueError("dictionary manifest declares an unsupported validation kind")
    return IceIhCandidateDictionaryVerification(
        dictionary_id=dictionary_id,
        path=root,
        entry_count=len(entries),
        expected_top_entry_index=expected_top,
    )


__all__ = [
    "CandidateMatch",
    "CandidateRefinement",
    "IceIhCandidateDictionaryResult",
    "IceIhCandidateDictionaryVerification",
    "build_candidate_matrix",
    "compose_quaternions_wxyz",
    "ice_ih_s2_directions",
    "ice_ih_so3_orientations",
    "local_refine_candidate",
    "publish_ice_ih_candidate_dictionary",
    "quaternion_rotation_matrices",
    "quaternion_from_rotation_vectors_degrees",
    "quaternion_misorientation_degrees",
    "rank_candidate_matrix",
    "run_synthetic_recovery",
    "sample_stereographic_master",
    "SyntheticRecovery",
    "verify_ice_ih_candidate_dictionary",
]
