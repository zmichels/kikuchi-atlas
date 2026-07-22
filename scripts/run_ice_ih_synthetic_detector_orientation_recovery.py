#!/usr/bin/env python3
"""Seal orientation-varied synthetic Ice Ih detector recovery evidence."""

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

from kikuchi_lab.dictionary.detector_to_s2 import (
    rank_masked_candidate_matrix,
    reproject_stereographic_master_to_detector,
    sample_detector_to_s2,
)
from kikuchi_lab.dictionary.ice_ih import (
    quaternion_misorientation_degrees,
    quaternion_rotation_matrices,
    verify_ice_ih_candidate_dictionary,
)
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-synthetic-detector-orientation-recovery-v0.1.0"


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


def _write_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.savez_compressed(handle, **{name: np.ascontiguousarray(value) for name, value in arrays.items()})
        handle.flush()
        os.fsync(handle.fileno())


def _unit_quaternions_wxyz(value: object) -> np.ndarray:
    quaternions = np.asarray(value, dtype=np.float64)
    if quaternions.ndim != 2 or quaternions.shape[1] != 4 or len(quaternions) == 0:
        raise ValueError("quaternions must be a non-empty (N, 4) array")
    if not np.all(np.isfinite(quaternions)):
        raise ValueError("quaternions must be finite")
    norms = np.linalg.norm(quaternions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=5.0e-13):
        raise ValueError("quaternions must be unit length")
    return np.ascontiguousarray(quaternions)


def _select_spread_entries(quaternions: object, *, count: int) -> np.ndarray:
    """Select a deterministic, separated subset of a sign-canonical SO(3) grid."""
    values = _unit_quaternions_wxyz(quaternions)
    if type(count) is not int or not 1 <= count <= len(values):
        raise ValueError("count must be a positive integer no greater than entry count")
    selected = [int(np.argmax(values[:, 0]))]
    while len(selected) < count:
        dots = np.abs(values @ values[selected].T)
        separation = np.degrees(2.0 * np.arccos(np.clip(dots, -1.0, 1.0)))
        nearest = np.min(separation, axis=1)
        nearest[selected] = -np.inf
        selected.append(int(np.argmax(nearest)))
    return np.asarray(selected, dtype=np.intp)


def _figure(
    path: Path,
    *,
    detector_fields: np.ndarray,
    records: list[dict[str, object]],
) -> None:
    _, rows, columns = detector_fields.shape
    value_min, value_max = np.quantile(detector_fields.reshape(-1), (0.005, 0.9985))
    figure, axes = plt.subplots(2, len(records), figsize=(5.0 * len(records), 9.5))
    figure.subplots_adjust(left=0.035, right=0.965, top=0.82, bottom=0.07, wspace=0.23, hspace=0.31)
    figure.suptitle(
        "Ice Ih: orientation-varied synthetic detector recovery",
        fontsize=20,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.89,
        "Canonical master → declared detector geometry → covered S² samples → cached candidate ranking",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.865,
        "Synthetic convention proof only: each input is reprojected from the same canonical master, not acquired EBSD.",
        ha="center",
        va="center",
        fontsize=10.0,
        color="#34495e",
    )
    for position, record in enumerate(records):
        image_axis = axes[0, position]
        image = image_axis.imshow(
            detector_fields[position],
            cmap="gray",
            interpolation="nearest",
            vmin=value_min,
            vmax=value_max,
        )
        image_axis.set_title(
            f"{chr(65 + position)}. target entry {record['target_entry_index']}",
            fontsize=12,
        )
        image_axis.set_axis_off()
        rank_axis = axes[1, position]
        matches = record["top_matches"]
        scores = [float(match["score"]) for match in matches]
        entry_ids = [str(match["entry_index"]) for match in matches]
        colors = [
            "#3e9c8d" if match["entry_index"] == record["target_entry_index"] else "#9db0bc"
            for match in matches
        ]
        ranks = np.arange(1, len(matches) + 1)
        rank_axis.barh(ranks, scores, color=colors)
        rank_axis.set(
            title=f"ranked covered-S² candidates\ntop error {float(record['top_error_degrees']):.3f}°",
            xlabel="masked normalized cosine",
            xlim=(min(0.35, min(scores) - 0.05), 1.01),
            yticks=ranks,
            yticklabels=entry_ids,
            ylabel="entry index (ranked)",
        )
        rank_axis.invert_yaxis()
        rank_axis.grid(axis="x", alpha=0.22, linewidth=0.5)
        rank_axis.text(
            0.04,
            0.04,
            f"target top: {record['target_is_top']}\nscore: {scores[0]:.6f}",
            transform=rank_axis.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.5,
            bbox={"boxstyle": "round,pad=0.38", "facecolor": "white", "edgecolor": "#78909c"},
        )
    colorbar = figure.colorbar(image, ax=axes[0, :], fraction=0.024, pad=0.018)
    colorbar.set_label("raw reprojected kinematical intensity", fontsize=9)
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, recipe_path: Path, output_root: Path, *, orientation_count: int) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"synthetic recovery output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache_info = manifest["candidate_cache"]
    master_path = dictionary_root / manifest["source"]["master_path"]
    master = np.load(master_path, allow_pickle=False)
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = _unit_quaternions_wxyz(
        np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    )
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    recipe = load_kinematical_recipe(recipe_path)
    selected = _select_spread_entries(quaternions, count=orientation_count)
    rotations = quaternion_rotation_matrices(quaternions[selected])
    detector_fields: list[np.ndarray] = []
    partial_signals: list[np.ndarray] = []
    records: list[dict[str, object]] = []
    coverage: np.ndarray | None = None
    for entry_index, rotation in zip(selected, rotations, strict=True):
        detector = reproject_stereographic_master_to_detector(
            master,
            recipe.detector,
            crystal_to_sample_matrix=rotation,
        )
        sampled = sample_detector_to_s2(detector, directions, recipe.detector)
        if coverage is None:
            coverage = sampled.covered
        elif not np.array_equal(coverage, sampled.covered):
            raise ValueError("one declared detector geometry must yield a stable coverage mask")
        matches = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=5)
        top = matches[0]
        detector_fields.append(detector.astype(np.float32))
        partial_signals.append(sampled.values.astype(np.float32))
        records.append(
            {
                "target_entry_index": int(entry_index),
                "target_quaternion_wxyz": quaternions[entry_index].tolist(),
                "top_matches": [
                    {"entry_index": match.entry_index, "score": match.score} for match in matches
                ],
                "target_is_top": bool(top.entry_index == entry_index),
                "top_error_degrees": quaternion_misorientation_degrees(
                    quaternions[entry_index], quaternions[top.entry_index]
                ),
            }
        )
    if coverage is None:
        raise ValueError("no synthetic orientation was selected")
    detector_stack = np.stack(detector_fields)
    signal_stack = np.stack(partial_signals)
    if not all(bool(record["target_is_top"]) for record in records):
        raise ValueError("synthetic detector recovery failed to return every target entry first")
    result = {
        "schema": "kikuchi.ice-ih-synthetic-detector-orientation-recovery/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "master_path": master_path.relative_to(ROOT).as_posix(),
            "master_file_sha256": _sha256(master_path),
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
        },
        "detector_geometry": recipe.detector.to_dict(),
        "orientation_selection": {
            "method": "greedy maximum minimum sign-invariant quaternion separation",
            "count": int(len(selected)),
            "entry_indices": selected.tolist(),
        },
        "adapter": {
            "detector_projection": "gnomonic",
            "master_sampling": "bilinear upper/lower stereographic sampling",
            "detector_sampling": "bilinear detector pixel sampling onto fixed sample-frame S2 directions",
            "covered_direction_count": int(np.sum(coverage)),
            "metric": "masked mean-centered normalized cosine",
        },
        "recoveries": records,
        "claim_boundary": (
            "End-to-end synthetic convention proof: every detector field is reprojected from the "
            "same canonical Ice Ih master used to build the cache. It is not acquired-EBSD "
            "validation, independent simulation validation, calibration, or indexing accuracy evidence."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "synthetic-detector-fields.npz",
            detector_fields=detector_stack,
            target_entry_indices=selected.astype(np.int32),
            target_quaternions_wxyz=quaternions[selected].astype(np.float64),
        )
        _write_npz(
            staging / "detector-derived-partial-s2-signals.npz",
            partial_s2_signals=signal_stack,
            coverage_mask=coverage,
        )
        _write_json(staging / "synthetic-detector-recovery.json", result)
        _figure(
            staging / "synthetic-detector-orientation-recovery.png",
            detector_fields=detector_stack,
            records=records,
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
    print(f"Synthetic detector recovery: {output_root}")
    print(f"Selected entries: {', '.join(str(index) for index in selected)}")
    print(f"Covered directions: {int(np.sum(coverage))}/{len(coverage)}")
    print("All targets recovered first: yes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--orientation-count", type=int, default=4)
    args = parser.parse_args(argv)
    try:
        run(
            args.dictionary,
            args.recipe,
            args.output,
            orientation_count=args.orientation_count,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
