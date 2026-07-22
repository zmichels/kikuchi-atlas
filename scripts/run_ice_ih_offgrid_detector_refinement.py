#!/usr/bin/env python3
"""Prove coarse-to-refined recovery for held-out synthetic Ice Ih detector views."""

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
    local_refine_masked_candidate,
    rank_masked_candidate_matrix,
    reproject_stereographic_master_to_detector,
    sample_detector_to_s2,
)
from kikuchi_lab.dictionary.ice_ih import (
    compose_quaternions_wxyz,
    quaternion_from_rotation_vectors_degrees,
    quaternion_misorientation_degrees,
    quaternion_rotation_matrices,
    verify_ice_ih_candidate_dictionary,
)
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-offgrid-detector-refinement-v0.1.0"
_BASE_ENTRIES = np.asarray((6577, 15, 297), dtype=np.intp)
_HELD_OUT_DELTA_DEGREES = np.asarray((1.7, -1.3, 2.2), dtype=np.float64)
_LOCAL_HALF_WIDTH_DEGREES = 4.0
_LOCAL_STEP_DEGREES = 0.5


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
        np.savez_compressed(
            handle,
            **{name: np.ascontiguousarray(value) for name, value in arrays.items()},
        )
        handle.flush()
        os.fsync(handle.fileno())


def _unit_quaternions(value: object) -> np.ndarray:
    quaternions = np.asarray(value, dtype=np.float64)
    if quaternions.ndim != 2 or quaternions.shape[1] != 4 or len(quaternions) == 0:
        raise ValueError("quaternions must have non-empty shape (N, 4)")
    if not np.all(np.isfinite(quaternions)) or not np.allclose(
        np.linalg.norm(quaternions, axis=1), 1.0, rtol=0.0, atol=5.0e-13
    ):
        raise ValueError("quaternions must be finite unit wxyz values")
    return np.ascontiguousarray(quaternions)


def _held_out_orientations(quaternions: np.ndarray) -> np.ndarray:
    if np.any(_BASE_ENTRIES >= len(quaternions)):
        raise ValueError("declared base entry is not present in this dictionary")
    delta = quaternion_from_rotation_vectors_degrees(_HELD_OUT_DELTA_DEGREES.reshape(1, 3))
    values = compose_quaternions_wxyz(
        quaternions[_BASE_ENTRIES], np.repeat(delta, len(_BASE_ENTRIES), axis=0)
    )
    for quaternion in values:
        separation = np.asarray(
            [quaternion_misorientation_degrees(quaternion, candidate) for candidate in quaternions]
        )
        if float(np.min(separation)) <= 1.0e-7:
            raise ValueError("held-out orientation unexpectedly occurs in the coarse cache")
    return values


def _figure(
    path: Path,
    *,
    detector_fields: np.ndarray,
    records: list[dict[str, object]],
) -> None:
    _, rows, columns = detector_fields.shape
    vmin, vmax = np.quantile(detector_fields.reshape(-1), (0.005, 0.9985))
    figure, axes = plt.subplots(2, len(records), figsize=(5.15 * len(records), 9.5))
    figure.subplots_adjust(left=0.045, right=0.965, top=0.80, bottom=0.085, wspace=0.28, hspace=0.36)
    figure.suptitle(
        "Ice Ih: blind off-grid detector recovery with local refinement",
        fontsize=20,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.892,
        "Canonical master → declared detector → covered S² samples → coarse cache seed → local masked refinement",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.865,
        "Each truth is deliberately absent from the 13,155-entry cache. Synthetic convention proof only; not acquired EBSD validation.",
        ha="center",
        va="center",
        fontsize=9.7,
        color="#34495e",
    )
    for position, record in enumerate(records):
        image_axis = axes[0, position]
        image = image_axis.imshow(
            detector_fields[position],
            cmap="gray",
            interpolation="nearest",
            vmin=vmin,
            vmax=vmax,
        )
        image_axis.set_title(
            f"{chr(65 + position)}. held-out view near entry {record['base_entry_index']}",
            fontsize=11.5,
        )
        image_axis.set_axis_off()

        score_axis = axes[1, position]
        matches = record["coarse_top_matches"]
        scores = [float(match["score"]) for match in matches]
        labels = [str(match["entry_index"]) for match in matches]
        score_axis.barh(
            np.arange(1, len(matches) + 1),
            scores,
            color=["#3e9c8d", *["#aebfc9"] * (len(matches) - 1)],
        )
        score_axis.set(
            title="coarse cache ranking",
            xlabel="masked normalized cosine",
            xlim=(min(0.35, min(scores) - 0.05), 1.01),
            yticks=np.arange(1, len(matches) + 1),
            yticklabels=labels,
            ylabel="entry index (ranked)",
        )
        score_axis.invert_yaxis()
        score_axis.grid(axis="x", alpha=0.22, linewidth=0.5)
        score_axis.text(
            0.03,
            0.04,
            "coarse error: "
            f"{float(record['coarse_error_degrees']):.3f}°\n"
            "refined error: "
            f"{float(record['refined_error_degrees']):.3f}°\n"
            f"local score: {float(record['refined_score']):.6f}",
            transform=score_axis.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.2,
            bbox={"boxstyle": "round,pad=0.38", "facecolor": "white", "edgecolor": "#78909c"},
        )
    colorbar = figure.colorbar(image, ax=axes[0, :], fraction=0.024, pad=0.018)
    colorbar.set_label("raw reprojected kinematical intensity", fontsize=9)
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, recipe_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"off-grid refinement output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache_info = manifest["candidate_cache"]
    master_path = dictionary_root / manifest["source"]["master_path"]
    master = np.load(master_path, allow_pickle=False)
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = _unit_quaternions(
        np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    )
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    recipe = load_kinematical_recipe(recipe_path)
    truths = _held_out_orientations(quaternions)

    detector_fields: list[np.ndarray] = []
    partial_signals: list[np.ndarray] = []
    records: list[dict[str, object]] = []
    coverage: np.ndarray | None = None
    for base_index, truth, rotation in zip(
        _BASE_ENTRIES,
        truths,
        quaternion_rotation_matrices(truths),
        strict=True,
    ):
        detector = reproject_stereographic_master_to_detector(
            master,
            recipe.detector,
            crystal_to_sample_matrix=rotation,
        )
        sampled = sample_detector_to_s2(detector, directions, recipe.detector)
        if coverage is None:
            coverage = sampled.covered
        elif not np.array_equal(coverage, sampled.covered):
            raise ValueError("one named detector geometry must have one stable coverage mask")
        coarse = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=5)
        refined = local_refine_masked_candidate(
            master,
            quaternions[coarse[0].entry_index],
            directions,
            sampled.values,
            sampled.covered,
            half_width_degrees=_LOCAL_HALF_WIDTH_DEGREES,
            step_degrees=_LOCAL_STEP_DEGREES,
        )
        coarse_error = quaternion_misorientation_degrees(
            truth, quaternions[coarse[0].entry_index]
        )
        refined_error = quaternion_misorientation_degrees(truth, refined.quaternion_wxyz)
        if not refined_error < coarse_error:
            raise ValueError("masked local refinement did not improve the held-out result")
        detector_fields.append(detector.astype(np.float32))
        partial_signals.append(sampled.values.astype(np.float32))
        records.append(
            {
                "base_entry_index": int(base_index),
                "held_out_quaternion_wxyz": truth.tolist(),
                "coarse_top_matches": [
                    {"entry_index": match.entry_index, "score": match.score} for match in coarse
                ],
                "coarse_error_degrees": coarse_error,
                "refined_quaternion_wxyz": list(refined.quaternion_wxyz),
                "refined_score": refined.score,
                "refined_error_degrees": refined_error,
                "local_entry_count": refined.local_entry_count,
            }
        )
    if coverage is None:
        raise ValueError("no held-out detector fields were generated")

    result = {
        "schema": "kikuchi.ice-ih-offgrid-detector-refinement/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "master_path": master_path.relative_to(ROOT).as_posix(),
            "master_file_sha256": _sha256(master_path),
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
        },
        "detector_geometry": recipe.detector.to_dict(),
        "held_out_orientation_construction": {
            "base_entry_indices": _BASE_ENTRIES.tolist(),
            "active_right_handed_rotation_vector_degrees": _HELD_OUT_DELTA_DEGREES.tolist(),
            "cache_exclusion": "each composed truth is confirmed absent from the fixed coarse cache",
        },
        "adapter": {
            "detector_projection": "gnomonic",
            "master_sampling": "bilinear upper/lower stereographic sampling",
            "detector_sampling": "bilinear detector pixel sampling onto fixed sample-frame S2 directions",
            "covered_direction_count": int(np.sum(coverage)),
            "metric": "masked mean-centered normalized cosine",
            "local_refinement": {
                "half_width_degrees": _LOCAL_HALF_WIDTH_DEGREES,
                "step_degrees": _LOCAL_STEP_DEGREES,
            },
        },
        "recoveries": records,
        "claim_boundary": (
            "Held-out synthetic detector convention proof: every truth is deliberately absent from "
            "the fixed coarse cache but is still reprojected from the same canonical Ice Ih master. "
            "It is not acquired-EBSD validation, independent simulation validation, detector "
            "calibration, phase discrimination, or experimental indexing-accuracy evidence."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "synthetic-detector-fields.npz",
            detector_fields=np.stack(detector_fields),
            base_entry_indices=_BASE_ENTRIES.astype(np.int32),
            held_out_quaternions_wxyz=truths,
        )
        _write_npz(
            staging / "detector-derived-partial-s2-signals.npz",
            partial_s2_signals=np.stack(partial_signals),
            coverage_mask=coverage,
        )
        _write_json(staging / "offgrid-detector-refinement.json", result)
        _figure(
            staging / "offgrid-detector-refinement.png",
            detector_fields=np.stack(detector_fields),
            records=records,
        )
        _write_json(
            staging / "checksums.json",
            {
                "schema_version": 1,
                "files": {
                    item.relative_to(staging).as_posix(): {
                        "bytes": item.stat().st_size,
                        "sha256": _sha256(item),
                    }
                    for item in sorted(path for path in staging.rglob("*") if path.is_file())
                },
            },
        )
        os.replace(staging, output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"Off-grid detector refinement: {output_root}")
    print(f"Covered directions: {int(np.sum(coverage))}/{len(coverage)}")
    for record in records:
        print(
            f"base {record['base_entry_index']}: "
            f"{float(record['coarse_error_degrees']):.3f}° → "
            f"{float(record['refined_error_degrees']):.3f}°"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        run(args.dictionary, args.recipe, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
