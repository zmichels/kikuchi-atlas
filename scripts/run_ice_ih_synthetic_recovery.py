#!/usr/bin/env python3
"""Seal a reproducible held-out synthetic recovery proof for an Ice Ih dictionary."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from kikuchi_lab.dictionary.ice_ih import (
    build_candidate_matrix,
    rank_candidate_matrix,
    run_synthetic_recovery,
    verify_ice_ih_candidate_dictionary,
)
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.0"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-spherical-recovery-proof-v0.1.0"
HELD_OUT_ROTATION_VECTOR_DEGREES = (1.5, -2.0, 2.5)
LOCAL_HALF_WIDTH_DEGREES = 5.0
LOCAL_STEP_DEGREES = 1.0


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


def _plot_signal(axis: plt.Axes, directions: np.ndarray, signal: np.ndarray, title: str) -> None:
    longitude = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    latitude = np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))
    scatter = axis.scatter(longitude, latitude, c=signal, cmap="gray", s=8, linewidths=0)
    axis.set(
        title=title,
        xlim=(-180, 180),
        ylim=(-90, 90),
        xlabel="longitude (deg)",
        ylabel="latitude (deg)",
    )
    axis.set_facecolor("#101519")
    axis.grid(alpha=0.18, linewidth=0.4)
    return scatter


def _write_figure(
    path: Path,
    *,
    directions: np.ndarray,
    observed: np.ndarray,
    coarse: np.ndarray,
    refined: np.ndarray,
    recovery: dict[str, object],
    top_scores: list[float],
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    _plot_signal(axes[0, 0], directions, observed, "Held-out Ice Ih spherical signal")
    _plot_signal(axes[0, 1], directions, coarse, "Best coarse candidate")
    _plot_signal(axes[1, 0], directions, refined, "Full-master local refinement")
    score_axis = axes[1, 1]
    score_axis.barh(np.arange(len(top_scores)), top_scores, color="#9ec8e8")
    score_axis.invert_yaxis()
    score_axis.set(xlabel="normalized cosine similarity", ylabel="coarse candidate rank")
    score_axis.set_title("Fast search → local refinement")
    score_axis.grid(axis="x", alpha=0.22, linewidth=0.5)
    score_axis.text(
        0.02,
        0.03,
        "\n".join(
            (
                f"coarse error: {float(recovery['coarse_error_degrees']):.3f}°",
                f"refined error: {float(recovery['refined_error_degrees']):.3f}°",
                f"local candidates: {int(recovery['local_entry_count'])}",
            )
        ),
        transform=score_axis.transAxes,
        va="bottom",
        ha="left",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#f4f7fa", "edgecolor": "#78909c"},
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"recovery output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads(
        (dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8")
    )
    cache_info = manifest["candidate_cache"]
    master = np.load(dictionary_root / manifest["source"]["master_path"], allow_pickle=False)
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")

    started = perf_counter()
    recovery = run_synthetic_recovery(
        master,
        quaternions,
        directions,
        cache,
        held_out_rotation_vector_degrees=HELD_OUT_ROTATION_VECTOR_DEGREES,
        local_half_width_degrees=LOCAL_HALF_WIDTH_DEGREES,
        local_step_degrees=LOCAL_STEP_DEGREES,
    )
    elapsed_seconds = perf_counter() - started
    held_out = np.asarray(recovery.held_out_quaternion_wxyz, dtype=np.float64)[None, :]
    observed = build_candidate_matrix(master, held_out, directions)[0]
    top = rank_candidate_matrix(cache, observed, top_k=5)
    coarse = np.asarray(cache[recovery.coarse_entry_index], dtype=np.float32)
    refined = build_candidate_matrix(
        master,
        np.asarray(recovery.refined_quaternion_wxyz, dtype=np.float64)[None, :],
        directions,
    )[0]

    result = {
        "schema": "kikuchi.ice-ih-synthetic-recovery/v1",
        "dictionary": {
            "dictionary_id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "entry_count": verification.entry_count,
            "candidate_shape": list(cache.shape),
        },
        "held_out_rotation_vector_degrees": list(HELD_OUT_ROTATION_VECTOR_DEGREES),
        "local_refinement": {
            "half_width_degrees": LOCAL_HALF_WIDTH_DEGREES,
            "step_degrees": LOCAL_STEP_DEGREES,
        },
        "recovery": asdict(recovery),
        "top_coarse_scores": [
            {"entry_index": match.entry_index, "score": match.score} for match in top
        ],
        "elapsed_seconds": elapsed_seconds,
        "claim_boundary": "Synthetic kinematical recovery only; not acquired-EBSD accuracy or detector calibration.",
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npy(staging / "observed-held-out-spherical-signal.npy", observed)
        _write_json(staging / "recovery.json", result)
        _write_figure(
            staging / "synthetic-recovery-overview.png",
            directions=directions,
            observed=observed,
            coarse=coarse,
            refined=refined,
            recovery=result["recovery"],
            top_scores=[match.score for match in top],
        )
        files = {
            path.relative_to(staging).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(item for item in staging.rglob("*") if item.is_file())
        }
        _write_json(staging / "checksums.json", {"schema_version": 1, "files": files})
        os.replace(staging, output_root)
    except Exception:
        raise
    print(f"Recovery proof: {output_root}")
    print(f"Coarse angular error: {recovery.coarse_error_degrees:.6f} degrees")
    print(f"Refined angular error: {recovery.refined_error_degrees:.6f} degrees")
    print(f"Elapsed: {elapsed_seconds:.6f} seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        run(args.dictionary, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
