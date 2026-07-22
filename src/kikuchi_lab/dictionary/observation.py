"""Portable, explicit detector-observation packages for spherical matching."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4

import numpy as np

from kikuchi_lab.dictionary.detector_to_s2 import DetectorToS2Sample, sample_detector_to_s2
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.model.recipes import DetectorRecipe


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SCHEMA = "kikuchi.detector-observation/v1"


@dataclass(frozen=True)
class DetectorObservationPreparation:
    """Raw detector observation resampled onto a declared partial S2 grid."""

    detector_intensity: np.ndarray
    directions: np.ndarray
    sample: DetectorToS2Sample


@dataclass(frozen=True)
class DetectorObservationPackageResult:
    """Identity and location of one atomically published observation package."""

    observation_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class DetectorObservationPackageVerification:
    """Independent check result for one observation package."""

    observation_id: str
    path: Path
    direction_count: int
    covered_direction_count: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
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


def _write_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.savez_compressed(
            handle,
            **{name: np.ascontiguousarray(value) for name, value in arrays.items()},
        )
        handle.flush()
        os.fsync(handle.fileno())


def _unit_directions(value: object) -> np.ndarray:
    directions = np.asarray(value, dtype=np.float64)
    if directions.ndim != 2 or directions.shape[1] != 3 or len(directions) < 2:
        raise ValueError("directions must have shape (N, 3) with at least two entries")
    if not np.all(np.isfinite(directions)) or not np.allclose(
        np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=5.0e-13
    ):
        raise ValueError("directions must be finite unit vectors")
    return np.ascontiguousarray(directions)


def _raw_detector_intensity(value: object, detector: DetectorRecipe) -> np.ndarray:
    intensity = np.asarray(value)
    if intensity.shape != detector.supersampled_shape or not np.issubdtype(intensity.dtype, np.number):
        raise ValueError("detector_intensity must be numeric and match the declared detector shape")
    if not np.all(np.isfinite(intensity)):
        raise ValueError("detector_intensity must be finite")
    return np.ascontiguousarray(intensity)


def _identity_preprocessing(value: object) -> tuple[dict[str, object], ...]:
    try:
        stages = tuple(plain_data(value))
    except TypeError as error:
        raise ValueError("preprocessing must be a sequence of explicit stage mappings") from error
    if not stages:
        raise ValueError("preprocessing must declare the identity stage explicitly")
    expected = ({"name": "identity", "parameters": {}},)
    if stages != expected:
        raise ValueError("only explicit identity preprocessing is currently supported")
    return expected


def _source_record(value: Mapping[str, object]) -> dict[str, str]:
    source = plain_data(value)
    if not isinstance(source, dict) or set(source) != {"kind", "id", "sha256"}:
        raise ValueError("source must have exactly kind, id, and sha256")
    if not all(isinstance(source[name], str) and source[name].strip() for name in ("kind", "id")):
        raise ValueError("source kind and id must be non-empty text")
    if not isinstance(source["sha256"], str) or not _SHA256.fullmatch(source["sha256"]):
        raise ValueError("source sha256 must be a lower-case SHA-256 digest")
    return {name: source[name] for name in ("kind", "id", "sha256")}


def _authors(value: Sequence[str]) -> list[str]:
    names = list(value)
    if not names or any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("authors must be non-empty text")
    return names


def prepare_detector_observation(
    detector_intensity: object,
    directions: object,
    detector: DetectorRecipe,
    *,
    preprocessing: object = ({"name": "identity", "parameters": {}},),
) -> DetectorObservationPreparation:
    """Prepare one raw detector image with named identity preprocessing only.

    The explicit identity stage is deliberate: this function currently refuses
    to hide background subtraction, denoising, saturation handling, or any
    visual transform behind a generic "preprocessing" name. Future transforms
    can be added only as separately tested, serialized stages.
    """
    if not isinstance(detector, DetectorRecipe):
        raise TypeError("detector must be a DetectorRecipe")
    _identity_preprocessing(preprocessing)
    intensity = _raw_detector_intensity(detector_intensity, detector)
    samples = _unit_directions(directions)
    sampled = sample_detector_to_s2(intensity.astype(np.float64), samples, detector)
    return DetectorObservationPreparation(
        detector_intensity=intensity,
        directions=samples,
        sample=sampled,
    )


def _manifest_payload(
    *,
    observation_id: str,
    observation_version: str,
    created_at: str,
    authors: list[str],
    source: dict[str, str],
    detector: DetectorRecipe,
    preparation: DetectorObservationPreparation,
) -> dict[str, object]:
    intensity = preparation.detector_intensity
    directions = preparation.directions
    sample = preparation.sample
    return {
        "schema": _SCHEMA,
        "observation_id": observation_id,
        "observation_version": observation_version,
        "created_at": created_at,
        "authors": authors,
        "source": source,
        "input": {
            "path": "observed-detector.npy",
            "shape": list(intensity.shape),
            "dtype": intensity.dtype.str,
            "intensity_kind": "raw numeric detector intensity",
            "pixel_origin": "top-left row-column",
        },
        "detector_geometry": detector.to_dict(),
        "preprocessing": {
            "stages": [{"name": "identity", "parameters": {}}],
            "nonclaims": [
                "No background correction",
                "No denoising or blur",
                "No gain normalization",
                "No saturation correction",
            ],
        },
        "adapter": {
            "projection_model": "gnomonic",
            "detector_sampling": "bilinear detector pixel sampling onto fixed sample-frame S2 directions",
            "direction_grid_path": "fixed-s2-directions.npy",
            "direction_count": int(len(directions)),
            "partial_signal_path": "partial-s2-signal.npz",
            "covered_direction_count": int(np.sum(sample.covered)),
            "outside_coverage": "NaN signal values and false coverage mask",
        },
        "matching": {
            "recommended_metric": "masked mean-centered normalized cosine",
            "metric_constraint": "compare only observations with an explicitly named coverage mask",
        },
        "claim_boundary": (
            "This package preserves one raw detector observation and a named geometry-only "
            "identity-preprocessing adapter result. It is not a calibration, an acquired-pattern "
            "benchmark, a phase/orientation solution, or a general preprocessing pipeline."
        ),
    }


def _checksums(root: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "excludes": ["checksums.json"],
        "files": {
            path.relative_to(root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
            for path in sorted(item for item in root.rglob("*") if item.is_file())
            if path.name != "checksums.json"
        },
    }


def _write_readme(path: Path, *, observation_id: str) -> None:
    _write_bytes(
        path,
        (
            "# Detector observation package\n\n"
            f"Observation ID: `{observation_id}`.\n\n"
            "This package carries raw detector values, named detector geometry, explicit "
            "identity preprocessing, an exact fixed-S2 grid, and the resulting partial-S2 "
            "signal/coverage mask. It deliberately does not perform hidden background "
            "correction, denoising, intensity normalization, or detector calibration.\n"
        ).encode("utf-8"),
    )


def publish_detector_observation_package(
    *,
    output_root: str | Path,
    detector_intensity: object,
    directions: object,
    detector: DetectorRecipe,
    source: Mapping[str, object],
    observation_version: str,
    created_at: str,
    authors: Sequence[str],
    preprocessing: object = ({"name": "identity", "parameters": {}},),
) -> DetectorObservationPackageResult:
    """Atomically publish a portable detector-to-partial-S2 observation package."""
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError(f"observation package output already exists: {root}")
    if not isinstance(observation_version, str) or not observation_version.strip():
        raise ValueError("observation_version must be non-empty text")
    if not isinstance(created_at, str) or not _UTC.fullmatch(created_at):
        raise ValueError("created_at must be a UTC ISO-8601 timestamp")
    source_record = _source_record(source)
    author_names = _authors(authors)
    preparation = prepare_detector_observation(
        detector_intensity,
        directions,
        detector,
        preprocessing=preprocessing,
    )
    observation_id = stable_id(
        "detector-observation",
        {
            "schema": _SCHEMA,
            "version": observation_version,
            "source": source_record,
            "detector": detector.to_dict(),
            "input_shape": list(preparation.detector_intensity.shape),
            "input_dtype": preparation.detector_intensity.dtype.str,
            "direction_grid": preparation.directions.tolist(),
            "preprocessing": [{"name": "identity", "parameters": {}}],
        },
    )
    manifest = _manifest_payload(
        observation_id=observation_id,
        observation_version=observation_version,
        created_at=created_at,
        authors=author_names,
        source=source_record,
        detector=detector,
        preparation=preparation,
    )
    manifest_sha256 = _sha256_bytes(canonical_json(manifest).encode("utf-8"))
    manifest["manifest_sha256"] = manifest_sha256
    staging = root.parent / f".{root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npy(staging / "observed-detector.npy", preparation.detector_intensity)
        _write_npy(staging / "fixed-s2-directions.npy", preparation.directions)
        _write_npz(
            staging / "partial-s2-signal.npz",
            values=preparation.sample.values,
            covered=preparation.sample.covered,
            pixel_coordinates_yx=preparation.sample.pixel_coordinates_yx,
        )
        _write_readme(staging / "README.md", observation_id=observation_id)
        _write_json(staging / "observation.manifest.json", manifest)
        _write_json(staging / "checksums.json", _checksums(staging))
        os.replace(staging, root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return DetectorObservationPackageResult(observation_id, root, manifest_sha256)


def verify_detector_observation_package(
    path: str | Path,
) -> DetectorObservationPackageVerification:
    """Verify package hashes and structural compatibility without matching it."""
    root = Path(path).resolve()
    manifest_path = root / "observation.manifest.json"
    checksums_path = root / "checksums.json"
    if not manifest_path.is_file() or not checksums_path.is_file():
        raise ValueError("observation package is missing manifest or checksums")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != _SCHEMA:
        raise ValueError("observation manifest schema is not supported")
    expected_manifest_sha = manifest.get("manifest_sha256")
    material = dict(manifest)
    material.pop("manifest_sha256", None)
    if not isinstance(expected_manifest_sha, str) or expected_manifest_sha != _sha256_bytes(
        canonical_json(material).encode("utf-8")
    ):
        raise ValueError("observation manifest hash does not match its canonical payload")
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    files = checksums.get("files") if isinstance(checksums, dict) else None
    if not isinstance(files, dict):
        raise ValueError("observation checksums do not declare files")
    for relative, record in files.items():
        if not isinstance(relative, str) or not isinstance(record, dict):
            raise ValueError("observation checksum record is malformed")
        target = root / relative
        if not target.is_file() or record.get("sha256") != _sha256_file(target):
            raise ValueError(f"observation checksum mismatch for {relative}")
    directions = _unit_directions(np.load(root / "fixed-s2-directions.npy", allow_pickle=False))
    partial = np.load(root / "partial-s2-signal.npz", allow_pickle=False)
    values = np.asarray(partial["values"], dtype=np.float64)
    covered = np.asarray(partial["covered"], dtype=bool)
    pixels = np.asarray(partial["pixel_coordinates_yx"], dtype=np.float64)
    if values.shape != (len(directions),) or covered.shape != values.shape or pixels.shape != (len(values), 2):
        raise ValueError("observation partial-S2 arrays do not match the direction grid")
    if not np.all(np.isfinite(values[covered])) or int(np.sum(covered)) < 2:
        raise ValueError("observation partial-S2 signal lacks finite covered values")
    observation_id = manifest.get("observation_id")
    if not isinstance(observation_id, str) or not observation_id:
        raise ValueError("observation manifest has no observation id")
    return DetectorObservationPackageVerification(
        observation_id=observation_id,
        path=root,
        direction_count=len(directions),
        covered_direction_count=int(np.sum(covered)),
    )


__all__ = [
    "DetectorObservationPackageResult",
    "DetectorObservationPackageVerification",
    "DetectorObservationPreparation",
    "prepare_detector_observation",
    "publish_detector_observation_package",
    "verify_detector_observation_package",
]
