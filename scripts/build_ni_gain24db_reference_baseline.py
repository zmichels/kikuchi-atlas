#!/usr/bin/env python3
"""Build a source-bound Ni gain 24 dB calibration-pattern Hough baseline.

Run with the optional Hough dependency pinned by the recipe:

    uv run --with pyebsdindex==0.3.9.2 \
      python scripts/build_ni_gain24db_reference_baseline.py
"""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
from matplotlib import pyplot as plt

import kikuchipy as kp
from diffsims.crystallography import ReciprocalLatticeVector
from orix.crystal_map import PhaseList


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "recipes/reference-pack/ni-gain24db-calibration-hough-v0.1.yml"
DEFAULT_OUTPUT = ROOT / "local/reference-packs/ni-gain24db-calibration-hough-v0.1"


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
    _write_bytes(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n",
    )


def _load_recipe(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"reference-pack recipe {path} must be a mapping")
    if value.get("schema_version") != 1:
        raise ValueError("reference-pack recipe must declare schema_version 1")
    return value


def _source_inventory(root: Path) -> list[dict[str, object]]:
    if not root.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {root}")
    records: list[dict[str, object]] = []
    for path in sorted(candidate for candidate in root.iterdir() if candidate.is_file()):
        records.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    if not records:
        raise ValueError(f"source directory contains no files: {root}")
    return records


def _reflectors(phase: object, recipe: dict[str, object]) -> ReciprocalLatticeVector:
    hough = recipe["hough"]
    if not isinstance(hough, dict):
        raise ValueError("recipe hough section must be a mapping")
    min_dspacing = float(hough["min_dspacing_nm"])
    threshold = float(hough["structure_factor_relative_threshold"])
    reflectors = ReciprocalLatticeVector.from_min_dspacing(phase.deepcopy(), min_dspacing)
    reflectors.sanitise_phase()
    reflectors.calculate_structure_factor()
    amplitude = abs(reflectors.structure_factor)
    selected = reflectors[amplitude > threshold * amplitude.max()]
    if selected.size != int(hough["expected_reflector_count"]):
        raise ValueError(
            "selected reflector count does not match the declared source-bound "
            f"baseline: {selected.size} != {hough['expected_reflector_count']}"
        )
    return selected


def _render_baseline(
    path: Path,
    *,
    calibration: object,
    detector: object,
    reflectors: ReciprocalLatticeVector,
    xmap: object,
    result: dict[str, float | int],
) -> None:
    normalized = calibration.normalize_intensity(dtype_out="float32", inplace=False)
    simulation = kp.simulations.KikuchiPatternSimulator(reflectors).on_detector(
        detector, xmap.rotations
    )
    figure, axes = plt.subplots(3, 3, figsize=(12.6, 13.2))
    figure.subplots_adjust(
        left=0.035,
        right=0.965,
        top=0.925,
        bottom=0.045,
        wspace=0.055,
        hspace=0.075,
    )
    figure.suptitle(
        "Ni 24 dB gain dataset: calibration-pattern Hough baseline",
        fontsize=18,
        fontweight="bold",
        y=0.972,
    )
    figure.text(
        0.5,
        0.947,
        "Source-bound Bruker PC from the upstream hybrid-indexing tutorial · "
        "white traces are Hough-indexed geometrical simulations",
        ha="center",
        va="top",
        fontsize=9.8,
        color="#3d4d57",
    )
    for index, axis in enumerate(axes.flat):
        axis.set_axis_off()
        if index >= xmap.size:
            continue
        pattern = np.asarray(normalized.inav[index].data)
        axis.imshow(
            pattern,
            cmap="gray",
            vmin=-3,
            vmax=3,
            interpolation="nearest",
        )
        axis.add_collection(
            simulation.as_collections(
                index, lines_kwargs={"color": "white", "linewidth": 0.7, "alpha": 0.9}
            )[0]
        )
        axis.set_xlim(0, pattern.shape[1] - 1)
        axis.set_ylim(pattern.shape[0] - 1, 0)
        axis.text(
            0.025,
            0.965,
            f"cal {index}  fit {float(xmap.prop['fit'][index]):.3f}  "
            f"cm {float(xmap.prop['cm'][index]):.3f}",
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="white",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#16222a", "alpha": 0.74},
        )
    figure.text(
        0.5,
        0.008,
        f"{result['indexed']}/{result['patterns']} calibration patterns indexed · "
        f"mean fit {result['fit_mean']:.6f} · mean confidence {result['confidence_mean']:.6f}",
        ha="center",
        va="bottom",
        fontsize=10.3,
        color="#1a2b34",
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def run(recipe_path: Path, output_root: Path, *, allow_download: bool) -> Path:
    try:
        import pyebsdindex  # noqa: F401
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "This baseline requires pyebsdindex. Run with the recipe-pinned command: "
            "uv run --with pyebsdindex==0.3.9.2 "
            "python scripts/build_ni_gain24db_reference_baseline.py"
        ) from error

    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(
            f"reference baseline output already exists: {output_root}; use a new output path"
        )
    recipe = _load_recipe(recipe_path)
    source = recipe["source"]
    phase_record = recipe["phase"]
    geometry = recipe["geometry"]
    processing = recipe["processing"]
    hough = recipe["hough"]
    nonclaims = recipe["nonclaims"]
    if not all(
        isinstance(value, dict) for value in (source, phase_record, geometry, processing, hough)
    ):
        raise ValueError("source, phase, geometry, processing, and hough must be mappings")
    if not isinstance(nonclaims, list):
        raise ValueError("nonclaims must be a list")

    acquisition = source["acquisition"]
    calibration_source = source["calibration"]
    if not isinstance(acquisition, dict) or not isinstance(calibration_source, dict):
        raise ValueError("source acquisition and calibration records must be mappings")
    acquisition_number = int(acquisition["kwargs"]["number"])
    calibration_number = int(calibration_source["kwargs"]["number"])
    if acquisition_number != calibration_number:
        raise ValueError("source acquisition and calibration must refer to the same gain number")

    acquisition_signal = kp.data.ni_gain(
        acquisition_number,
        allow_download=allow_download,
        lazy=True,
        show_progressbar=False,
    )
    calibration = kp.data.ni_gain_calibration(
        calibration_number,
        allow_download=allow_download,
        lazy=False,
        show_progressbar=False,
    )
    master = kp.data.nickel_ebsd_master_pattern_small()
    raw_pattern_path = Path(acquisition_signal.metadata.General.original_filename)
    calibration_settings_path = Path(calibration.metadata.General.original_filename)
    if raw_pattern_path.parent != calibration_settings_path.parent:
        raise ValueError("Ni acquisition and calibration loaders resolved to different source directories")

    expected_raw_shape = tuple(int(value) for value in acquisition["raw_pattern_shape"])
    expected_calibration_shape = tuple(int(value) for value in calibration_source["raw_pattern_shape"])
    if tuple(acquisition_signal.data.shape) != expected_raw_shape:
        raise ValueError(
            f"acquisition shape {acquisition_signal.data.shape} != declared {expected_raw_shape}"
        )
    if tuple(calibration.data.shape) != expected_calibration_shape:
        raise ValueError(
            f"calibration shape {calibration.data.shape} != declared {expected_calibration_shape}"
        )

    calibration_processing = processing["calibration_patterns"]
    if not isinstance(calibration_processing, dict):
        raise ValueError("calibration pattern processing must be a mapping")
    calibration.remove_static_background(str(calibration_processing["static_background"]))
    calibration.remove_dynamic_background(str(calibration_processing["dynamic_background"]))

    reflectors = _reflectors(master.phase, recipe)
    detector = calibration.detector.deepcopy()
    detector.pc = np.asarray(geometry["published_hough_pc"], dtype=np.float64)
    phase_list = PhaseList(master.phase)
    indexer = detector.get_indexer(phase_list, reflectors.unique(True))
    xmap = calibration.hough_indexing(phase_list=phase_list, indexer=indexer, verbose=0)
    indexed = xmap["indexed"]
    result: dict[str, float | int] = {
        "patterns": int(xmap.size),
        "indexed": int(indexed.size),
        "fraction_indexed": float(indexed.size / xmap.size),
        "fit_mean": float(xmap.prop["fit"].mean()),
        "confidence_mean": float(xmap.prop["cm"].mean()),
        "reflector_count": int(reflectors.size),
    }
    expected_fields = {
        "patterns": int(hough["expected_calibration_count"]),
        "indexed": int(hough["expected_indexed_count"]),
        "reflector_count": int(hough["expected_reflector_count"]),
    }
    for field, expected in expected_fields.items():
        if result[field] != expected:
            raise ValueError(f"baseline {field} {result[field]} != expected {expected}")
    for field in ("fit_mean", "confidence_mean"):
        expected = float(hough[f"expected_{field}"])
        if not np.isclose(float(result[field]), expected, rtol=0.0, atol=1e-7):
            raise ValueError(f"baseline {field} {result[field]} != expected {expected}")

    staging_root = output_root.with_name(f".{output_root.name}.staging-{uuid4().hex}")
    try:
        staging_root.mkdir(parents=True)
        _render_baseline(
            staging_root / "calibration-hough-baseline.png",
            calibration=calibration,
            detector=detector,
            reflectors=reflectors,
            xmap=xmap,
            result=result,
        )
        source_inventory = _source_inventory(raw_pattern_path.parent)
        report = {
            "schema_version": 1,
            "status": "source-bound-baseline-reproduced",
            "recipe": {
                "path": str(recipe_path.relative_to(ROOT)),
                "sha256": _sha256(recipe_path),
                "id": recipe["id"],
            },
            "runtime": {
                "python": sys.version.split()[0],
                "kikuchipy": version("kikuchipy"),
                "pyebsdindex": version("pyebsdindex"),
                "diffsims": version("diffsims"),
                "orix": version("orix"),
            },
            "source": {
                "acquisition_loader": acquisition["loader"],
                "calibration_loader": calibration_source["loader"],
                "gain_number": acquisition_number,
                "zenodo_doi": acquisition["zenodo_doi"],
                "license": acquisition["license"],
                "raw_pattern_path": raw_pattern_path.name,
                "source_inventory": source_inventory,
                "detector": acquisition["detector"],
                "beam_energy_keV": acquisition["beam_energy_keV"],
            },
            "phase_and_master": {
                "name": phase_record["name"],
                "space_group": phase_record["space_group"],
                "master_loader": phase_record["master"]["loader"],
                "master_energy_keV": phase_record["master"]["energy_keV"],
                "master_shape": list(master.data.shape),
                "master_dtype": str(master.data.dtype),
                "master_projection": master.projection,
                "master_origin": phase_record["master"]["origin"],
            },
            "observation": {
                "acquisition_shape": list(acquisition_signal.data.shape),
                "calibration_shape": list(calibration.data.shape),
                "calibration_indices": calibration.original_metadata.calibration_patterns.indices.tolist(),
                "detector_pc_bruker": detector.pc_flattened.tolist(),
                "detector_sample_tilt_deg": float(detector.sample_tilt),
                "raw_metadata_limit": geometry["raw_metadata_limit"],
            },
            "processing": calibration_processing,
            "hough_result": result,
            "nonclaims": nonclaims,
        }
        _write_json(staging_root / "baseline.json", report)
        manifest = {
            "schema_version": 1,
            "files": [
                {
                    "path": path.relative_to(staging_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in sorted(candidate for candidate in staging_root.rglob("*") if candidate.is_file())
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
        help="allow kikuchipy to download source data that is absent from the local cache",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = run(args.recipe, args.output, allow_download=args.allow_download)
    report = json.loads((output / "baseline.json").read_text(encoding="utf-8"))
    result = report["hough_result"]
    print(
        "Ni source-bound baseline reproduced "
        f"indexed={result['indexed']}/{result['patterns']} "
        f"fit={result['fit_mean']:.6f} confidence={result['confidence_mean']:.6f} "
        f"output={output}"
    )


if __name__ == "__main__":
    main()
