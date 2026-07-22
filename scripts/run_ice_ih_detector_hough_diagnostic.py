#!/usr/bin/env python3
"""Seal a native-resolution Hough diagnostic for the Ice Ih detector proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from kikuchi_lab.diagnostics import HoughLineDiagnostic, image_hough_lines
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-detector-hough-diagnostic-v0.1.0"
_DETECTOR_ARRAY = "products/kinematical-detector.npy"


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


def _write_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.save(handle, np.ascontiguousarray(value), allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())


def _checked_detector(run_root: Path) -> tuple[Path, dict[str, object]]:
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(_DETECTOR_ARRAY), dict):
        raise ValueError(f"source run manifest does not declare {_DETECTOR_ARRAY}")
    detector = run_root / _DETECTOR_ARRAY
    if _sha256(detector) != files[_DETECTOR_ARRAY].get("sha256"):
        raise ValueError("source detector hash differs from source run manifest")
    return detector, manifest


def _plot_hough_lines(axis: plt.Axes, result: HoughLineDiagnostic) -> None:
    height, width = result.edge_mask.shape
    x = np.asarray((0.0, width - 1.0))
    for theta, distance in zip(
        result.peak_theta_radians[:12], result.peak_distance_pixels[:12], strict=True
    ):
        sin_theta = float(np.sin(theta))
        cos_theta = float(np.cos(theta))
        if abs(sin_theta) > 1e-12:
            axis.plot(x, (distance - x * cos_theta) / sin_theta, color="#54c5c8", linewidth=0.65)
        elif abs(cos_theta) > 1e-12:
            axis.axvline(distance / cos_theta, color="#54c5c8", linewidth=0.65)
    axis.set_xlim(0, width - 1)
    axis.set_ylim(height - 1, 0)


def _figure(path: Path, *, detector: np.ndarray, result: HoughLineDiagnostic) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 11))
    figure.subplots_adjust(left=0.055, right=0.95, top=0.83, bottom=0.075, wspace=0.22, hspace=0.24)
    figure.suptitle("Ice Ih: raw detector pattern → finite-difference edges → Hough accumulator", fontsize=19, fontweight="bold")
    figure.text(
        0.5,
        0.895,
        "Native-resolution image-space diagnostic: no Gaussian blur, no detector-to-sphere transform, and no orientation solution.",
        ha="center",
        va="center",
        fontsize=10.3,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.872,
        f"Finite-difference gradient threshold: top {100.0 - result.edge_percentile:.1f}% of pixels; accumulator peaks are line hypotheses only.",
        ha="center",
        va="center",
        fontsize=9.8,
        color="#34495e",
    )
    low, high = np.quantile(detector, (0.005, 0.9985))
    raw_axis, gradient_axis, edge_axis, hough_axis = axes.reshape(-1)
    raw = raw_axis.imshow(detector, cmap="gray", interpolation="nearest", vmin=low, vmax=high)
    _plot_hough_lines(raw_axis, result)
    raw_axis.set_title("1. Raw kinematical detector + top Hough hypotheses", fontsize=12)
    raw_axis.set_axis_off()
    raw_bar = figure.colorbar(raw, ax=raw_axis, fraction=0.046, pad=0.03)
    raw_bar.set_label("raw intensity", fontsize=9)

    gradient = gradient_axis.imshow(
        np.log1p(result.gradient_magnitude), cmap="magma", interpolation="nearest"
    )
    gradient_axis.set_title("2. log(1 + finite-difference gradient magnitude)", fontsize=12)
    gradient_axis.set_axis_off()
    gradient_bar = figure.colorbar(gradient, ax=gradient_axis, fraction=0.046, pad=0.03)
    gradient_bar.set_label("display transform only", fontsize=9)

    edge_axis.imshow(result.edge_mask, cmap="gray", interpolation="nearest", vmin=0.0, vmax=1.0)
    edge_axis.set_title("3. Binary edge support used by accumulator", fontsize=12)
    edge_axis.set_axis_off()

    theta_degrees = np.degrees(result.theta_radians)
    accumulator = np.log1p(result.accumulator.astype(np.float64))
    hough = hough_axis.imshow(
        accumulator,
        cmap="viridis",
        aspect="auto",
        interpolation="nearest",
        extent=(theta_degrees[0], theta_degrees[-1], result.distance_pixels[-1], result.distance_pixels[0]),
    )
    hough_axis.scatter(
        np.degrees(result.peak_theta_radians),
        result.peak_distance_pixels,
        facecolors="none",
        edgecolors="#f8f9f9",
        s=34,
        linewidths=0.8,
    )
    hough_axis.set(
        title="4. log(1 + Hough line accumulator)",
        xlabel="line normal angle (degrees)",
        ylabel="line distance from detector origin (pixels)",
    )
    accumulator_bar = figure.colorbar(hough, ax=hough_axis, fraction=0.046, pad=0.03)
    accumulator_bar.set_label("log vote count", fontsize=9)
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(
    run_root: Path,
    output_root: Path,
    *,
    edge_percentile: float,
    theta_step_degrees: float,
    peak_count: int,
) -> None:
    run_root = run_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"Hough diagnostic output already exists: {output_root}")
    detector_path, manifest = _checked_detector(run_root)
    detector = np.asarray(np.load(detector_path, allow_pickle=False), dtype=np.float32)
    result = image_hough_lines(
        detector,
        edge_percentile=edge_percentile,
        theta_step_degrees=theta_step_degrees,
        peak_count=peak_count,
    )
    peak_records = [
        {
            "votes": int(votes),
            "theta_degrees": float(np.degrees(theta)),
            "distance_pixels": float(distance),
        }
        for votes, theta, distance in zip(
            result.peak_accumulator_values,
            result.peak_theta_radians,
            result.peak_distance_pixels,
            strict=True,
        )
    ]
    record = {
        "schema": "kikuchi.ice-ih-detector-hough-diagnostic/v1",
        "source_run": {
            "run_id": manifest["run_id"],
            "detector_path": detector_path.relative_to(ROOT).as_posix(),
            "detector_file_sha256": _sha256(detector_path),
            "shape": list(detector.shape),
        },
        "edge_support": {
            "method": "native-resolution finite-difference gradient magnitude threshold",
            "gaussian_or_other_smoothing": "none",
            "edge_percentile": result.edge_percentile,
            "edge_pixel_count": int(np.sum(result.edge_mask)),
            "edge_fraction": float(np.mean(result.edge_mask)),
        },
        "hough": {
            "kind": "standard image-space line Hough transform",
            "theta_step_degrees": theta_step_degrees,
            "accumulator_shape": list(result.accumulator.shape),
            "peaks": peak_records,
        },
        "claim_boundary": (
            "Image-space line-evidence diagnostic only. It does not identify crystallographic "
            "bands, determine an orientation, apply detector geometry, or establish acquired-EBSD performance."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npy(staging / "gradient-magnitude.npy", result.gradient_magnitude)
        _write_npy(staging / "edge-mask.npy", result.edge_mask)
        _write_npy(staging / "hough-accumulator.npy", result.accumulator)
        _write_npy(staging / "hough-theta-radians.npy", result.theta_radians)
        _write_npy(staging / "hough-distance-pixels.npy", result.distance_pixels)
        _write_json(staging / "hough-diagnostic.json", record)
        _figure(staging / "detector-hough-diagnostic.png", detector=detector, result=result)
        checksums = {
            "schema_version": 1,
            "files": {
                item.relative_to(staging).as_posix(): {
                    "bytes": item.stat().st_size,
                    "sha256": _sha256(item),
                }
                for item in sorted(path for path in staging.rglob("*") if path.is_file())
            },
        }
        _write_json(staging / "checksums.json", checksums)
        os.replace(staging, output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"Detector Hough diagnostic: {output_root}")
    print(f"Edge pixels: {int(np.sum(result.edge_mask))}/{result.edge_mask.size}")
    print(f"Accumulator shape: {tuple(result.accumulator.shape)}")
    print(f"Peak count: {len(result.peak_accumulator_values)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--edge-percentile", type=float, default=99.2)
    parser.add_argument("--theta-step-degrees", type=float, default=0.5)
    parser.add_argument("--peak-count", type=int, default=16)
    args = parser.parse_args(argv)
    try:
        run(
            args.run,
            args.output,
            edge_percentile=args.edge_percentile,
            theta_step_degrees=args.theta_step_degrees,
            peak_count=args.peak_count,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
