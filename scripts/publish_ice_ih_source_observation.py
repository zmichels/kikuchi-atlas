#!/usr/bin/env python3
"""Package the checked simulated Ice Ih detector field as an explicit observation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from kikuchi_lab.dictionary.ice_ih import verify_ice_ih_candidate_dictionary
from kikuchi_lab.dictionary.observation import (
    publish_detector_observation_package,
    verify_detector_observation_package,
)
from kikuchi_lab.kinematical import load_kinematical_recipe


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
DEFAULT_SOURCE_DETECTOR = (
    ROOT
    / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
    / "products/kinematical-detector.npy"
)
DEFAULT_OUTPUT = ROOT / "local/observations/ice-ih-source-detector-identity-v0.1.0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(dictionary_root: Path, recipe_path: Path, detector_path: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    recipe_path = recipe_path.resolve()
    detector_path = detector_path.resolve()
    output_root = output_root.resolve()
    verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    directions = np.load(
        dictionary_root / manifest["candidate_cache"]["directions_path"], allow_pickle=False
    )
    detector = np.load(detector_path, allow_pickle=False)
    recipe = load_kinematical_recipe(recipe_path)
    result = publish_detector_observation_package(
        output_root=output_root,
        detector_intensity=detector,
        directions=directions,
        detector=recipe.detector,
        source={
            "kind": "simulated-kinematical-detector",
            "id": "kinematical-ice/kinematical-run-8e0fa453f0869a21",
            "sha256": _sha256(detector_path),
        },
        observation_version="0.1.0",
        created_at="2026-07-22T00:00:00Z",
        authors=("Kikuchi Atlas",),
    )
    checked = verify_detector_observation_package(result.path)
    if checked.direction_count != len(directions):
        raise ValueError("observation direction count differs from the source dictionary grid")
    print(f"Ice Ih detector observation: {result.path}")
    print(f"Observation ID: {result.observation_id}")
    print(f"Covered directions: {checked.covered_direction_count}/{checked.direction_count}")


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
