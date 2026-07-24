#!/usr/bin/env python3
"""Fetch (when allowed) and verify the lightweight Ni 24 dB Reference Pack.

This command deliberately retains source data in the Kikuchipy cache rather
than copying the 100+ MB acquired source into this repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import kikuchipy as kp

from kikuchi_lab.reference_pack import (
    SourceInventoryVerification,
    load_source_inventory_manifest,
    sha256_file,
    verify_exact_source_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reference-packs/ni-gain24db-calibration-hough-v0.1.source-inventory.json"


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"reference-pack manifest is not valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError("reference-pack manifest must be a JSON object")
    return value


def _verify_recipe(document: Mapping[str, Any]) -> tuple[str, str]:
    recipe = document.get("recipe")
    if not isinstance(recipe, Mapping):
        raise ValueError("reference-pack manifest recipe must be a mapping")
    relative_path = recipe.get("path")
    expected_sha256 = recipe.get("sha256")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("reference-pack manifest recipe path must be a non-empty string")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("reference-pack manifest recipe sha256 must be a SHA-256 digest")
    recipe_path = (ROOT / relative_path).resolve()
    if not recipe_path.is_relative_to(ROOT):
        raise ValueError("reference-pack recipe path must remain inside the repository")
    if not recipe_path.is_file():
        raise ValueError(f"reference-pack recipe does not exist: {relative_path}")
    actual_sha256 = sha256_file(recipe_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"reference-pack recipe checksum mismatch for {relative_path}: "
            f"{actual_sha256} != {expected_sha256}"
        )
    return relative_path, actual_sha256


def verify(*, manifest_path: Path, allow_download: bool) -> tuple[SourceInventoryVerification, str]:
    """Load named upstream sources and verify their exact cached inventory."""
    manifest_path = manifest_path.resolve()
    document = _load_document(manifest_path)
    source = document.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("reference-pack manifest source must be a mapping")
    gain_number = source.get("gain_number")
    if not isinstance(gain_number, int) or isinstance(gain_number, bool):
        raise ValueError("reference-pack source gain_number must be an integer")
    manifest = load_source_inventory_manifest(manifest_path)
    recipe_path, _ = _verify_recipe(document)
    acquisition = kp.data.ni_gain(
        gain_number,
        allow_download=allow_download,
        lazy=True,
        show_progressbar=False,
    )
    calibration = kp.data.ni_gain_calibration(
        gain_number,
        allow_download=allow_download,
        lazy=False,
        show_progressbar=False,
    )
    acquisition_source = Path(acquisition.metadata.General.original_filename)
    calibration_source = Path(calibration.metadata.General.original_filename)
    if acquisition_source.parent != calibration_source.parent:
        raise ValueError("Ni acquisition and calibration loaders resolved to different source directories")
    result = verify_exact_source_inventory(acquisition_source.parent, manifest)
    return result, recipe_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow Kikuchipy to fetch missing CC BY source files into its user cache",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result, recipe_path = verify(manifest_path=args.manifest, allow_download=args.allow_download)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"verification failed: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "verified",
                "source_inventory_id": result.manifest_id,
                "source_directory": str(result.source_root),
                "file_count": result.file_count,
                "total_bytes": result.total_bytes,
                "recipe": recipe_path,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
