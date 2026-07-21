#!/usr/bin/env python3
"""Render an honest visual bridge for the current Ice Ih S² dictionary input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from kikuchi_lab.dictionary.ice_ih import verify_ice_ih_candidate_dictionary
from kikuchi_lab.dictionary.signal_space_bridge import (
    publish_signal_space_bridge,
    sample_frame_rays_from_gnomonic,
)
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.projection.kikuchipy_adapter import _to_kikuchipy_detector


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RUN = ROOT / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-signal-space-bridge-v0.1.1"
_DETECTOR_PNG = "products/kinematical-detector.png"
_MASTER_PNG = "products/kinematical-master-stereographic.png"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _declared_source_image(run_root: Path, relative_path: str) -> Path:
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(relative_path), dict):
        raise ValueError(f"source run manifest does not declare {relative_path}")
    source = run_root / relative_path
    declared_sha256 = files[relative_path].get("sha256")
    if not isinstance(declared_sha256, str) or _sha256(source) != declared_sha256:
        raise ValueError(f"source run image hash differs from its run manifest: {relative_path}")
    return source


def _detector_boundary_pixels(shape: tuple[int, int], *, samples_per_edge: int = 96) -> np.ndarray:
    if type(samples_per_edge) is not int or samples_per_edge < 2:
        raise ValueError("samples_per_edge must be an integer of at least two")
    rows, columns = shape
    horizontal = np.linspace(0.0, columns - 1.0, samples_per_edge)
    vertical = np.linspace(0.0, rows - 1.0, samples_per_edge)
    return np.concatenate(
        (
            np.column_stack((np.zeros(samples_per_edge), horizontal)),
            np.column_stack((vertical, np.full(samples_per_edge, columns - 1.0))),
            np.column_stack((np.full(samples_per_edge, rows - 1.0), horizontal[::-1])),
            np.column_stack((vertical[::-1], np.zeros(samples_per_edge))),
        )
    )


def _detector_footprint(recipe_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    recipe = load_kinematical_recipe(recipe_path)
    detector = _to_kikuchipy_detector(recipe.detector)
    pixels = _detector_boundary_pixels(recipe.detector.supersampled_shape)
    gnomonic = np.asarray(detector.to_gnomonic_coords(pixels), dtype=np.float64)
    if gnomonic.ndim == 3 and gnomonic.shape[0] == 1:
        gnomonic = gnomonic[0]
    if gnomonic.shape != pixels.shape:
        raise ValueError("kikuchipy returned an unexpected gnomonic boundary shape")
    matrices = np.asarray(detector.sample_to_detector.to_matrix(), dtype=np.float64).reshape(-1, 3, 3)
    if len(matrices) != 1:
        raise ValueError("signal-space bridge requires one detector geometry")
    footprint = sample_frame_rays_from_gnomonic(gnomonic, matrices[0])
    pc_ray = sample_frame_rays_from_gnomonic(np.zeros((1, 2), dtype=np.float64), matrices[0])[0]
    geometry = {
        "recipe_id": recipe.recipe_id,
        "projection": "gnomonic",
        "pc_convention": recipe.detector.pc_convention,
        "shape": list(recipe.detector.supersampled_shape),
        "pc": [recipe.detector.pcx, recipe.detector.pcy, recipe.detector.pcz],
        "sample_tilt_deg": recipe.detector.sample_tilt_deg,
        "detector_tilt_deg": recipe.detector.detector_tilt_deg,
        "detector_azimuth_deg": recipe.detector.detector_azimuth_deg,
        "detector_twist_deg": recipe.detector.detector_twist_deg,
        "geometry_owner": "kikuchipy.EBSDDetector.to_gnomonic_coords and sample_to_detector",
    }
    return footprint, pc_ray, geometry


def render(dictionary_root: Path, run_root: Path, recipe_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    run_root = run_root.resolve()
    recipe_path = recipe_path.resolve()
    output_root = output_root.resolve()
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache = manifest.get("candidate_cache")
    validation = manifest.get("validation")
    if not isinstance(cache, dict) or not isinstance(validation, dict):
        raise ValueError("Ice Ih package lacks candidate-cache or validation metadata")
    directions = cache.get("directions_path")
    observed = validation.get("observed_fixture")
    if not isinstance(directions, str) or not isinstance(observed, str):
        raise ValueError("Ice Ih package lacks declared S² input files")
    detector = _declared_source_image(run_root, _DETECTOR_PNG)
    master = _declared_source_image(run_root, _MASTER_PNG)
    footprint, pc_ray, geometry = _detector_footprint(recipe_path)
    run_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    if run_manifest["run_identity"].get("recipe_id") != geometry["recipe_id"]:
        raise ValueError("detector recipe differs from the declared source run")
    result = publish_signal_space_bridge(
        output_root=output_root,
        detector_image=detector,
        master_image=master,
        directions_path=dictionary_root / directions,
        observed_signal_path=dictionary_root / observed,
        source_root=ROOT,
        phase_name="Ice Ih average oxygen sublattice",
        dictionary_id=verification.dictionary_id,
        dictionary_manifest_sha256=manifest["manifest_sha256"],
        dictionary_entry_count=verification.entry_count,
        detector_footprint_directions=footprint,
        detector_pc_direction=pc_ray,
        detector_geometry=geometry,
        extra_source_files=(recipe_path,),
    )
    print(f"Signal-space bridge: {result.path}")
    print(f"Manifest SHA-256: {result.manifest_sha256}")
    print("Matcher input: fixed sample-frame S² feature vector; not detector pixels or Hough space.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        render(args.dictionary, args.run, args.recipe, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
