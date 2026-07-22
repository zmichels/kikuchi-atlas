#!/usr/bin/env python3
"""Visualize named synthetic photometric stress cases for the Ice Ih cache."""

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
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-photometric-stress-v0.1.0"


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


def _finite_image(value: object) -> np.ndarray:
    image = np.asarray(value, dtype=np.float64)
    if image.ndim != 2 or not image.size or not np.all(np.isfinite(image)):
        raise ValueError("image must be a non-empty finite two-dimensional array")
    if float(np.std(image)) <= np.finfo(np.float64).eps:
        raise ValueError("image must have non-zero contrast")
    return np.ascontiguousarray(image)


def stress_cases(image: object) -> tuple[tuple[str, dict[str, object], np.ndarray], ...]:
    """Return explicit, deterministic stress inputs; this is not preprocessing."""
    source = _finite_image(image)
    mean = float(np.mean(source))
    contrast = float(np.std(source))
    rows, columns = source.shape
    row_ramp = np.linspace(-1.0, 1.0, rows, dtype=np.float64)[:, None]
    column_ramp = np.linspace(-1.0, 1.0, columns, dtype=np.float64)[None, :]
    rng = np.random.default_rng(20_260_722)
    saturation = float(np.quantile(source, 0.92))
    cases = (
        ("identity", {"transform": "none"}, source),
        (
            "affine-contrast",
            {"transform": "mean + 1.6 * (image - mean)", "gain": 1.6},
            mean + 1.6 * (source - mean),
        ),
        (
            "row-illumination-ramp",
            {"transform": "image + 0.8 * standard_deviation * row_ramp", "amplitude_sd": 0.8},
            source + 0.8 * contrast * row_ramp,
        ),
        (
            "column-illumination-ramp",
            {"transform": "image + 0.8 * standard_deviation * column_ramp", "amplitude_sd": 0.8},
            source + 0.8 * contrast * column_ramp,
        ),
        (
            "upper-saturation",
            {"transform": "minimum(image, 92nd-percentile source intensity)", "percentile": 92.0},
            np.minimum(source, saturation),
        ),
        (
            "additive-noise",
            {
                "transform": "image + seeded Gaussian noise",
                "seed": 20_260_722,
                "standard_deviation_sd": 0.35,
            },
            source + rng.normal(scale=0.35 * contrast, size=source.shape),
        ),
    )
    if any(not np.all(np.isfinite(case[2])) for case in cases):
        raise ValueError("stress case produced non-finite detector intensity")
    return tuple((name, parameters, np.ascontiguousarray(values)) for name, parameters, values in cases)


def _figure(
    path: Path,
    *,
    fields: np.ndarray,
    records: list[dict[str, object]],
) -> None:
    lower, upper = np.quantile(fields.reshape(-1), (0.004, 0.998))
    figure, axes = plt.subplots(2, 3, figsize=(16, 10))
    figure.subplots_adjust(left=0.035, right=0.94, top=0.82, bottom=0.07, wspace=0.10, hspace=0.22)
    figure.suptitle(
        "Ice Ih: named synthetic photometric stress against the frozen coarse cache",
        fontsize=19,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.89,
        "Each panel is a deliberately declared test input, sampled through unchanged geometry and ranked with the same coverage-specific metric.",
        ha="center",
        va="center",
        fontsize=10.2,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.865,
        "These are not recommended preprocessing steps or detector-response models; they are transparent stress probes.",
        ha="center",
        va="center",
        fontsize=9.7,
        color="#34495e",
    )
    for axis, field, record in zip(axes.reshape(-1), fields, records, strict=True):
        image = axis.imshow(
            field,
            cmap="gray",
            interpolation="nearest",
            vmin=lower,
            vmax=upper,
        )
        axis.set_title(
            f"{record['name']}\nentry {record['top_entry_index']} · "
            f"score {float(record['top_score']):.4f} · "
            f"error {float(record['top_error_degrees']):.2f}°",
            fontsize=10.2,
        )
        axis.set_axis_off()
    colorbar = figure.colorbar(image, ax=axes, fraction=0.020, pad=0.012)
    colorbar.set_label("synthetic detector intensity", fontsize=9)
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, recipe_path: Path, detector_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    detector_path = detector_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"photometric stress output already exists: {output_root}")
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache_info = manifest["candidate_cache"]
    directions = np.load(dictionary_root / cache_info["directions_path"], allow_pickle=False)
    quaternions = np.load(dictionary_root / cache_info["quaternions_path"], allow_pickle=False)
    cache = np.load(dictionary_root / cache_info["path"], allow_pickle=False, mmap_mode="r")
    source = _finite_image(np.load(detector_path, allow_pickle=False))
    recipe = load_kinematical_recipe(recipe_path)
    if source.shape != recipe.detector.supersampled_shape:
        raise ValueError("source detector shape does not match the declared detector recipe")
    identity_entry = int(np.argmax(quaternions[:, 0]))
    fields: list[np.ndarray] = []
    partial_signals: list[np.ndarray] = []
    records: list[dict[str, object]] = []
    coverage: np.ndarray | None = None
    for name, parameters, field in stress_cases(source):
        sampled = sample_detector_to_s2(field, directions, recipe.detector)
        if coverage is None:
            coverage = sampled.covered
        elif not np.array_equal(coverage, sampled.covered):
            raise ValueError("fixed geometry must preserve a stable coverage mask")
        top = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=3)
        fields.append(field.astype(np.float32))
        partial_signals.append(sampled.values.astype(np.float32))
        records.append(
            {
                "name": name,
                "parameters": parameters,
                "top_entry_index": top[0].entry_index,
                "top_score": top[0].score,
                "top_error_degrees": quaternion_misorientation_degrees(
                    quaternions[identity_entry], quaternions[top[0].entry_index]
                ),
                "top_matches": [
                    {"entry_index": match.entry_index, "score": match.score} for match in top
                ],
            }
        )
    if coverage is None:
        raise ValueError("no stress fields were generated")
    result = {
        "schema": "kikuchi.ice-ih-photometric-stress/v1",
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
            "shape": list(source.shape),
        },
        "detector_geometry": recipe.detector.to_dict(),
        "coverage": {"covered_direction_count": int(np.sum(coverage))},
        "stress_cases": records,
        "claim_boundary": (
            "These deterministic image transforms are synthetic stress inputs, not recommended "
            "preprocessing, a detector-response model, acquired-pattern validation, or an "
            "experimental robustness benchmark."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "synthetic-stress-detector-fields.npz",
            fields=np.stack(fields),
            names=np.asarray([record["name"] for record in records]),
        )
        _write_npz(
            staging / "detector-derived-partial-s2-signals.npz",
            partial_s2_signals=np.stack(partial_signals),
            coverage_mask=coverage,
        )
        _write_json(staging / "photometric-stress.json", result)
        _figure(staging / "photometric-stress.png", fields=np.stack(fields), records=records)
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
    print(f"Photometric stress: {output_root}")
    for record in records:
        print(
            f"{record['name']}: entry {record['top_entry_index']} "
            f"score {float(record['top_score']):.6f} "
            f"error {float(record['top_error_degrees']):.3f}°"
        )


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
