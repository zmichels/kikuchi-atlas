#!/usr/bin/env python3
"""Recover the source projection center from a finite shared-mask candidate grid."""

from __future__ import annotations

import argparse
from dataclasses import replace
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

from kikuchi_lab.dictionary.geometry_search import rank_detector_geometry_candidates
from kikuchi_lab.dictionary.ice_ih import (
    quaternion_misorientation_degrees,
    verify_ice_ih_candidate_dictionary,
)
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.model.identity import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_SOURCE_DETECTOR = (
    ROOT
    / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
    / "products/kinematical-detector.npy"
)
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-projection-center-cosearch-v0.1.0"
_OFFSETS = np.linspace(-0.08, 0.08, 9, dtype=np.float64)


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


def _figure(
    path: Path,
    *,
    detector: np.ndarray,
    offsets: np.ndarray,
    scores: np.ndarray,
    errors: np.ndarray,
    native_coverage: np.ndarray,
    common_coverage_count: int,
    best_offset_x: float,
    best_offset_y: float,
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 12))
    figure.subplots_adjust(left=0.07, right=0.94, top=0.84, bottom=0.09, wspace=0.25, hspace=0.28)
    figure.suptitle(
        "Ice Ih: finite projection-center co-search on one shared S² mask",
        fontsize=19,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.905,
        f"Every PC candidate is scored on the same {common_coverage_count} directions; candidate-native coverage is retained separately.",
        ha="center",
        va="center",
        fontsize=10.3,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.878,
        "Finite-grid synthetic convention proof only: not continuous calibration or acquired-pattern geometry fitting.",
        ha="center",
        va="center",
        fontsize=9.8,
        color="#34495e",
    )
    extent = (offsets[0], offsets[-1], offsets[0], offsets[-1])
    axes[0, 0].imshow(detector, cmap="gray", interpolation="nearest")
    axes[0, 0].set_title("fixed source detector image", fontsize=13)
    axes[0, 0].set_axis_off()
    panels = (
        (axes[0, 1], scores, "comparable top-candidate cosine", "viridis", None),
        (axes[1, 0], errors, "top-candidate error from nominal orientation (deg)", "magma_r", 0.0),
        (axes[1, 1], native_coverage, "candidate-native covered S² directions", "cividis", None),
    )
    for axis, values, title, cmap, minimum in panels:
        image = axis.imshow(
            values,
            origin="lower",
            extent=extent,
            aspect="equal",
            interpolation="nearest",
            cmap=cmap,
            vmin=minimum,
        )
        axis.contour(
            offsets,
            offsets,
            values,
            colors="white",
            linewidths=0.55,
            alpha=0.58,
        )
        axis.scatter(
            (best_offset_x,),
            (best_offset_y,),
            marker="*",
            color="white",
            edgecolor="#10232c",
            s=190,
            linewidths=0.65,
            zorder=3,
        )
        axis.set(
            title=title,
            xlabel="delta PCx (declared units)",
            ylabel="delta PCy (declared units)",
        )
        colorbar = figure.colorbar(image, ax=axis, fraction=0.047, pad=0.04)
        colorbar.ax.tick_params(labelsize=8.5)
    figure.text(
        0.07,
        0.025,
        "White star: best finite candidate. Shared-mask score makes this finite candidate comparison meaningful.",
        ha="left",
        va="center",
        fontsize=9.5,
        color="#34495e",
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, recipe_path: Path, detector_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    detector_path = detector_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"projection-center co-search output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache_info = manifest["candidate_cache"]
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    detector_image = np.asarray(np.load(detector_path, allow_pickle=False), dtype=np.float64)
    recipe = load_kinematical_recipe(recipe_path)
    if detector_image.shape != recipe.detector.supersampled_shape or not np.all(
        np.isfinite(detector_image)
    ):
        raise ValueError("source detector must be finite and match the declared detector recipe")
    identity_entry = int(np.argmax(quaternions[:, 0]))
    detectors = tuple(
        replace(
            recipe.detector,
            pcx=float(recipe.detector.pcx + delta_x),
            pcy=float(recipe.detector.pcy + delta_y),
        )
        for delta_y in _OFFSETS
        for delta_x in _OFFSETS
    )
    result = rank_detector_geometry_candidates(
        detector_image,
        directions,
        cache,
        detectors,
        top_k=3,
    )
    rows = len(_OFFSETS)
    scores = np.empty((rows, rows), dtype=np.float64)
    errors = np.empty((rows, rows), dtype=np.float64)
    native_coverage = np.empty((rows, rows), dtype=np.int32)
    top_entries = np.empty((rows, rows), dtype=np.int32)
    records: list[dict[str, object]] = []
    for candidate in result.candidates:
        row, column = divmod(candidate.candidate_index, rows)
        delta_x = float(_OFFSETS[column])
        delta_y = float(_OFFSETS[row])
        error = quaternion_misorientation_degrees(
            quaternions[identity_entry], quaternions[candidate.matches[0].entry_index]
        )
        scores[row, column] = candidate.score
        errors[row, column] = error
        native_coverage[row, column] = candidate.covered_direction_count
        top_entries[row, column] = candidate.matches[0].entry_index
        records.append(
            {
                "candidate_index": candidate.candidate_index,
                "delta_pcx": delta_x,
                "delta_pcy": delta_y,
                "top_entry_index": candidate.matches[0].entry_index,
                "top_score": candidate.score,
                "top_error_degrees_from_nominal": error,
                "candidate_native_covered_direction_count": candidate.covered_direction_count,
                "top_matches": [
                    {"entry_index": match.entry_index, "score": match.score}
                    for match in candidate.matches
                ],
            }
        )
    best = result.best
    best_row, best_column = divmod(best.candidate_index, rows)
    best_offset_x = float(_OFFSETS[best_column])
    best_offset_y = float(_OFFSETS[best_row])
    if best_offset_x != 0.0 or best_offset_y != 0.0:
        raise ValueError("finite shared-mask co-search did not recover the source projection center")
    if best.matches[0].entry_index != identity_entry:
        raise ValueError("finite shared-mask co-search did not recover the nominal identity entry")
    payload = {
        "schema": "kikuchi.ice-ih-projection-center-cosearch/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
            "nominal_identity_entry_index": identity_entry,
        },
        "source_detector": {
            "path": detector_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(detector_path),
            "shape": list(detector_image.shape),
        },
        "nominal_detector_geometry": recipe.detector.to_dict(),
        "candidate_grid": {
            "quantity": "PCx and PCy only",
            "offsets": _OFFSETS.tolist(),
            "candidate_count": len(detectors),
            "pcz": "unchanged",
            "score_comparability": "all candidates use the intersection of their detector-to-S2 coverage masks",
            "common_covered_direction_count": int(np.sum(result.common_coverage)),
        },
        "best_candidate": {
            "candidate_index": best.candidate_index,
            "delta_pcx": best_offset_x,
            "delta_pcy": best_offset_y,
            "top_entry_index": best.matches[0].entry_index,
            "top_score": best.score,
        },
        "records": sorted(records, key=lambda record: int(record["candidate_index"])),
        "claim_boundary": (
            "Finite shared-mask geometry candidate proof using one source-bound simulated Ice Ih "
            "detector field. It is not continuous projection-center fitting, detector calibration, "
            "uncertainty estimation, acquired-pattern validation, or a performance benchmark."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "projection-center-cosearch-grid.npz",
            offsets=_OFFSETS,
            comparable_top_scores=scores,
            top_orientation_errors_degrees=errors,
            candidate_native_coverage_counts=native_coverage,
            top_entry_indices=top_entries,
            common_coverage_mask=result.common_coverage,
        )
        _write_json(staging / "projection-center-cosearch.json", payload)
        _figure(
            staging / "projection-center-cosearch.png",
            detector=detector_image,
            offsets=_OFFSETS,
            scores=scores,
            errors=errors,
            native_coverage=native_coverage,
            common_coverage_count=int(np.sum(result.common_coverage)),
            best_offset_x=best_offset_x,
            best_offset_y=best_offset_y,
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
    print(f"Projection-center co-search: {output_root}")
    print(f"Shared coverage: {int(np.sum(result.common_coverage))}/{len(directions)}")
    print(f"Best PC offsets: ({best_offset_x:+.3f}, {best_offset_y:+.3f})")
    print(f"Best score: {best.score:.9f}; entry: {best.matches[0].entry_index}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--detector", type=Path, default=DEFAULT_SOURCE_DETECTOR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        run(args.dictionary, args.recipe, args.detector, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
