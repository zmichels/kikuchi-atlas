#!/usr/bin/env python3
"""Build the verified Ice Ih spherical candidate dictionary from its checked master."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import yaml

from kikuchi_lab.dictionary.ice_ih import publish_ice_ih_candidate_dictionary
from kikuchi_lab.model.identity import stable_id


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "recipes/dictionaries/ice-ih-spherical-candidate-v0.1.3.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _relative_path(recipe_path: Path, value: object, name: str) -> Path:
    text = _text(value, name)
    path = Path(text)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative to the recipe")
    resolved = (recipe_path.parent / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"{name} escapes the repository")
    return resolved


def _positive_number(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
    ):
        raise ValueError(f"{name} must be a positive number")
    return float(value)


def build(recipe_path: Path, output_root: Path) -> None:
    recipe_path = recipe_path.resolve()
    recipe = _mapping(yaml.safe_load(recipe_path.read_text(encoding="utf-8")), "recipe")
    required = {
        "schema_version",
        "name",
        "dictionary_version",
        "created_at",
        "authors",
        "phase_source",
        "source_master",
        "sampling",
        "claim_boundary",
    }
    optional = {"synthetic_recovery"}
    if (
        not required <= set(recipe)
        or not set(recipe) <= required | optional
        or recipe["schema_version"] != 1
    ):
        raise ValueError("Ice Ih dictionary recipe fields or schema_version differ from version 1")
    if recipe["name"] != "ice-ih-spherical-candidate":
        raise ValueError("Ice Ih dictionary recipe name is unexpected")

    source_path = _relative_path(recipe_path, recipe["phase_source"], "phase_source")
    source_record = _mapping(
        yaml.safe_load(source_path.read_text(encoding="utf-8")), "phase source"
    )
    phase = _mapping(source_record.get("phase"), "phase source.phase")
    if phase.get("name") != "ice-Ih-oxygen-sublattice" or phase.get("space_group_number") != 194:
        raise ValueError("Ice Ih dictionary requires the checked average oxygen-sublattice source")
    if phase.get("setting") != "P 63/m m c":
        raise ValueError("Ice Ih dictionary requires the P 63/m m c source setting")
    source_sha256 = _text(source_record.get("sha256"), "phase source.sha256")

    source_master = _mapping(recipe["source_master"], "source_master")
    if set(source_master) != {"path", "sha256", "run_manifest", "run_manifest_sha256"}:
        raise ValueError("source_master fields differ from the dictionary recipe contract")
    master_path = _relative_path(recipe_path, source_master["path"], "source_master.path")
    manifest_path = _relative_path(
        recipe_path, source_master["run_manifest"], "source_master.run_manifest"
    )
    if _sha256(master_path) != _text(source_master["sha256"], "source_master.sha256"):
        raise ValueError("source master SHA-256 differs from recipe")
    if _sha256(manifest_path) != _text(source_master["run_manifest_sha256"], "run_manifest_sha256"):
        raise ValueError("source run manifest SHA-256 differs from recipe")
    run_manifest = _mapping(
        json.loads(manifest_path.read_text(encoding="utf-8")), "source run manifest"
    )
    master_file = _mapping(run_manifest.get("files"), "source run manifest.files").get(
        "products/kinematical-master-stereographic.npy"
    )
    if not isinstance(master_file, dict) or master_file.get("sha256") != source_master["sha256"]:
        raise ValueError("source run manifest does not bind to the requested stereographic master")
    run_identity = _mapping(run_manifest.get("run_identity"), "source run manifest.run_identity")
    products = _mapping(run_identity.get("products"), "source run manifest.run_identity.products")
    master_product = _mapping(products.get("master-stereographic"), "source run master product")
    if run_identity.get("source_sha256") != source_sha256:
        raise ValueError("source run manifest does not bind to the checked Ice Ih phase source")

    sampling = _mapping(recipe["sampling"], "sampling")
    orientation = _mapping(sampling.get("orientation"), "sampling.orientation")
    directions = _mapping(sampling.get("directions"), "sampling.directions")
    if orientation.get("symmetry") != "6/mmm" or orientation.get("method") != "cubochoric":
        raise ValueError("Ice Ih dictionary orientation sampling must be 6/mmm cubochoric")
    if directions.get("method") != "spherified_cube_edge":
        raise ValueError("Ice Ih dictionary direction sampling must be spherified_cube_edge")
    if sampling.get("master_interpolation") != "bilinear-upper-owns-equator":
        raise ValueError("Ice Ih dictionary master interpolation policy differs from contract")
    if sampling.get("candidate_preprocessing") != "per-row-mean-center-and-l2-normalize":
        raise ValueError("Ice Ih dictionary preprocessing policy differs from contract")
    synthetic_recovery = recipe.get("synthetic_recovery")
    if synthetic_recovery is not None:
        synthetic_recovery = _mapping(synthetic_recovery, "synthetic_recovery")
    authors = recipe["authors"]
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(value, str) for value in authors)
    ):
        raise ValueError("authors must be a non-empty text list")
    master = np.load(master_path, allow_pickle=False)
    result = publish_ice_ih_candidate_dictionary(
        output_root=output_root,
        master=master,
        master_array_sha256=hashlib.sha256(
            np.ascontiguousarray(master, dtype=np.float32).tobytes()
        ).hexdigest(),
        source={
            "phase_source_id": _text(
                run_identity.get("source_id"), "source run manifest.source_id"
            ),
            "phase_source_sha256": source_sha256,
            "phase_source_uri": _text(source_record.get("uri"), "source.uri"),
            "structural_citation": _text(source_record.get("citation"), "source.citation"),
            "kinematical_recipe_id": _text(
                run_identity.get("recipe_id"), "source run manifest.recipe_id"
            ),
            "master_product_id": _text(
                master_product.get("product_id"), "source run master product.product_id"
            ),
            "energy_kev": 20.0,
        },
        recipe={
            "recipe_id": stable_id("dictionary-recipe", recipe),
            "schema_version": recipe["schema_version"],
            "name": recipe["name"],
            "sampling": sampling,
            "synthetic_recovery": synthetic_recovery,
            "claim_boundary": _text(recipe["claim_boundary"], "claim_boundary"),
            "source_run_id": _text(run_manifest.get("run_id"), "source run manifest.run_id"),
            "source_master_file_sha256": _text(source_master["sha256"], "source_master.sha256"),
            "source_run_manifest_sha256": _text(
                source_master["run_manifest_sha256"], "run_manifest_sha256"
            ),
        },
        dictionary_version=_text(recipe["dictionary_version"], "dictionary_version"),
        created_at=_text(recipe["created_at"], "created_at"),
        authors=tuple(authors),
        orientation_resolution_degrees=_positive_number(
            orientation.get("nominal_spacing_degrees"),
            "sampling.orientation.nominal_spacing_degrees",
        ),
        direction_resolution_degrees=_positive_number(
            directions.get("nominal_spacing_degrees"), "sampling.directions.nominal_spacing_degrees"
        ),
        synthetic_recovery=synthetic_recovery,
    )
    print(f"Published {result.dictionary_id}")
    print(f"Path: {result.path}")
    print(f"Manifest SHA-256: {result.manifest_sha256}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        build(args.recipe, args.output.resolve())
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
