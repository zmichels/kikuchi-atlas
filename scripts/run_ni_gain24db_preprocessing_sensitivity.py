#!/usr/bin/env python3
"""Reproduce the source-bound Ni 24 dB Hough preprocessing sensitivity study.

Run with the pinned optional Hough dependency:

    uv run --with pyebsdindex==0.3.9.2 \
      python scripts/run_ni_gain24db_preprocessing_sensitivity.py
"""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping
from uuid import uuid4

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
from matplotlib import pyplot as plt

import kikuchipy as kp
from diffsims.crystallography import ReciprocalLatticeVector
from orix.crystal_map import PhaseList
from orix.quaternion import Orientation

from kikuchi_lab.reference_pack import (
    load_source_inventory_manifest,
    sha256_file,
    summarize_variant,
    verify_exact_source_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "recipes/reference-pack/ni-gain24db-preprocessing-sensitivity-v0.1.yml"
DEFAULT_OUTPUT = ROOT / "local/reference-packs/ni-gain24db-preprocessing-sensitivity-v0.1"


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: object) -> None:
    _write_bytes(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n",
    )


def _load_recipe(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"preprocessing sensitivity recipe is invalid YAML: {path}") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("preprocessing sensitivity recipe must declare schema_version 1")
    if value.get("id") != "ni-gain24db-preprocessing-sensitivity-v0.1":
        raise ValueError("preprocessing sensitivity recipe id is unexpected")
    variants = value.get("variants")
    if not isinstance(variants, list) or not variants:
        raise ValueError("preprocessing sensitivity recipe variants must be a non-empty list")
    identifiers = [variant.get("id") for variant in variants if isinstance(variant, dict)]
    if identifiers != ["raw", "static-divide", "static-dynamic-divide"]:
        raise ValueError("preprocessing sensitivity recipe variants differ from the declared protocol")
    if value.get("reference_variant") != "static-dynamic-divide":
        raise ValueError("preprocessing sensitivity reference variant is unexpected")
    return value


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _reflectors(phase: object, hough: Mapping[str, Any]) -> ReciprocalLatticeVector:
    reflectors = ReciprocalLatticeVector.from_min_dspacing(
        phase.deepcopy(), float(hough["min_dspacing_nm"])
    )
    reflectors.sanitise_phase()
    reflectors.calculate_structure_factor()
    amplitude = abs(reflectors.structure_factor)
    selected = reflectors[amplitude > float(hough["structure_factor_relative_threshold"]) * amplitude.max()]
    if selected.size != int(hough["expected_reflector_count"]):
        raise ValueError(
            f"selected reflector count {selected.size} != {hough['expected_reflector_count']}"
        )
    return selected


def _verify_expected(summary: Mapping[str, float | int | str], expected: Mapping[str, Any]) -> None:
    for summary_field, expected_field in (("pattern_count", "patterns"), ("indexed_count", "indexed")):
        if int(summary[summary_field]) != int(expected[expected_field]):
            raise ValueError(
                f"{summary['identifier']} {summary_field} {summary[summary_field]} "
                f"!= {expected[expected_field]}"
            )
    for field in (
        "fit_mean",
        "confidence_mean",
        "orientation_delta_mean_deg",
        "orientation_delta_max_deg",
    ):
        if not np.isclose(float(summary[field]), float(expected[field]), rtol=0.0, atol=1e-6):
            raise ValueError(f"{summary['identifier']} {field} {summary[field]} != {expected[field]}")


def _render_study(
    path: Path,
    *,
    runs: list[dict[str, Any]],
    reflectors: ReciprocalLatticeVector,
    nonclaims: list[str],
) -> None:
    figure = plt.figure(figsize=(15.6, 10.6), facecolor="white")
    grid = figure.add_gridspec(2, 3, height_ratios=(1.05, 0.95), hspace=0.35, wspace=0.26)
    figure.suptitle(
        "Ni 24 dB calibration patterns — fixed Hough preprocessing sensitivity",
        fontsize=19,
        fontweight="bold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.945,
        "Same seven acquired patterns, Bruker PC, 50 Ni reflectors, and CPU Hough route; "
        "only preprocessing varies",
        ha="center",
        va="top",
        fontsize=10.3,
        color="#3d4d57",
    )
    for column, run in enumerate(runs):
        axis = figure.add_subplot(grid[0, column])
        pattern = np.asarray(run["calibration"].normalize_intensity(dtype_out="float32", inplace=False).inav[0].data)
        axis.imshow(pattern, cmap="gray", vmin=-3, vmax=3, interpolation="nearest")
        simulation = kp.simulations.KikuchiPatternSimulator(reflectors).on_detector(
            run["detector"], run["xmap"].rotations
        )
        axis.add_collection(
            simulation.as_collections(0, lines_kwargs={"color": "#9ad9ff", "linewidth": 0.7, "alpha": 0.9})[0]
        )
        axis.set_xlim(0, pattern.shape[1] - 1)
        axis.set_ylim(pattern.shape[0] - 1, 0)
        axis.set_axis_off()
        summary = run["summary"]
        axis.set_title(
            f"{summary['identifier']}\nfit {summary['fit_mean']:.3f} · cm {summary['confidence_mean']:.3f}",
            fontsize=11,
            fontweight="bold",
        )

    labels = [run["summary"]["identifier"] for run in runs]
    positions = np.arange(len(runs))
    metrics_axis = figure.add_subplot(grid[1, 0])
    metrics_axis.bar(positions - 0.18, [run["summary"]["fit_mean"] for run in runs], width=0.34, label="mean fit", color="#5e90ad")
    metrics_axis.bar(positions + 0.18, [run["summary"]["confidence_mean"] for run in runs], width=0.34, label="mean confidence", color="#77ad8d")
    metrics_axis.set_ylim(0, 0.9)
    metrics_axis.set_xticks(positions, [label.replace("-", "\n") for label in labels], fontsize=8.8)
    metrics_axis.set_ylabel("Hough aggregate diagnostic")
    metrics_axis.set_title("Aggregate Hough diagnostics", fontweight="bold")
    metrics_axis.grid(axis="y", color="#dce5ea", linewidth=0.7)
    metrics_axis.legend(frameon=False, fontsize=8.8)

    delta_axis = figure.add_subplot(grid[1, 1])
    calibration_index = np.arange(1, len(runs[0]["orientation_delta_deg"]) + 1)
    colors = ("#bd6b73", "#5e90ad", "#77ad8d")
    for run, color in zip(runs, colors, strict=True):
        delta_axis.plot(
            calibration_index,
            run["orientation_delta_deg"],
            marker="o",
            linewidth=1.8,
            markersize=4.6,
            label=run["summary"]["identifier"],
            color=color,
        )
    delta_axis.set_xticks(calibration_index)
    delta_axis.set_xlabel("calibration pattern")
    delta_axis.set_ylabel("symmetry-reduced delta to all-division (deg)")
    delta_axis.set_title("Orientation agreement with reference variant", fontweight="bold")
    delta_axis.grid(color="#dce5ea", linewidth=0.7)
    delta_axis.legend(frameon=False, fontsize=8.2)

    note_axis = figure.add_subplot(grid[1, 2])
    note_axis.set_axis_off()
    note_axis.text(
        0.0,
        1.0,
        "How to read this study",
        transform=note_axis.transAxes,
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
        color="#17232c",
    )
    note_axis.text(
        0.0,
        0.83,
        "• The cyan traces are Hough-derived geometrical simulations.\n"
        "• The reference is static + dynamic background division.\n"
        "• Cubic symmetry is applied before reporting orientation changes.\n"
        "• No result is treated as independently known orientation truth.\n\n"
        "Claim boundary:\n"
        + "\n".join(f"• {claim}" for claim in nonclaims),
        transform=note_axis.transAxes,
        ha="left",
        va="top",
        fontsize=8.9,
        color="#3d4d57",
        linespacing=1.45,
        wrap=True,
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(recipe_path: Path, output_root: Path, *, allow_download: bool) -> Path:
    try:
        import pyebsdindex  # noqa: F401
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "This study requires pyebsdindex. Run with the recipe-pinned command: "
            "uv run --with pyebsdindex==0.3.9.2 "
            "python scripts/run_ni_gain24db_preprocessing_sensitivity.py"
        ) from error
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"sensitivity-study output already exists: {output_root}")
    recipe = _load_recipe(recipe_path)
    reference_pack = _mapping(recipe["reference_pack"], label="reference_pack")
    source = _mapping(recipe["source"], label="source")
    geometry = _mapping(recipe["geometry"], label="geometry")
    hough = _mapping(recipe["hough"], label="hough")
    nonclaims = recipe.get("nonclaims")
    if not isinstance(nonclaims, list) or not all(isinstance(claim, str) for claim in nonclaims):
        raise ValueError("nonclaims must be a list of text")
    baseline_recipe = ROOT / str(reference_pack["baseline_recipe"])
    if sha256_file(baseline_recipe) != reference_pack["baseline_recipe_sha256"]:
        raise ValueError("linked Ni baseline recipe checksum does not match this study recipe")
    gain_number = int(source["gain_number"])
    calibration = kp.data.ni_gain_calibration(
        gain_number,
        allow_download=allow_download,
        lazy=False,
        show_progressbar=False,
    )
    expected_shape = tuple(int(value) for value in source["calibration_shape"])
    if tuple(calibration.data.shape) != expected_shape:
        raise ValueError(f"calibration shape {calibration.data.shape} != declared {expected_shape}")
    source_manifest = load_source_inventory_manifest(ROOT / str(reference_pack["source_inventory"]))
    source_root = Path(calibration.metadata.General.original_filename).parent
    source_verification = verify_exact_source_inventory(source_root, source_manifest)
    master = kp.data.nickel_ebsd_master_pattern_small()
    reflectors = _reflectors(master.phase, hough)
    phase_list = PhaseList(master.phase)
    raw_runs: list[dict[str, Any]] = []
    for variant in recipe["variants"]:
        variant_mapping = _mapping(variant, label="variant")
        work = kp.data.ni_gain_calibration(
            gain_number,
            allow_download=allow_download,
            lazy=False,
            show_progressbar=False,
        )
        static = variant_mapping.get("static_background")
        dynamic = variant_mapping.get("dynamic_background")
        if static is not None:
            work.remove_static_background(str(static))
        if dynamic is not None:
            work.remove_dynamic_background(str(dynamic))
        detector = work.detector.deepcopy()
        detector.pc = np.asarray(geometry["published_hough_pc"], dtype=np.float64)
        indexer = detector.get_indexer(phase_list, reflectors.unique(True))
        xmap = work.hough_indexing(phase_list=phase_list, indexer=indexer, verbose=0)
        raw_runs.append(
            {
                "id": str(variant_mapping["id"]),
                "expected": _mapping(variant_mapping["expected"], label="variant expected"),
                "static_background": static,
                "dynamic_background": dynamic,
                "calibration": work,
                "detector": detector,
                "xmap": xmap,
            }
        )
    reference = next(run for run in raw_runs if run["id"] == recipe["reference_variant"])
    reference_orientation = Orientation(
        np.asarray(reference["xmap"].rotations.data), symmetry=master.phase.point_group
    )
    for run_record in raw_runs:
        orientation = Orientation(
            np.asarray(run_record["xmap"].rotations.data), symmetry=master.phase.point_group
        )
        deltas = orientation.angle_with(reference_orientation, degrees=True)
        xmap = run_record["xmap"]
        summary = summarize_variant(
            identifier=run_record["id"],
            fit=np.asarray(xmap.prop["fit"], dtype=np.float64),
            confidence=np.asarray(xmap.prop["cm"], dtype=np.float64),
            indexed=np.asarray(xmap.is_indexed, dtype=bool),
            symmetry_reduced_orientation_delta_deg=deltas,
        ).as_dict()
        _verify_expected(summary, run_record["expected"])
        run_record["summary"] = summary
        run_record["orientation_delta_deg"] = np.asarray(deltas, dtype=np.float64)
    staging_root = output_root.with_name(f".{output_root.name}.staging-{uuid4().hex}")
    try:
        staging_root.mkdir(parents=True)
        _render_study(
            staging_root / "preprocessing-sensitivity.png",
            runs=raw_runs,
            reflectors=reflectors,
            nonclaims=nonclaims,
        )
        report_runs = []
        for run_record in raw_runs:
            xmap = run_record["xmap"]
            report_runs.append(
                {
                    "id": run_record["id"],
                    "static_background": run_record["static_background"],
                    "dynamic_background": run_record["dynamic_background"],
                    "summary": run_record["summary"],
                    "per_pattern": {
                        "fit": np.asarray(xmap.prop["fit"], dtype=np.float64).tolist(),
                        "confidence": np.asarray(xmap.prop["cm"], dtype=np.float64).tolist(),
                        "symmetry_reduced_orientation_delta_deg": run_record[
                            "orientation_delta_deg"
                        ].tolist(),
                    },
                }
            )
        report = {
            "schema_version": 1,
            "status": "source-bound-preprocessing-sensitivity-reproduced",
            "recipe": {
                "id": recipe["id"],
                "path": recipe_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(recipe_path),
            },
            "reference_pack": {
                "source_inventory_id": source_verification.manifest_id,
                "source_file_count": source_verification.file_count,
                "source_total_bytes": source_verification.total_bytes,
                "linked_baseline_recipe": reference_pack["baseline_recipe"],
                "linked_baseline_recipe_sha256": reference_pack["baseline_recipe_sha256"],
            },
            "runtime": {
                "python": sys.version.split()[0],
                "kikuchipy": version("kikuchipy"),
                "pyebsdindex": version("pyebsdindex"),
                "diffsims": version("diffsims"),
                "orix": version("orix"),
            },
            "protocol": {
                "gain_number": gain_number,
                "calibration_shape": list(calibration.data.shape),
                "hough_pc_bruker": np.asarray(geometry["published_hough_pc"]).tolist(),
                "reflector_count": int(reflectors.size),
                "reference_variant": recipe["reference_variant"],
            },
            "variants": report_runs,
            "nonclaims": nonclaims,
        }
        _write_json(staging_root / "sensitivity.json", report)
        manifest = {
            "schema_version": 1,
            "files": [
                {
                    "path": candidate.relative_to(staging_root).as_posix(),
                    "bytes": candidate.stat().st_size,
                    "sha256": sha256_file(candidate),
                }
                for candidate in sorted(staging_root.rglob("*"))
                if candidate.is_file()
            ],
        }
        _write_json(staging_root / "manifest.json", manifest)
        staging_root.replace(output_root)
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise
    return output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow Kikuchipy to download source data absent from the user cache",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = run(args.recipe, args.output, allow_download=args.allow_download)
    report = json.loads((output / "sensitivity.json").read_text(encoding="utf-8"))
    summaries = [variant["summary"] for variant in report["variants"]]
    print(
        "Ni preprocessing sensitivity reproduced "
        + " ".join(
            f"{summary['identifier']}:fit={summary['fit_mean']:.6f},cm={summary['confidence_mean']:.6f}"
            for summary in summaries
        )
        + f" output={output}"
    )


if __name__ == "__main__":
    main()
