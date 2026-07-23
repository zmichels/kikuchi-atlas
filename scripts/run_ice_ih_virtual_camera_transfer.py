#!/usr/bin/env python3
"""Prove Ice Ih recovery through several declared virtual camera geometries."""

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

from kikuchi_lab.dictionary.detector_profiles import ice_ih_virtual_camera_profiles
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
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-virtual-camera-transfer-v0.1.2"


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


def _unit_quaternions_wxyz(value: object) -> np.ndarray:
    quaternions = np.asarray(value, dtype=np.float64)
    if quaternions.ndim != 2 or quaternions.shape[1] != 4 or len(quaternions) < 2:
        raise ValueError("quaternions must contain at least two finite (N, 4) values")
    if not np.all(np.isfinite(quaternions)):
        raise ValueError("quaternions must be finite")
    if not np.allclose(np.linalg.norm(quaternions, axis=1), 1.0, rtol=0.0, atol=5.0e-13):
        raise ValueError("quaternions must be unit length")
    return np.ascontiguousarray(quaternions)


def _select_target_entries(quaternions: object) -> np.ndarray:
    """Select identity and its most separated sign-invariant cache orientation."""
    values = _unit_quaternions_wxyz(quaternions)
    identity = int(np.argmax(values[:, 0]))
    separations = np.degrees(
        2.0 * np.arccos(np.clip(np.abs(values @ values[identity]), -1.0, 1.0))
    )
    separations[identity] = -np.inf
    return np.asarray((identity, int(np.argmax(separations))), dtype=np.intp)


def _s2_coordinates(directions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    longitude = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    latitude = np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))
    return longitude, latitude


def _figure(
    path: Path,
    *,
    directions: np.ndarray,
    detector_fields: np.ndarray,
    profile_records: list[dict[str, object]],
) -> None:
    profile_count, orientation_count, _, _ = detector_fields.shape
    if profile_count != len(profile_records) or orientation_count != 2:
        raise ValueError("figure expects two target fields for every virtual camera profile")
    lower, upper = np.quantile(detector_fields.reshape(-1), (0.005, 0.9985))
    longitude, latitude = _s2_coordinates(directions)
    figure, axes = plt.subplots(profile_count, 3, figsize=(16, 4.65 * profile_count))
    figure.subplots_adjust(left=0.055, right=0.975, top=0.80, bottom=0.06, wspace=0.22, hspace=0.31)
    figure.text(
        0.5,
        0.982,
        "Ice Ih: virtual-camera transfer through declared detector geometries",
        ha="center",
        va="top",
        fontsize=20,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.952,
        "Each detector field is generated, sampled, and ranked with its own named geometry; covered-S² scores are only interpreted within that profile.",
        ha="center",
        va="center",
        fontsize=10.2,
        color="#34495e",
    )
    figure.text(
        0.5,
        0.929,
        "Virtual geometry transfer proof only: not a commercial-camera model, detector calibration, or acquired-pattern benchmark.",
        ha="center",
        va="center",
        fontsize=9.7,
        color="#34495e",
    )
    for row, record in enumerate(profile_records):
        profile = record["profile"]
        assert isinstance(profile, dict)
        recoveries = record["recoveries"]
        assert isinstance(recoveries, list)
        for column, recovery in enumerate(recoveries):
            assert isinstance(recovery, dict)
            axis = axes[row, column]
            axis.imshow(
                detector_fields[row, column],
                cmap="gray",
                interpolation="nearest",
                vmin=lower,
                vmax=upper,
            )
            axis.set_title(
                f"{profile['label']}\ntarget {recovery['target_entry_index']} → top {recovery['top_entry_index']}  ·  {float(recovery['top_score']):.6f}",
                fontsize=10.4,
            )
            axis.set_axis_off()
        coverage = np.asarray(record["coverage_mask"], dtype=bool)
        coverage_axis = axes[row, 2]
        coverage_axis.scatter(longitude, latitude, s=5, color="#c7d2d9", alpha=0.38, linewidths=0)
        coverage_axis.scatter(
            longitude[coverage],
            latitude[coverage],
            s=8,
            color="#0f786f",
            alpha=0.95,
            linewidths=0,
        )
        coverage_axis.set(
            xlim=(-180, 180),
            ylim=(-90, 90),
            xlabel="sample-frame longitude (deg)",
            ylabel="sample-frame latitude (deg)",
            title=f"fixed S² coverage: {int(np.sum(coverage))}/{len(coverage)} directions",
        )
        coverage_axis.grid(alpha=0.22, linewidth=0.5)
        coverage_axis.text(
            0.02,
            0.04,
            f"PCz {float(profile['detector_geometry']['pc']['z']):.2f}\nboth targets recovered first: {record['all_targets_recovered_first']}",
            transform=coverage_axis.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.3,
            bbox={"boxstyle": "round,pad=0.38", "facecolor": "white", "edgecolor": "#78909c"},
        )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(dictionary_root: Path, recipe_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"virtual-camera transfer output already exists: {output_root}")
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
    profiles = ice_ih_virtual_camera_profiles(recipe.detector)
    targets = _select_target_entries(quaternions)
    rotations = quaternion_rotation_matrices(quaternions[targets])
    detector_fields: list[np.ndarray] = []
    partial_signals: list[np.ndarray] = []
    profile_records: list[dict[str, object]] = []
    for profile in profiles:
        fields: list[np.ndarray] = []
        signals: list[np.ndarray] = []
        recoveries: list[dict[str, object]] = []
        coverage: np.ndarray | None = None
        for entry_index, rotation in zip(targets, rotations, strict=True):
            detector_field = reproject_stereographic_master_to_detector(
                master,
                profile.detector,
                crystal_to_sample_matrix=rotation,
            )
            sampled = sample_detector_to_s2(detector_field, directions, profile.detector)
            if coverage is None:
                coverage = sampled.covered
            elif not np.array_equal(coverage, sampled.covered):
                raise ValueError("one declared detector profile must yield one stable coverage mask")
            matches = rank_masked_candidate_matrix(cache, sampled.values, sampled.covered, top_k=3)
            top = matches[0]
            fields.append(detector_field.astype(np.float32))
            signals.append(sampled.values.astype(np.float32))
            recoveries.append(
                {
                    "target_entry_index": int(entry_index),
                    "target_quaternion_wxyz": quaternions[entry_index].tolist(),
                    "top_entry_index": top.entry_index,
                    "top_score": top.score,
                    "target_is_top": bool(top.entry_index == entry_index),
                    "top_error_degrees": quaternion_misorientation_degrees(
                        quaternions[entry_index], quaternions[top.entry_index]
                    ),
                    "top_matches": [
                        {"entry_index": match.entry_index, "score": match.score} for match in matches
                    ],
                }
            )
        if coverage is None:
            raise ValueError("virtual detector profile has no target fields")
        if not all(bool(recovery["target_is_top"]) for recovery in recoveries):
            raise ValueError(f"virtual detector profile {profile.name} did not recover every target first")
        detector_fields.append(np.stack(fields))
        partial_signals.append(np.stack(signals))
        profile_records.append(
            {
                "profile": profile.to_dict(),
                "coverage_mask": coverage,
                "covered_direction_count": int(np.sum(coverage)),
                "all_targets_recovered_first": True,
                "recoveries": recoveries,
            }
        )
    field_stack = np.stack(detector_fields)
    signal_stack = np.stack(partial_signals)
    result_profiles = [
        {
            "profile": record["profile"],
            "covered_direction_count": record["covered_direction_count"],
            "all_targets_recovered_first": record["all_targets_recovered_first"],
            "recoveries": record["recoveries"],
        }
        for record in profile_records
    ]
    result = {
        "schema": "kikuchi.ice-ih-virtual-camera-transfer/v1",
        "dictionary": {
            "id": verification.dictionary_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "master_path": master_path.relative_to(ROOT).as_posix(),
            "master_file_sha256": _sha256(master_path),
            "entry_count": verification.entry_count,
            "direction_count": int(len(directions)),
        },
        "orientation_selection": {
            "method": "identity plus most separated sign-invariant cache orientation",
            "entry_indices": targets.tolist(),
            "quaternions_wxyz": quaternions[targets].tolist(),
        },
        "profiles": result_profiles,
        "adapter": {
            "detector_projection": "gnomonic",
            "master_sampling": "bilinear upper/lower stereographic sampling",
            "detector_sampling": "bilinear detector pixel sampling onto fixed sample-frame S2 directions",
            "metric": "masked mean-centered normalized cosine within each profile",
            "cross_profile_score_comparison": "not meaningful; every profile has its own detector field and coverage mask",
        },
        "claim_boundary": (
            "Source-bound virtual-camera transfer proof using detector fields reprojected from the "
            "same canonical Ice Ih master. It is not a commercial-detector model, inter-instrument "
            "calibration, acquired-pattern validation, phase discrimination study, or indexing benchmark."
        ),
    }
    staging = output_root.parent / f".{output_root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_npz(
            staging / "virtual-camera-detector-fields.npz",
            detector_fields=field_stack,
            target_entry_indices=targets.astype(np.int32),
            target_quaternions_wxyz=quaternions[targets].astype(np.float64),
        )
        _write_npz(
            staging / "virtual-camera-partial-s2-signals.npz",
            partial_s2_signals=signal_stack,
            coverage_masks=np.stack([np.asarray(record["coverage_mask"], dtype=bool) for record in profile_records]),
        )
        _write_json(staging / "virtual-camera-transfer.json", result)
        _figure(
            staging / "virtual-camera-transfer.png",
            directions=directions,
            detector_fields=field_stack,
            profile_records=profile_records,
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
    print(f"Virtual-camera transfer: {output_root}")
    print(f"Target entries: {', '.join(str(index) for index in targets)}")
    print(
        "Covered directions: "
        + ", ".join(
            f"{record['profile']['name']}={record['covered_direction_count']}/{len(directions)}"
            for record in profile_records
        )
    )
    print("All profile/target recoveries first: yes")


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
