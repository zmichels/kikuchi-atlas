#!/usr/bin/env python3
"""Map coarse Ice Ih candidate sensitivity to declared detector projection center."""

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

from kikuchi_lab.dictionary.detector_to_s2 import rank_masked_candidate_matrix, sample_detector_to_s2
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
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-projection-center-sensitivity-v0.1.0"
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


def _verify_offsets(value: object) -> np.ndarray:
    offsets = np.asarray(value, dtype=np.float64)
    if offsets.ndim != 1 or len(offsets) < 3 or not np.all(np.isfinite(offsets)):
        raise ValueError("offsets must be at least three finite values")
    if not np.all(np.diff(offsets) > 0.0) or not np.any(np.isclose(offsets, 0.0)):
        raise ValueError("offsets must be strictly increasing and include zero")
    return np.ascontiguousarray(offsets)


def _figure(
    path: Path,
    *,
    detector: np.ndarray,
    offsets: np.ndarray,
    scores: np.ndarray,
    errors: np.ndarray,
    coverage: np.ndarray,
    identity_entry: int,
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 12))
    figure.subplots_adjust(left=0.07, right=0.94, top=0.84, bottom=0.09, wspace=0.25, hspace=0.28)
    figure.suptitle(
        "Ice Ih: coarse dictionary sensitivity to declared projection center",
        fontsize=19,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.905,
        "One fixed simulated detector field is sampled with offset camera geometries; each cell is independently ranked against the frozen cache.",
        ha="center",
        va="center",
        fontsize=10.3,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.878,
        "This is a geometry-sensitivity map, not a calibration estimate or acquired-pattern benchmark.",
        ha="center",
        va="center",
        fontsize=9.8,
        color="#34495e",
    )
    extent = (offsets[0], offsets[-1], offsets[0], offsets[-1])

    image_axis = axes[0, 0]
    image_axis.imshow(detector, cmap="gray", interpolation="nearest")
    image_axis.set_title("fixed source detector image", fontsize=13)
    image_axis.set_axis_off()

    panels = (
        (axes[0, 1], scores, "masked top-candidate cosine", "viridis", None),
        (axes[1, 0], errors, "top-candidate error from nominal orientation (deg)", "magma_r", 0.0),
        (axes[1, 1], coverage, "covered fixed-S² directions", "cividis", None),
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
        axis.scatter((0.0,), (0.0,), marker="+", color="white", s=130, linewidths=2.0)
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
        f"Nominal identity cache entry: {identity_entry}; white cross: source-declared projection center.",
        ha="left",
        va="center",
        fontsize=9.5,
        color="#34495e",
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(
    dictionary_root: Path,
    recipe_path: Path,
    source_detector_path: Path,
    output_root: Path,
    *,
    offsets: object = _OFFSETS,
) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    source_detector_path = source_detector_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"projection-center sensitivity output already exists: {output_root}")
    values = _verify_offsets(offsets)
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache_info = manifest["candidate_cache"]
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    detector_image = np.asarray(np.load(source_detector_path, allow_pickle=False), dtype=np.float64)
    recipe = load_kinematical_recipe(recipe_path)
    if detector_image.shape != recipe.detector.supersampled_shape or not np.all(
        np.isfinite(detector_image)
    ):
        raise ValueError("source detector must be finite and match the declared detector geometry")
    identity_entry = int(np.argmax(quaternions[:, 0]))

    shape = (len(values), len(values))
    scores = np.empty(shape, dtype=np.float64)
    errors = np.empty(shape, dtype=np.float64)
    coverage = np.empty(shape, dtype=np.int32)
    top_entries = np.empty(shape, dtype=np.int32)
    records: list[dict[str, object]] = []
    for row, delta_y in enumerate(values):
        for column, delta_x in enumerate(values):
            detector = replace(
                recipe.detector,
                pcx=float(recipe.detector.pcx + delta_x),
                pcy=float(recipe.detector.pcy + delta_y),
            )
            sampled = sample_detector_to_s2(detector_image, directions, detector)
            top = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=1)[0]
            error = quaternion_misorientation_degrees(
                quaternions[identity_entry], quaternions[top.entry_index]
            )
            scores[row, column] = top.score
            errors[row, column] = error
            coverage[row, column] = int(np.sum(sampled.covered))
            top_entries[row, column] = top.entry_index
            records.append(
                {
                    "delta_pcx": float(delta_x),
                    "delta_pcy": float(delta_y),
                    "top_entry_index": top.entry_index,
                    "top_score": top.score,
                    "top_error_degrees_from_nominal": error,
                    "covered_direction_count": int(np.sum(sampled.covered)),
                }
            )
    zero = int(np.flatnonzero(np.isclose(values, 0.0))[0])
    if top_entries[zero, zero] != identity_entry:
        raise ValueError("the source-declared geometry did not recover its nominal identity entry")

    result = {
        "schema": "kikuchi.ice-ih-projection-center-sensitivity/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
            "nominal_identity_entry_index": identity_entry,
        },
        "source_detector": {
            "path": source_detector_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(source_detector_path),
            "shape": list(detector_image.shape),
        },
        "nominal_detector_geometry": recipe.detector.to_dict(),
        "perturbation": {
            "quantity": "declared detector PCx and PCy only",
            "offsets": values.tolist(),
            "pcz": "unchanged",
            "detector_image": "fixed; only the detector-to-S2 sampling geometry varies",
        },
        "metric": {
            "name": "masked mean-centered normalized cosine",
            "coverage": "recomputed for every named perturbed camera geometry",
        },
        "records": records,
        "claim_boundary": (
            "Synthetic projection-center sensitivity map for one fixed kinematical Ice Ih detector "
            "field and its source recipe. It is not a detector calibration procedure, uncertainty "
            "estimate, experimental tolerance, phase-discrimination result, or acquired-EBSD benchmark."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "projection-center-grid.npz",
            offsets=values,
            masked_top_scores=scores,
            top_orientation_errors_degrees=errors,
            covered_direction_counts=coverage,
            top_entry_indices=top_entries,
        )
        _write_json(staging / "projection-center-sensitivity.json", result)
        _figure(
            staging / "projection-center-sensitivity.png",
            detector=detector_image,
            offsets=values,
            scores=scores,
            errors=errors,
            coverage=coverage,
            identity_entry=identity_entry,
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
    print(f"Projection-center sensitivity: {output_root}")
    print(f"Nominal score: {scores[zero, zero]:.9f}")
    print(f"Maximum top-entry error across grid: {np.max(errors):.3f}°")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--source-detector", type=Path, default=DEFAULT_SOURCE_DETECTOR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        run(args.dictionary, args.recipe, args.source_detector, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
