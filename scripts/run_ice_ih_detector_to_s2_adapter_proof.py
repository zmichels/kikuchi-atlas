#!/usr/bin/env python3
"""Seal an Ice Ih detector-to-partial-S2 geometry and ranking proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from kikuchi_lab.dictionary.detector_to_s2 import (
    rank_masked_candidate_matrix,
    sample_detector_to_s2,
)
from kikuchi_lab.dictionary.ice_ih import (
    quaternion_misorientation_degrees,
    verify_ice_ih_candidate_dictionary,
)
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RUN = ROOT / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-detector-to-s2-proof-v0.1.0"
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


def _source_array(run_root: Path, relative_path: str) -> tuple[Path, dict[str, object]]:
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(relative_path), dict):
        raise ValueError(f"source run manifest does not declare {relative_path}")
    path = run_root / relative_path
    declared = files[relative_path]
    if _sha256(path) != declared.get("sha256"):
        raise ValueError(f"source run array hash differs from its manifest: {relative_path}")
    return path, manifest


def _write_figure(
    path: Path,
    *,
    detector: np.ndarray,
    pixels_yx: np.ndarray,
    covered: np.ndarray,
    directions: np.ndarray,
    sampled_values: np.ndarray,
    top_scores: list[float],
    identity_index: int,
    top_index: int,
    top_error_degrees: float,
) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(18, 7))
    figure.subplots_adjust(left=0.035, right=0.975, top=0.78, bottom=0.13, wspace=0.28)
    figure.suptitle("Ice Ih: detector pixels → covered S² samples → masked cache ranking", fontsize=18)
    figure.text(
        0.5,
        0.91,
        "Geometry self-consistency proof only: raw simulated detector array, exact declared camera model, "
        "and a partial-S² metric separate from the current full-S² Rust matcher.",
        ha="center",
        va="center",
        fontsize=10,
        color="#34495e",
    )

    detector_axis, sphere_axis, score_axis = axes
    detector_axis.imshow(detector, cmap="gray", interpolation="nearest")
    detector_axis.scatter(
        pixels_yx[covered, 1],
        pixels_yx[covered, 0],
        s=5,
        facecolors="none",
        edgecolors="#54c5c8",
        linewidths=0.45,
    )
    detector_axis.set_title("1. Source detector pattern\n308 mapped cache directions", fontsize=13)
    detector_axis.set_axis_off()

    longitude = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    latitude = np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))
    scatter = sphere_axis.scatter(
        longitude[covered],
        latitude[covered],
        c=sampled_values[covered],
        cmap="gray",
        s=26,
        linewidths=0.0,
    )
    sphere_axis.set(
        title="2. Detector-derived partial S² signal\nraw intensity at covered directions",
        xlim=(-180.0, 180.0),
        ylim=(-90.0, 90.0),
        xlabel="sample-frame longitude (deg)",
        ylabel="sample-frame latitude (deg)",
    )
    sphere_axis.set_facecolor("#101519")
    sphere_axis.grid(alpha=0.18, linewidth=0.4)
    colorbar = figure.colorbar(scatter, ax=sphere_axis, fraction=0.047, pad=0.03)
    colorbar.set_label("raw detector intensity", fontsize=9)

    ranks = np.arange(1, len(top_scores) + 1)
    score_axis.barh(ranks, top_scores, color="#54c5c8")
    score_axis.invert_yaxis()
    score_axis.set(
        title="3. Masked candidate ranking\ncoverage-specific normalized cosine",
        xlabel="masked normalized cosine",
        ylabel="candidate rank",
    )
    score_axis.grid(axis="x", alpha=0.24, linewidth=0.5)
    score_axis.text(
        0.04,
        0.05,
        "\n".join(
            (
                f"top entry: {top_index}",
                f"identity entry: {identity_index}",
                f"top error: {top_error_degrees:.6f}°",
            )
        ),
        transform=score_axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#f4f7fa", "edgecolor": "#78909c"},
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, run_root: Path, recipe_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    run_root = run_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"adapter proof output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    dictionary_manifest = json.loads(
        (dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8")
    )
    cache_info = dictionary_manifest["candidate_cache"]
    detector_path, run_manifest = _source_array(run_root, _DETECTOR_ARRAY)
    recipe = load_kinematical_recipe(recipe_path)
    if run_manifest["run_identity"].get("recipe_id") != recipe.recipe_id:
        raise ValueError("detector recipe differs from the declared source run")
    detector = np.load(detector_path, allow_pickle=False)
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    quaternions = np.load(
        dictionary_root / cache_info["quaternions_path"], allow_pickle=False, mmap_mode="r"
    )
    sampled = sample_detector_to_s2(detector, directions, recipe.detector)
    matches = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=5)
    identity_index = int(np.argmax(quaternions[:, 0]))
    top_error = quaternion_misorientation_degrees(
        quaternions[matches[0].entry_index], quaternions[identity_index]
    )
    result = {
        "schema": "kikuchi.ice-ih-detector-to-s2-proof/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": dictionary_manifest["manifest_sha256"],
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
        },
        "source_detector": {
            "path": detector_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(detector_path),
            "shape": list(detector.shape),
            "source_run_id": run_manifest["run_id"],
            "recipe_path": recipe_path.relative_to(ROOT).as_posix(),
            "recipe_id": recipe.recipe_id,
            "detector_geometry": recipe.detector.to_dict(),
        },
        "adapter": {
            "projection": "gnomonic",
            "direction_frame": "sample",
            "interpolation": "bilinear detector pixel sampling",
            "background_or_tone_processing": "none",
            "covered_direction_count": int(np.sum(sampled.covered)),
            "coverage_fraction": float(np.mean(sampled.covered)),
        },
        "ranking": {
            "metric": "masked mean-centered normalized cosine",
            "top_matches": [
                {"entry_index": match.entry_index, "score": match.score} for match in matches
            ],
            "identity_entry_index": identity_index,
            "top_entry_error_from_identity_degrees": top_error,
        },
        "claim_boundary": (
            "Self-consistency proof using a detector pattern simulated from the same Ice Ih source "
            "run; not acquired-EBSD calibration, experimental accuracy, or the full-S2 Rust matcher."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npy(staging / "detector-derived-partial-s2-values.npy", sampled.values)
        _write_npy(staging / "coverage-mask.npy", sampled.covered)
        _write_npy(staging / "pixel-coordinates-yx.npy", sampled.pixel_coordinates_yx)
        _write_json(staging / "adapter-proof.json", result)
        _write_figure(
            staging / "detector-to-s2-adapter-overview.png",
            detector=detector,
            pixels_yx=sampled.pixel_coordinates_yx,
            covered=sampled.covered,
            directions=directions,
            sampled_values=sampled.values,
            top_scores=[match.score for match in matches],
            identity_index=identity_index,
            top_index=matches[0].entry_index,
            top_error_degrees=top_error,
        )
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
        for path in sorted(staging.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        staging.rmdir()
        raise
    print(f"Detector-to-S2 proof: {output_root}")
    print(f"Covered directions: {int(np.sum(sampled.covered))}/{len(sampled.covered)}")
    print(f"Top entry: {matches[0].entry_index} score={matches[0].score:.9f}")
    print(f"Top error from identity: {top_error:.9f} degrees")


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
