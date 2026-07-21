#!/usr/bin/env python3
"""Seal a source-bound Ice Ih master-to-detector reprojection proof."""

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

from kikuchi_lab.dictionary.detector_to_s2 import reproject_stereographic_master_to_detector
from kikuchi_lab.dictionary.ice_ih import verify_ice_ih_candidate_dictionary
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RUN = ROOT / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-master-detector-congruence-v0.1.1"
_DETECTOR_ARRAY = "products/kinematical-detector.npy"
_MASTER_ARRAY = "products/kinematical-master-stereographic.npy"


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


def _checked_run_array(run_root: Path, relative_path: str) -> Path:
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(relative_path), dict):
        raise ValueError(f"source run manifest does not declare {relative_path}")
    path = run_root / relative_path
    if _sha256(path) != files[relative_path].get("sha256"):
        raise ValueError(f"source run array hash differs from its manifest: {relative_path}")
    return path


def _center_l2(values: np.ndarray) -> np.ndarray:
    centered = values - float(np.mean(values))
    scale = float(np.linalg.norm(centered))
    if not np.isfinite(scale) or scale <= np.finfo(np.float64).eps:
        raise ValueError("detector field must have non-zero finite variance")
    return centered / scale


def _zscore(values: np.ndarray) -> np.ndarray:
    centered = values - float(np.mean(values))
    scale = float(np.std(centered))
    if not np.isfinite(scale) or scale <= np.finfo(np.float64).eps:
        raise ValueError("detector field must have non-zero finite variance")
    return centered / scale


def _figure(
    path: Path,
    *,
    detector: np.ndarray,
    reprojection: np.ndarray,
    residual: np.ndarray,
    centered_cosine: float,
    correlation: float,
    normalized_rmse: float,
) -> None:
    shared_min, shared_max = np.quantile(
        np.concatenate((detector.reshape(-1), reprojection.reshape(-1))), (0.005, 0.9985)
    )
    residual_limit = float(np.quantile(np.abs(residual), 0.999))
    display_indices = np.linspace(0, detector.size - 1, 40000, dtype=np.intp)
    source_values = detector.reshape(-1)[display_indices]
    projected_values = reprojection.reshape(-1)[display_indices]
    line_min, line_max = np.quantile(
        np.concatenate((source_values, projected_values)), (0.002, 0.998)
    )

    figure, axes = plt.subplots(2, 2, figsize=(13.5, 13.0))
    figure.subplots_adjust(left=0.055, right=0.955, top=0.85, bottom=0.07, wspace=0.19, hspace=0.2)
    figure.suptitle(
        "Ice Ih: raw detector pattern ↔ canonical-master reprojection",
        fontsize=20,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.91,
        "Same-source geometry congruence only — no intensity fit, detector preprocessing, or acquired-data claim.",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.885,
        "The master is bilinearly sampled through the declared TSL PC and sample-to-detector transform.",
        ha="center",
        va="center",
        fontsize=10.0,
        color="#34495e",
    )

    source_axis, projected_axis, residual_axis, scatter_axis = axes.reshape(-1)
    for axis, field, title in (
        (source_axis, detector, "1. Checked raw simulated detector"),
        (projected_axis, reprojection, "2. Canonical master reprojected to detector"),
    ):
        image = axis.imshow(
            field,
            cmap="gray",
            interpolation="nearest",
            vmin=shared_min,
            vmax=shared_max,
        )
        axis.set_title(title, fontsize=12.5)
        axis.set_axis_off()
    colorbar = figure.colorbar(image, ax=(source_axis, projected_axis), fraction=0.028, pad=0.018)
    colorbar.set_label("raw kinematical intensity", fontsize=9)

    residual_image = residual_axis.imshow(
        residual,
        cmap="coolwarm",
        interpolation="nearest",
        vmin=-residual_limit,
        vmax=residual_limit,
    )
    residual_axis.set_title("3. Normalized residual (source − reprojection)", fontsize=12.5)
    residual_axis.set_axis_off()
    residual_bar = figure.colorbar(residual_image, ax=residual_axis, fraction=0.046, pad=0.03)
    residual_bar.set_label("per-field z-score difference", fontsize=9)

    scatter_axis.scatter(source_values, projected_values, s=0.26, alpha=0.14, color="#1f6177", linewidths=0)
    scatter_axis.plot((line_min, line_max), (line_min, line_max), color="#c0392b", linewidth=1.0)
    scatter_axis.set(
        title="4. Pixelwise congruence (40,000 samples)",
        xlabel="source detector intensity",
        ylabel="master-reprojected intensity",
        xlim=(line_min, line_max),
        ylim=(line_min, line_max),
    )
    scatter_axis.set_aspect("equal", adjustable="box")
    scatter_axis.grid(alpha=0.18, linewidth=0.5)
    scatter_axis.text(
        0.035,
        0.955,
        "\n".join(
            (
                f"centered cosine: {centered_cosine:.9f}",
                f"Pearson r: {correlation:.9f}",
                f"normalized RMSE: {normalized_rmse:.6f}",
            )
        ),
        transform=scatter_axis.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#78909c"},
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, run_root: Path, recipe_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    run_root = run_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"congruence proof output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    dictionary_manifest = json.loads(
        (dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8")
    )
    detector_path = _checked_run_array(run_root, _DETECTOR_ARRAY)
    run_master_path = _checked_run_array(run_root, _MASTER_ARRAY)
    dictionary_master_path = dictionary_root / dictionary_manifest["source"]["master_path"]
    if _sha256(dictionary_master_path) != _sha256(run_master_path):
        raise ValueError("dictionary master bytes differ from checked source-run master")
    recipe = load_kinematical_recipe(recipe_path)
    run_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    if run_manifest["run_identity"].get("recipe_id") != recipe.recipe_id:
        raise ValueError("detector recipe differs from the declared source run")
    detector = np.asarray(np.load(detector_path, allow_pickle=False), dtype=np.float64)
    master = np.load(dictionary_master_path, allow_pickle=False)
    reprojection = reproject_stereographic_master_to_detector(master, recipe.detector)
    source_normalized = _center_l2(detector)
    reprojection_normalized = _center_l2(reprojection)
    source_zscore = _zscore(detector)
    reprojection_zscore = _zscore(reprojection)
    residual = source_zscore - reprojection_zscore
    centered_cosine = float(
        np.dot(source_normalized.reshape(-1), reprojection_normalized.reshape(-1))
    )
    correlation = float(
        np.corrcoef(detector.reshape(-1), reprojection.reshape(-1))[0, 1]
    )
    normalized_rmse = float(np.sqrt(np.mean(residual * residual)))

    result = {
        "schema": "kikuchi.ice-ih-master-detector-congruence/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": dictionary_manifest["manifest_sha256"],
            "master_path": dictionary_master_path.relative_to(ROOT).as_posix(),
            "master_file_sha256": _sha256(dictionary_master_path),
        },
        "source_run": {
            "run_id": run_manifest["run_id"],
            "detector_path": detector_path.relative_to(ROOT).as_posix(),
            "detector_file_sha256": _sha256(detector_path),
            "master_path": run_master_path.relative_to(ROOT).as_posix(),
            "master_file_sha256": _sha256(run_master_path),
            "recipe_path": recipe_path.relative_to(ROOT).as_posix(),
            "recipe_id": recipe.recipe_id,
            "detector_geometry": recipe.detector.to_dict(),
        },
        "reprojection": {
            "master_sampling": "bilinear upper/lower stereographic master sampling",
            "projection": "gnomonic detector rays via kikuchipy EBSDDetector",
            "crystal_to_sample_matrix": np.eye(3, dtype=np.float64).tolist(),
            "tone_or_background_processing": "none",
        },
        "metrics": {
            "pixel_count": int(detector.size),
            "centered_cosine": centered_cosine,
            "pearson_correlation": correlation,
            "normalized_rmse": normalized_rmse,
        },
        "claim_boundary": (
            "Source-bound congruence proof: both detector and master originate from the same "
            "checked kinematical run. It is not independent physics validation, detector "
            "calibration, acquired-EBSD validation, or indexing accuracy evidence."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npy(staging / "master-reprojected-detector.npy", reprojection.astype(np.float32))
        _write_npy(staging / "normalized-residual.npy", residual.astype(np.float32))
        _write_json(staging / "congruence.json", result)
        _figure(
            staging / "master-detector-congruence.png",
            detector=detector,
            reprojection=reprojection,
            residual=residual,
            centered_cosine=centered_cosine,
            correlation=correlation,
            normalized_rmse=normalized_rmse,
        )
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
    print(f"Master-detector congruence proof: {output_root}")
    print(f"Centered cosine: {centered_cosine:.9f}")
    print(f"Pearson correlation: {correlation:.9f}")
    print(f"Normalized RMSE: {normalized_rmse:.9f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        run(args.dictionary, args.run, args.recipe, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
