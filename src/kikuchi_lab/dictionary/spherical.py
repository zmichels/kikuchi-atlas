"""A small, portable S2 dictionary resource with explicit conventions.

This module deliberately publishes a coarse interoperability fixture rather
than a calibrated detector-pattern dictionary. It turns a cited canonical S2
signal into three exact quarter-turn patterns on a cube-shell lattice. The
limited lattice lets the fixture prove orientation and package semantics
without silently choosing an interpolation or detector model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import csv
from itertools import product
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
from uuid import uuid4
import zipfile

import numpy as np

from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id


_ENTRY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXACT_DIRECTION_TOLERANCE = 2.0e-12


@dataclass(frozen=True)
class OrientationEntry:
    """One active, right-handed crystal-to-sample quaternion orientation."""

    entry_id: str
    quaternion_wxyz: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if not _ENTRY_ID.fullmatch(self.entry_id):
            raise ValueError("orientation entry_id must be a safe portable identifier")
        quaternion = np.asarray(self.quaternion_wxyz, dtype=np.float64)
        if quaternion.shape != (4,) or not np.all(np.isfinite(quaternion)):
            raise ValueError("quaternion_wxyz must contain four finite values")
        norm = float(np.linalg.norm(quaternion))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5e-13):
            raise ValueError("quaternion_wxyz must be normalized")
        if quaternion[0] < 0.0:
            raise ValueError("quaternion_wxyz must use a non-negative scalar component")
        object.__setattr__(self, "quaternion_wxyz", tuple(float(value) for value in quaternion))

    def to_dict(self) -> dict[str, object]:
        return {"entry_id": self.entry_id, "quaternion_wxyz": list(self.quaternion_wxyz)}


@dataclass(frozen=True)
class DictionaryMatch:
    """A deterministic score for one explicit dictionary entry."""

    entry_id: str
    score: float
    root_mean_square_error: float


@dataclass(frozen=True)
class SphericalDictionaryResult:
    """Identity and location of one immutable published dictionary resource."""

    dictionary_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class SphericalDictionaryVerification:
    """Result of rechecking one portable spherical dictionary resource."""

    dictionary_id: str
    path: Path
    file_count: int
    expected_top_entry_id: str


def cube_shell_directions() -> np.ndarray:
    """Return the fixed 26-node normalized {-1, 0, +1} cube-shell lattice."""
    integer_nodes = np.asarray(
        [node for node in product((-1.0, 0.0, 1.0), repeat=3) if node != (0.0, 0.0, 0.0)],
        dtype=np.float64,
    )
    norms = np.linalg.norm(integer_nodes, axis=1, keepdims=True)
    return np.ascontiguousarray(integer_nodes / norms, dtype=np.float64)


def quaternion_rotation_matrix(entry: OrientationEntry) -> np.ndarray:
    """Return the active crystal-to-sample rotation matrix for ``entry``."""
    w, x, y, z = entry.quaternion_wxyz
    matrix = np.asarray(
        (
            (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
            (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
            (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
        ),
        dtype=np.float64,
    )
    if not np.allclose(matrix.T @ matrix, np.eye(3), rtol=0.0, atol=5e-13):
        raise ValueError("quaternion rotation is not orthonormal")
    if not math.isclose(float(np.linalg.det(matrix)), 1.0, rel_tol=0.0, abs_tol=5e-13):
        raise ValueError("quaternion rotation must be right-handed")
    return matrix


def _directions(value: np.ndarray, name: str) -> np.ndarray:
    directions = np.asarray(value, dtype=np.float64)
    if directions.ndim != 2 or directions.shape[1] != 3 or len(directions) == 0:
        raise ValueError(f"{name} must be a non-empty (N, 3) array")
    if not np.all(np.isfinite(directions)):
        raise ValueError(f"{name} must contain only finite values")
    norms = np.linalg.norm(directions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=5e-13):
        raise ValueError(f"{name} must contain unit vectors")
    return np.ascontiguousarray(directions, dtype=np.float64)


def _signal(value: np.ndarray, count: int, name: str) -> np.ndarray:
    signal = np.asarray(value, dtype=np.float64)
    if signal.shape != (count,) or not np.all(np.isfinite(signal)):
        raise ValueError(f"{name} must be a finite one-dimensional array matching directions")
    return np.ascontiguousarray(signal, dtype=np.float64)


def _unique_entries(entries: Sequence[OrientationEntry]) -> tuple[OrientationEntry, ...]:
    result = tuple(entries)
    if not result:
        raise ValueError("dictionary must include at least one orientation entry")
    if len({entry.entry_id for entry in result}) != len(result):
        raise ValueError("dictionary orientation entry identifiers must be unique")
    return result


def _lookup_indices(canonical_directions: np.ndarray, query_directions: np.ndarray) -> np.ndarray:
    dot_products = query_directions @ canonical_directions.T
    indices = np.argmax(dot_products, axis=1)
    errors = np.linalg.norm(canonical_directions[indices] - query_directions, axis=1)
    worst_error = float(np.max(errors))
    if worst_error > _EXACT_DIRECTION_TOLERANCE:
        raise ValueError(
            "orientation leaves the fixture's exact cube-shell lattice; "
            "this resource intentionally defines no interpolation"
        )
    return indices.astype(np.int64, copy=False)


def rotate_canonical_signal_to_sample(
    canonical_directions: np.ndarray,
    canonical_signal: np.ndarray,
    entry: OrientationEntry,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate ``I_sample(s) = I_crystal(R_cs^-1 s)`` on the fixture lattice."""
    directions = _directions(canonical_directions, "canonical_directions")
    signal = _signal(canonical_signal, len(directions), "canonical_signal")
    rotation = quaternion_rotation_matrix(entry)
    crystal_directions = directions @ rotation
    indices = _lookup_indices(directions, crystal_directions)
    return directions.copy(), signal[indices].copy()


def rank_spherical_dictionary(
    *,
    canonical_directions: np.ndarray,
    canonical_signal: np.ndarray,
    entries: Sequence[OrientationEntry],
    sample_directions: np.ndarray,
    observed_signal: np.ndarray,
) -> tuple[DictionaryMatch, ...]:
    """Rank supplied-entry exact patterns against an observed fixture pattern.

    The score is ``1 - MSE / observed_range**2``. It is a compact fixture
    diagnostic, not a recommended experimental EBSD similarity metric.
    """
    directions = _directions(canonical_directions, "canonical_directions")
    signal = _signal(canonical_signal, len(directions), "canonical_signal")
    samples = _directions(sample_directions, "sample_directions")
    observed = _signal(observed_signal, len(samples), "observed_signal")
    if len(samples) != len(directions):
        raise ValueError("fixture observed directions must match canonical direction count")
    parsed_entries = _unique_entries(entries)
    observed_range = max(float(np.ptp(observed)), np.finfo(np.float64).eps)
    matches: list[DictionaryMatch] = []
    for entry in parsed_entries:
        rotation = quaternion_rotation_matrix(entry)
        crystal_directions = samples @ rotation
        predicted = signal[_lookup_indices(directions, crystal_directions)]
        residual = predicted - observed
        rmse = float(np.sqrt(np.mean(residual * residual)))
        score = float(1.0 - np.mean(residual * residual) / (observed_range * observed_range))
        matches.append(DictionaryMatch(entry.entry_id, score, rmse))
    return tuple(sorted(matches, key=lambda match: (-match.score, match.entry_id)))


def downsample_to_cube_shell(
    source_directions: np.ndarray,
    source_signal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Nearest-direction downsample of an S2 source field to the 26-node lattice."""
    source_xyz = _directions(source_directions, "source_directions")
    source_values = _signal(source_signal, len(source_xyz), "source_signal")
    target = cube_shell_directions()
    indices = np.argmax(target @ source_xyz.T, axis=1)
    selected = source_xyz[indices]
    angular_error = np.arccos(np.clip(np.sum(target * selected, axis=1), -1.0, 1.0))
    return target, source_values[indices].copy(), float(np.degrees(np.max(angular_error)))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    return _sha256_bytes(np.ascontiguousarray(value).tobytes(order="C"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_text(path: Path, value: str) -> None:
    _write_bytes(path, value.encode("utf-8"))


def _write_json(path: Path, value: object) -> None:
    _write_bytes(path, canonical_json(value).encode("utf-8"))


def _write_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    """Write timestamp-free NPZ bytes with explicit portable dtypes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with zipfile.ZipFile(handle, mode="w") as archive:
            for name in sorted(arrays):
                payload = io.BytesIO()
                np.lib.format.write_array(
                    payload,
                    np.ascontiguousarray(arrays[name]),
                    allow_pickle=False,
                )
                info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue())
        handle.flush()
        os.fsync(handle.fileno())


def _write_entries(path: Path, entries: Sequence[OrientationEntry]) -> None:
    lines = [
        "entry_id,q_w,q_x,q_y,q_z,rotation_direction,quaternion_convention,frame_handedness"
    ]
    for entry in entries:
        quaternion = ",".join(format(value, ".17g") for value in entry.quaternion_wxyz)
        lines.append(
            f"{entry.entry_id},{quaternion},crystal-to-sample,active-wxyz,right-handed"
        )
    _write_text(path, "\n".join(lines) + "\n")


def _safe_plain_mapping(value: Mapping[str, object], name: str) -> dict[str, object]:
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        _fsync_directory(path)
    _fsync_directory(root)


def _write_readme(
    path: Path,
    *,
    dictionary_id: str,
    dictionary_name: str,
    phase_name: str,
    validation_entry_id: str,
) -> None:
    _write_text(
        path,
        "\n".join(
            (
                f"# {dictionary_name}",
                "",
                f"Resource ID: `{dictionary_id}`.",
                "",
                "This is a deliberately coarse spherical-orientation dictionary fixture for "
                f"{phase_name}. It is an external resource shaped for the spherical "
                "dictionary contract, not an experimentally validated EBSD dictionary.",
                "",
                "## What is here",
                "",
                "- `spherical_signal.npz`: canonical crystal-frame S2 signal on 26 cube-shell nodes.",
                "- `entries.csv`: explicit active quaternions in w,x,y,z order, crystal to sample.",
                "- `patterns/`: one exact sample-frame pattern per supplied orientation entry.",
                "- `validation/`: an observed fixture and expected deterministic ranking.",
                "- `checksums.json`: SHA-256 and byte count for every package file except itself.",
                "",
                "## Convention",
                "",
                "For an active crystal-to-sample rotation R_cs, the pattern is evaluated as "
                "I_sample(s) = I_crystal(R_cs^-1 s). All vectors are right handed and "
                "dimensionless. This fixture deliberately supports exact lookup on its 26 "
                "directions only; it defines no interpolation, detector projection, background "
                "model, camera response, or experimental preprocessing.",
                "",
                "## Validation",
                "",
                f"The included observed pattern is generated from `{validation_entry_id}`. "
                "The expected ranking uses 1 - MSE / observed_range^2 and exists only as a "
                "portable convention-and-integrity test.",
                "",
            )
        ),
    )


def _write_citation(path: Path, *, dictionary_name: str, citation_text: str) -> None:
    escaped = citation_text.replace("\n", " ").replace('"', "'")
    _write_text(
        path,
        "\n".join(
            (
                "cff-version: 1.2.0",
                f'title: "{dictionary_name}"',
                "type: dataset",
                "message: Cite the structural source and this generated fixture when useful.",
                "references:",
                f'  - type: article\n    title: "{escaped}"',
                "",
            )
        ),
    )


def _write_license(path: Path, license_id: str) -> None:
    _write_text(
        path,
        "\n".join(
            (
                f"SPDX-License-Identifier: {license_id}",
                "",
                "This generated resource is distributed under the SPDX identifier above.",
                "Its source structural-data attribution is recorded in CITATION.cff and the",
                "dictionary manifest. Verify downstream license compatibility before reuse.",
                "",
            )
        ),
    )


def _checksums(root: Path) -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root).as_posix()
        if relative_path == "checksums.json":
            continue
        files[relative_path] = {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
    return {"schema_version": 1, "files": files, "excludes": ["checksums.json"]}


def _file_role(relative_path: str) -> str:
    if relative_path == "entries.csv":
        return "entries"
    if relative_path == "spherical_signal.npz":
        return "spherical_signal"
    if relative_path.startswith("patterns/"):
        return "patterns"
    if relative_path.startswith("validation/"):
        return "validation"
    return "documentation"


def _file_format(path: Path) -> str:
    return {
        ".npz": "npz",
        ".csv": "csv",
        ".json": "json",
        ".md": "markdown",
        ".cff": "cff",
    }.get(path.suffix, "text")


def _file_inventory(root: Path) -> list[dict[str, object]]:
    """Describe payload files that precede manifest/checksum self-references."""
    inventory: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root).as_posix()
        if relative_path in {"dictionary.manifest.json", "checksums.json"}:
            continue
        record: dict[str, object] = {
            "path": relative_path,
            "role": _file_role(relative_path),
            "format": _file_format(path),
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        if path.suffix == ".npz":
            with np.load(path, allow_pickle=False) as archive:
                record["arrays"] = {
                    name: {"shape": list(archive[name].shape), "dtype": archive[name].dtype.str}
                    for name in sorted(archive.files)
                }
            record["compression"] = "zip-deflate"
        inventory.append(record)
    return inventory


def _portable_package_path(root: Path, relative_path: object, name: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError(f"{name} must be non-empty text")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{name} must be a portable package-relative path")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{name} escapes the dictionary package")
    return resolved


def _read_entries(path: Path) -> tuple[OrientationEntry, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_columns = {
        "entry_id",
        "q_w",
        "q_x",
        "q_y",
        "q_z",
        "rotation_direction",
        "quaternion_convention",
        "frame_handedness",
    }
    if not rows or set(rows[0]) != expected_columns:
        raise ValueError("entries.csv fields differ from the spherical dictionary schema")
    entries: list[OrientationEntry] = []
    for row in rows:
        if (
            row["rotation_direction"] != "crystal-to-sample"
            or row["quaternion_convention"] != "active-wxyz"
            or row["frame_handedness"] != "right-handed"
        ):
            raise ValueError("entries.csv convention differs from the manifest contract")
        try:
            quaternion = tuple(float(row[name]) for name in ("q_w", "q_x", "q_y", "q_z"))
        except (TypeError, ValueError) as error:
            raise ValueError("entries.csv quaternion values must be finite numbers") from error
        entries.append(OrientationEntry(str(row["entry_id"]), quaternion))
    return _unique_entries(entries)


def _load_npz_pair(path: Path, direction_key: str) -> tuple[np.ndarray, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {direction_key, "intensity"}:
                raise ValueError(f"{path.name} arrays differ from the spherical dictionary schema")
            return archive[direction_key], archive["intensity"]
    except OSError as error:
        raise ValueError(f"cannot read {path.name} as an NPZ artifact") from error


def verify_spherical_dictionary(path: str | Path) -> SphericalDictionaryVerification:
    """Validate checksums, resource shape, and the included ranking fixture.

    This verifier intentionally validates only the portable fixture contract;
    it does not claim physical fidelity to experimental EBSD patterns.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"dictionary package directory does not exist: {root}")
    manifest_path = root / "dictionary.manifest.json"
    checksums_path = root / "checksums.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dictionary manifest or checksums file is unreadable") from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_name") != "ebsd-pattern-dictionary"
        or manifest.get("schema_version") != "0.1.0"
        or manifest.get("contract") != "spherical-dictionary-resource/v1"
        or manifest.get("representation_kind") != "spherical"
    ):
        raise ValueError("dictionary manifest does not declare the supported spherical contract")
    recorded_manifest_sha256 = manifest.get("manifest_sha256")
    manifest_without_hash = dict(manifest)
    manifest_without_hash.pop("manifest_sha256", None)
    if (
        not isinstance(recorded_manifest_sha256, str)
        or recorded_manifest_sha256 != _sha256_bytes(canonical_json(manifest_without_hash).encode("utf-8"))
    ):
        raise ValueError("dictionary manifest_sha256 differs from canonical manifest content")
    dictionary_id = manifest.get("dictionary_id")
    if not isinstance(dictionary_id, str) or not dictionary_id.startswith("spherical-dictionary-"):
        raise ValueError("dictionary manifest has an invalid dictionary_id")
    if not isinstance(checksums, dict) or checksums.get("excludes") != ["checksums.json"]:
        raise ValueError("checksums.json has an unsupported exclusion policy")
    file_records = checksums.get("files")
    if not isinstance(file_records, dict) or not file_records:
        raise ValueError("checksums.json must contain a non-empty files mapping")
    expected_paths: set[str] = set()
    for relative_path, record in file_records.items():
        artifact = _portable_package_path(root, relative_path, "checksums.files path")
        if not isinstance(record, dict):
            raise ValueError("checksums.json file record must be a mapping")
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f"checksum artifact is not a regular file: {relative_path}")
        actual_bytes = artifact.stat().st_size
        actual_sha256 = _sha256_file(artifact)
        if record.get("bytes") != actual_bytes or record.get("sha256") != actual_sha256:
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
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("dictionary manifest must contain a non-empty file inventory")
    inventory_by_path: dict[str, dict[str, object]] = {}
    for record in inventory:
        if not isinstance(record, dict):
            raise ValueError("dictionary manifest file inventory record must be a mapping")
        relative_path = record.get("path")
        if not isinstance(relative_path, str) or relative_path in inventory_by_path:
            raise ValueError("dictionary manifest file inventory paths must be unique text")
        _portable_package_path(root, relative_path, "manifest files path")
        inventory_by_path[relative_path] = record
    inventoried_paths = set(inventory_by_path)
    checksum_payload_paths = expected_paths - {"dictionary.manifest.json"}
    if inventoried_paths != checksum_payload_paths:
        raise ValueError("manifest file inventory differs from checksum payload inventory")
    for relative_path, record in inventory_by_path.items():
        checksum_record = file_records[relative_path]
        if (
            record.get("bytes") != checksum_record["bytes"]
            or record.get("sha256") != checksum_record["sha256"]
        ):
            raise ValueError("manifest file inventory hash differs from checksums.json")

    representation = manifest.get("representation")
    entries_info = manifest.get("entries")
    orientation = manifest.get("orientation_convention")
    validation = manifest.get("validation")
    if (
        not isinstance(representation, dict)
        or representation.get("kind") != "spherical"
        or not isinstance(entries_info, dict)
        or not isinstance(orientation, dict)
        or not isinstance(validation, dict)
    ):
        raise ValueError("dictionary manifest lacks required spherical resource sections")
    if orientation.get("rotation_direction") != "crystal-to-sample":
        raise ValueError("dictionary orientation direction must be crystal-to-sample")
    if orientation.get("quaternion_order") != "w,x,y,z":
        raise ValueError("dictionary quaternion order must be w,x,y,z")
    if orientation.get("frame_handedness") != "right-handed":
        raise ValueError("dictionary frame must be right-handed")

    signal_path = _portable_package_path(root, representation.get("canonical_signal"), "canonical signal")
    directions, signal = _load_npz_pair(signal_path, "directions")
    directions = _directions(directions, "canonical directions")
    signal = _signal(signal, len(directions), "canonical intensity")
    if representation.get("directions_sha256") != _array_sha256(directions):
        raise ValueError("canonical direction array hash differs from manifest")
    if representation.get("intensity_sha256") != _array_sha256(signal):
        raise ValueError("canonical intensity array hash differs from manifest")

    entries_path = _portable_package_path(root, entries_info.get("path"), "entries path")
    entries = _read_entries(entries_path)
    if entries_info.get("count") != len(entries):
        raise ValueError("manifest entry count differs from entries.csv")

    observed_path = _portable_package_path(root, validation.get("observed_fixture"), "validation fixture")
    sample_directions, observed_signal = _load_npz_pair(observed_path, "sample_directions")
    ranking = rank_spherical_dictionary(
        canonical_directions=directions,
        canonical_signal=signal,
        entries=entries,
        sample_directions=sample_directions,
        observed_signal=observed_signal,
    )
    expected_path = _portable_package_path(root, validation.get("expected_results"), "expected results")
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("expected validation result is unreadable") from error
    expected_ranking = expected.get("ranking") if isinstance(expected, dict) else None
    if not isinstance(expected_ranking, list) or len(expected_ranking) != len(ranking):
        raise ValueError("expected validation ranking differs from dictionary entries")
    for actual, recorded in zip(ranking, expected_ranking, strict=True):
        if not isinstance(recorded, dict) or recorded.get("entry_id") != actual.entry_id:
            raise ValueError("expected validation ranking entry differs from recomputed ranking")
        if not math.isclose(
            float(recorded.get("score")), actual.score, rel_tol=0.0, abs_tol=1e-14
        ):
            raise ValueError("expected validation score differs from recomputed ranking")
        if not math.isclose(
            float(recorded.get("root_mean_square_error")),
            actual.root_mean_square_error,
            rel_tol=0.0,
            abs_tol=1e-14,
        ):
            raise ValueError("expected validation RMSE differs from recomputed ranking")
    expected_top = validation.get("expected_top_entry_id")
    if expected_top != ranking[0].entry_id:
        raise ValueError("manifest expected top entry differs from recomputed ranking")
    return SphericalDictionaryVerification(
        dictionary_id=dictionary_id,
        path=root,
        file_count=len(file_records),
        expected_top_entry_id=ranking[0].entry_id,
    )


def publish_spherical_dictionary(
    *,
    output_root: str | Path,
    dictionary_name: str,
    phase: Mapping[str, object],
    source: Mapping[str, object],
    recipe: Mapping[str, object],
    canonical_directions: np.ndarray,
    canonical_signal: np.ndarray,
    entries: Sequence[OrientationEntry],
    validation_entry_id: str,
    license_id: str,
    citation_text: str,
    dictionary_version: str,
    created_at: str,
    authors: Sequence[str],
) -> SphericalDictionaryResult:
    """Publish one no-clobber spherical dictionary fixture atomically.

    The public API intentionally takes precomputed canonical values. A phase
    workflow is responsible for binding those values to a particular cited
    source field and recipe before calling this portable package layer.
    """
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError(f"dictionary output already exists: {root}")
    if not dictionary_name or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", dictionary_name):
        raise ValueError("dictionary_name must use lowercase ASCII words joined by hyphens")
    parsed_phase = _safe_plain_mapping(phase, "phase")
    required_phase = {"name", "formula", "space_group_number", "setting"}
    if not required_phase.issubset(parsed_phase):
        raise ValueError(f"phase must contain {sorted(required_phase)}")
    parsed_source = _safe_plain_mapping(source, "source")
    source_hash = parsed_source.get("source_file_sha256")
    if not isinstance(source_hash, str) or not _SHA256.fullmatch(source_hash):
        raise ValueError("source.source_file_sha256 must be a lower-case SHA-256 digest")
    parsed_recipe = _safe_plain_mapping(recipe, "recipe")
    directions = _directions(canonical_directions, "canonical_directions")
    signal = _signal(canonical_signal, len(directions), "canonical_signal")
    parsed_entries = _unique_entries(entries)
    if validation_entry_id not in {entry.entry_id for entry in parsed_entries}:
        raise ValueError("validation_entry_id must name one supplied orientation entry")
    if not license_id.strip() or not citation_text.strip():
        raise ValueError("license_id and citation_text must be non-empty")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", dictionary_version):
        raise ValueError("dictionary_version must use a semantic-version-like form")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_at):
        raise ValueError("created_at must be an ISO-8601 UTC timestamp with a Z suffix")
    parsed_authors = tuple(author.strip() for author in authors)
    if not parsed_authors or any(not author for author in parsed_authors):
        raise ValueError("authors must contain one or more non-empty names or organizations")

    canonical_hashes = {
        "directions_sha256": _array_sha256(directions),
        "intensity_sha256": _array_sha256(signal),
    }
    dictionary_id = stable_id(
        "spherical-dictionary",
        {
            "dictionary_name": dictionary_name,
            "phase": parsed_phase,
            "source": parsed_source,
            "recipe": parsed_recipe,
            "canonical_hashes": canonical_hashes,
            "entries": [entry.to_dict() for entry in parsed_entries],
        },
    )
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = root.parent / f".{root.name}.partial-{uuid4().hex}"
    if stage.exists():
        raise FileExistsError(f"dictionary staging path unexpectedly exists: {stage}")
    stage.mkdir()
    try:
        _write_npz(
            stage / "spherical_signal.npz",
            {
                "directions": np.asarray(directions, dtype="<f8"),
                "intensity": np.asarray(signal, dtype="<f8"),
            },
        )
        _write_entries(stage / "entries.csv", parsed_entries)

        expected_patterns: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for entry in parsed_entries:
            sample_directions, pattern = rotate_canonical_signal_to_sample(
                directions,
                signal,
                entry,
            )
            expected_patterns[entry.entry_id] = (sample_directions, pattern)
            _write_npz(
                stage / "patterns" / f"{entry.entry_id}.npz",
                {
                    "intensity": np.asarray(pattern, dtype="<f8"),
                    "sample_directions": np.asarray(sample_directions, dtype="<f8"),
                },
            )

        validation_directions, validation_signal = expected_patterns[validation_entry_id]
        _write_npz(
            stage / "validation" / f"observed-{validation_entry_id}.npz",
            {
                "intensity": np.asarray(validation_signal, dtype="<f8"),
                "sample_directions": np.asarray(validation_directions, dtype="<f8"),
            },
        )
        ranking = rank_spherical_dictionary(
            canonical_directions=directions,
            canonical_signal=signal,
            entries=parsed_entries,
            sample_directions=validation_directions,
            observed_signal=validation_signal,
        )
        _write_json(
            stage / "validation" / "expected-results.json",
            {
                "schema_version": 1,
                "observed_fixture": f"observed-{validation_entry_id}.npz",
                "metric": "score = 1 - MSE / observed_range^2",
                "known_scope": "fixture convention test; not an experimental EBSD metric",
                "ranking": [
                    {
                        "entry_id": match.entry_id,
                        "score": match.score,
                        "root_mean_square_error": match.root_mean_square_error,
                    }
                    for match in ranking
                ],
            },
        )

        _write_readme(
            stage / "README.md",
            dictionary_id=dictionary_id,
            dictionary_name=dictionary_name,
            phase_name=str(parsed_phase["name"]),
            validation_entry_id=validation_entry_id,
        )
        _write_citation(stage / "CITATION.cff", dictionary_name=dictionary_name, citation_text=citation_text)
        _write_license(stage / "LICENSE", license_id)
        manifest = {
            "schema_name": "ebsd-pattern-dictionary",
            "schema_version": "0.1.0",
            "contract": "spherical-dictionary-resource/v1",
            "dictionary_id": dictionary_id,
            "dictionary_name": dictionary_name,
            "dictionary_version": dictionary_version,
            "created_at": created_at,
            "authors": list(parsed_authors),
            "representation_kind": "spherical",
            "files": _file_inventory(stage),
            "representation": {
                "kind": "spherical",
                "canonical_signal": "spherical_signal.npz",
                "entry_patterns": "patterns/*.npz",
                "direction_count": int(len(directions)),
                "sphere_parameterization": "normalized cube-shell {-1,0,+1} directions",
                "sphere_frame": "canonical crystal frame",
                "sphere_handedness": "right-handed",
                "sphere_axis_labels": ["crystal-x", "crystal-y", "crystal-z"],
                "angular_units": "degree",
                "sampling_resolution": "irregular 26-node cube shell",
                "hemisphere_or_full_sphere": "full_sphere",
                "antipodal_assumption": "none; values are stored directionally",
                "interpolation_method": "none; exact lookup on supplied 26-node lattice only",
                "signal_channel": "intensity",
                "signal_semantics": "source spherical-field raw intensity sampled by nearest direction",
                "intensity_unit": "arbitrary simulated intensity",
                "intensity_transform": "none after source nearest-direction sampling",
                "normalization_scope": "none",
                **canonical_hashes,
            },
            "phase": parsed_phase,
            "entries": {
                "path": "entries.csv",
                "pattern_directory": "patterns",
                "count": len(parsed_entries),
            },
            "orientation_convention": {
                "orientation_representation": "unit_quaternion",
                "quaternion_order": "w,x,y,z",
                "quaternion_convention": "active",
                "quaternion_sign_rule": "w >= 0",
                "rotation_direction": "crystal-to-sample",
                "evaluation": "I_sample(s) = I_crystal(R_cs^-1 s)",
                "frame_handedness": "right-handed",
                "sampling_domain": "three explicit hand-selected orientations",
                "nominal_angular_spacing_degrees": None,
                "coverage_validation": "cube-shell closure under the supplied quarter turns",
            },
            "generation": {"source": parsed_source, "recipe": parsed_recipe},
            "matching": {
                "fixture_metric": "score = 1 - MSE / observed_range^2",
                "recommended_experimental_use": "none; this is a package and convention fixture",
                "required_observed_signal": "spherical float32 or float64 values on the exact 26-node lattice",
                "preprocessing": "none defined; no hidden normalization, denoising, or background correction",
                "detector_projection": "not supplied; a future matcher must declare its own geometry and sampling",
                "phase_candidates": "forsterite only",
                "score_interpretation": "fixture integrity diagnostic only; not confidence",
            },
            "detector_and_projection_geometry": {
                "fixed_geometry": False,
                "runtime_requirements": [
                    "projection model",
                    "projection-center convention and values",
                    "detector dimensions and pixel origin",
                    "sample and detector tilt",
                    "beam and detector-frame directions",
                ],
            },
            "validation": {
                "observed_fixture": f"validation/observed-{validation_entry_id}.npz",
                "expected_results": "validation/expected-results.json",
                "expected_top_entry_id": validation_entry_id,
            },
            "license": license_id,
            "license_file": "LICENSE",
            "citation": "CITATION.cff",
            "integrity": {
                "checksums": "checksums.json",
                "checksum_policy": "SHA-256 and byte count for all files except checksums.json",
            },
            "claim_boundary": {
                "experimental_ebsd_validated": False,
                "not_a_detector_projected_pattern_library": True,
                "not_a_dictionary_indexing_performance_claim": True,
                "not_an_atlas_visual_artifact": True,
            },
        }
        manifest["manifest_sha256"] = _sha256_bytes(canonical_json(manifest).encode("utf-8"))
        _write_json(stage / "dictionary.manifest.json", manifest)
        _write_json(stage / "checksums.json", _checksums(stage))
        _fsync_tree(stage)
        os.rename(stage, root)
        _fsync_directory(root.parent)
    except BaseException:
        if stage.exists():
            for path in sorted(stage.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            stage.rmdir()
        raise
    return SphericalDictionaryResult(
        dictionary_id=dictionary_id,
        path=root,
        manifest_sha256=_sha256_file(root / "dictionary.manifest.json"),
    )
