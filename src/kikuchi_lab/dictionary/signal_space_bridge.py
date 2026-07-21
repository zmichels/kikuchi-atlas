"""Source-bound figures that distinguish detector, spherical, and cache spaces."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
from uuid import uuid4

import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from kikuchi_lab.model.identity import canonical_json


_UNIT_TOLERANCE = 5.0e-13
_SHA256_LENGTH = 64


@dataclass(frozen=True)
class SignalSpaceBridgeResult:
    """Identity and path of one atomically published signal-space bridge."""

    path: Path
    manifest_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: object) -> None:
    _write_bytes(path, canonical_json(value).encode("utf-8"))


def _relative_source_path(path: Path, source_root: Path) -> str:
    try:
        return path.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"source path escapes source_root: {path}") from error


def _source_file(path: Path, source_root: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"required source file does not exist: {path}")
    return {
        "path": _relative_source_path(path, source_root),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _load_rgb(path: Path) -> np.ndarray:
    try:
        with Image.open(path) as image:
            raw = np.asarray(image)
            if raw.ndim == 2 and np.issubdtype(raw.dtype, np.integer):
                scale = np.iinfo(raw.dtype).max
                values = raw.astype(np.float64) / float(scale)
                return np.repeat(values[:, :, None], 3, axis=2)
            return np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0
    except OSError as error:
        raise ValueError(f"source image is not readable: {path}") from error


def _load_directions(path: Path) -> np.ndarray:
    directions = np.asarray(np.load(path, allow_pickle=False), dtype=np.float64)
    if directions.ndim != 2 or directions.shape[1] != 3 or len(directions) == 0:
        raise ValueError("directions must be a non-empty (N, 3) NPY array")
    if not np.all(np.isfinite(directions)):
        raise ValueError("directions must be finite")
    norms = np.linalg.norm(directions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError("directions must be unit vectors")
    return np.ascontiguousarray(directions)


def _load_signal(path: Path, count: int) -> np.ndarray:
    signal = np.asarray(np.load(path, allow_pickle=False), dtype=np.float64)
    if signal.shape != (count,):
        raise ValueError("observed signal and directions must have the same number of values")
    if not np.all(np.isfinite(signal)):
        raise ValueError("observed signal must contain finite values")
    centered = signal - float(np.mean(signal))
    norm = float(np.linalg.norm(centered))
    if norm <= np.finfo(np.float64).eps:
        raise ValueError("observed signal must have non-zero variance")
    return np.ascontiguousarray(centered / norm, dtype=np.float64)


def _write_figure(
    path: Path,
    *,
    detector_image: np.ndarray,
    master_image: np.ndarray,
    directions: np.ndarray,
    observed_signal: np.ndarray,
    phase_name: str,
) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(18, 8))
    figure.subplots_adjust(left=0.035, right=0.94, top=0.77, bottom=0.1, wspace=0.14)
    figure.suptitle(
        f"{phase_name}: detector image → directional field → dictionary feature vector",
        fontsize=19,
        fontweight="bold",
        y=0.985,
    )
    figure.text(
        0.5,
        0.905,
        "Related representations of one kinematical model.\n"
        "Current matcher consumes only panel 3; neither Hough/Radon space nor a detector-to-S² adapter is shown.",
        ha="center",
        va="center",
        fontsize=11,
        color="#34495e",
    )

    detector_axis, master_axis, cache_axis = axes
    detector_axis.imshow(detector_image)
    detector_axis.set_title("1. Detector projection\nimage-like Kikuchi bands", fontsize=14)
    detector_axis.set_axis_off()

    master_axis.imshow(master_image)
    master_axis.set_title(
        "2. Crystal-frame master field\nupper/lower stereographic hemispheres", fontsize=14
    )
    master_axis.set_axis_off()

    longitude = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    latitude = np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))
    limit = max(float(np.max(np.abs(observed_signal))), np.finfo(np.float64).eps)
    scatter = cache_axis.scatter(
        longitude,
        latitude,
        c=observed_signal,
        cmap="coolwarm",
        vmin=-limit,
        vmax=limit,
        s=13,
        linewidths=0.0,
    )
    cache_axis.set(
        title="3. Sample-frame cache signal\nfixed S² samples; not a detector image",
        xlim=(-180.0, 180.0),
        ylim=(-90.0, 90.0),
        xlabel="longitude (deg)",
        ylabel="latitude (deg)",
    )
    cache_axis.set_facecolor("#f7f9fb")
    cache_axis.grid(alpha=0.28, linewidth=0.5)
    colorbar = figure.colorbar(scatter, ax=cache_axis, fraction=0.047, pad=0.03)
    colorbar.set_label("mean-centered / L2-normalized feature value", fontsize=9)
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def publish_signal_space_bridge(
    *,
    output_root: Path,
    detector_image: Path,
    master_image: Path,
    directions_path: Path,
    observed_signal_path: Path,
    source_root: Path,
    phase_name: str,
    dictionary_id: str,
    dictionary_manifest_sha256: str,
    dictionary_entry_count: int,
) -> SignalSpaceBridgeResult:
    """Publish a human-readable bridge for the exact current S² matcher input.

    The panel layout deliberately does not claim that detector pixels are
    projected into S². It instead documents the currently separate spaces and
    makes the unimplemented adapter boundary visible in both figure and JSON.
    """
    output_root = output_root.resolve()
    source_root = source_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"signal-space bridge output already exists: {output_root}")
    if not isinstance(phase_name, str) or not phase_name.strip():
        raise ValueError("phase_name must be non-empty text")
    if not isinstance(dictionary_id, str) or not dictionary_id.strip():
        raise ValueError("dictionary_id must be non-empty text")
    if (
        not isinstance(dictionary_manifest_sha256, str)
        or len(dictionary_manifest_sha256) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in dictionary_manifest_sha256)
    ):
        raise ValueError("dictionary_manifest_sha256 must be a lower-case SHA-256 digest")
    if type(dictionary_entry_count) is not int or dictionary_entry_count <= 0:
        raise ValueError("dictionary_entry_count must be a positive integer")

    detector_image = detector_image.resolve()
    master_image = master_image.resolve()
    directions_path = directions_path.resolve()
    observed_signal_path = observed_signal_path.resolve()
    source_files = sorted(
        (
            _source_file(detector_image, source_root),
            _source_file(master_image, source_root),
            _source_file(directions_path, source_root),
            _source_file(observed_signal_path, source_root),
        ),
        key=lambda record: str(record["path"]),
    )
    directions = _load_directions(directions_path)
    observed_signal = _load_signal(observed_signal_path, len(directions))
    detector_pixels = _load_rgb(detector_image)
    master_pixels = _load_rgb(master_image)

    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        figure_path = staging / "ice-ih-signal-space-bridge.png"
        _write_figure(
            figure_path,
            detector_image=detector_pixels,
            master_image=master_pixels,
            directions=directions,
            observed_signal=observed_signal,
            phase_name=phase_name,
        )
        manifest = {
            "schema": "kikuchi.signal-space-bridge/v1",
            "phase_name": phase_name,
            "dictionary": {
                "id": dictionary_id,
                "manifest_sha256": dictionary_manifest_sha256,
                "entry_count": dictionary_entry_count,
            },
            "cache_signal": {
                "direction_count": int(len(directions)),
                "direction_frame": "sample",
                "normalization": "mean-center-and-L2-normalize",
                "matching_metric": "normalized-cosine",
            },
            "signal_spaces": [
                {
                    "id": "detector_projection",
                    "role": "source visualization only",
                    "description": "Kinematical detector-plane pattern with image-like Kikuchi bands.",
                },
                {
                    "id": "stereographic_master",
                    "role": "crystal-frame directional source field",
                    "description": "Upper/lower stereographic hemispheres used to evaluate orientation candidates.",
                },
                {
                    "id": "sample_frame_s2_cache_signal",
                    "role": "current exact matcher input",
                    "description": "One scalar feature at every declared sample-frame S² direction.",
                },
            ],
            "claim_boundary": {
                "hough_space": "not represented",
                "detector_to_s2_adapter": "not implemented",
                "acquired_ebsd_indexing": "not validated",
            },
            "source_files": source_files,
            "outputs": {"figure": figure_path.name},
        }
        manifest_path = staging / "signal-space-bridge.json"
        _write_json(manifest_path, manifest)
        checksums = {
            "schema_version": 1,
            "files": {
                path.relative_to(staging).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in sorted(item for item in staging.rglob("*") if item.is_file())
            },
        }
        _write_json(staging / "checksums.json", checksums)
        os.replace(staging, output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return SignalSpaceBridgeResult(
        path=output_root,
        manifest_sha256=_sha256(output_root / "signal-space-bridge.json"),
    )
