#!/usr/bin/env python3
"""Build the compact, provenance-bound forsterite spherical dictionary fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import yaml

from kikuchi_lab.dictionary import OrientationEntry, downsample_to_cube_shell, publish_spherical_dictionary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "recipes/dictionaries/forsterite-spherical-fixture.yml"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/forsterite-spherical-fixture-v0.1.0"


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


def _relative_path(recipe_path: Path, value: object, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative to the recipe")
    resolved = (recipe_path.parent / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"{name} escapes the repository")
    return resolved


def _relative_to_root(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _required_text(mapping: dict[str, Any], name: str) -> str:
    value = mapping.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"recipe {name} must be non-empty text")
    return value


def build(recipe_path: Path, output_root: Path) -> None:
    recipe_path = recipe_path.resolve()
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    recipe = _mapping(raw, "recipe")
    if recipe.get("schema_version") != 1:
        raise ValueError("dictionary fixture recipe schema_version must be 1")
    if recipe.get("name") != "forsterite-spherical-fixture":
        raise ValueError("dictionary fixture recipe name is unexpected")

    source_field = _mapping(recipe.get("source_spherical_field"), "source_spherical_field")
    npz_path = _relative_path(recipe_path, source_field.get("npz"), "source_spherical_field.npz")
    ledger_path = _relative_path(recipe_path, source_field.get("ledger"), "source_spherical_field.ledger")
    if _sha256(npz_path) != _required_text(source_field, "npz_sha256"):
        raise ValueError("source spherical NPZ SHA-256 differs from recipe")
    if _sha256(ledger_path) != _required_text(source_field, "ledger_sha256"):
        raise ValueError("source spherical ledger SHA-256 differs from recipe")
    ledger = _mapping(json.loads(ledger_path.read_text(encoding="utf-8")), "source ledger")
    field_id = _required_text(source_field, "field_id")
    if ledger.get("field_id") != field_id:
        raise ValueError("source spherical ledger field_id differs from recipe")

    phase_path = _relative_path(recipe_path, recipe.get("phase_source"), "phase_source")
    phase_source = _mapping(yaml.safe_load(phase_path.read_text(encoding="utf-8")), "phase source")
    phase = _mapping(phase_source.get("phase"), "phase source.phase")
    source_sha256 = _required_text(phase_source, "sha256")
    ledger_metadata = _mapping(ledger.get("metadata"), "source ledger metadata")
    ledger_source = ledger_metadata.get("source")
    ledger_source = _mapping(ledger_source, "source ledger metadata.source")
    if ledger_source.get("source_sha256") != source_sha256:
        raise ValueError("source spherical ledger does not bind to the tracked phase structure")

    sampling = _mapping(recipe.get("sampling"), "sampling")
    if sampling != {
        "topology": "normalized-cube-shell-26",
        "method": "nearest-direction",
        "interpolation": "none",
        "spatial_filter": "none",
    }:
        raise ValueError("fixture sampling must remain the documented no-filter cube-shell policy")
    intensity_channel = _required_text(source_field, "intensity_channel")
    if intensity_channel != "intensity_raw":
        raise ValueError("fixture must preserve the raw source intensity channel")
    with np.load(npz_path, allow_pickle=False) as archive:
        directions, intensity, max_error_deg = downsample_to_cube_shell(
            archive["xyz"],
            archive[intensity_channel],
        )

    orientations = _mapping(recipe.get("orientations"), "orientations")
    if orientations.get("convention") != "active-wxyz-crystal-to-sample":
        raise ValueError("fixture requires the active wxyz crystal-to-sample convention")
    raw_entries = orientations.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("orientations.entries must be a list")
    entries = tuple(
        OrientationEntry(
            _required_text(_mapping(value, "orientation entry"), "id"),
            tuple(_mapping(value, "orientation entry")["quaternion_wxyz"]),
        )
        for value in raw_entries
    )
    validation = _mapping(recipe.get("validation"), "validation")
    validation_entry_id = _required_text(validation, "observed_entry_id")

    target_setting = _mapping(phase_source.get("simulation_setting"), "simulation_setting").get(
        "target_setting"
    )
    if not isinstance(target_setting, str) or not target_setting:
        raise ValueError("forsterite source record requires simulation_setting.target_setting")
    source_frame = _mapping(ledger_metadata.get("frame"), "source ledger metadata.frame")
    source_phase = _mapping(ledger_metadata.get("phase"), "source ledger metadata.phase")
    lattice = phase.get("lattice_angstrom")
    if not isinstance(lattice, list) or len(lattice) != 6:
        raise ValueError("forsterite phase source requires six lattice parameters")
    authors = recipe.get("authors")
    if not isinstance(authors, list) or not all(isinstance(author, str) for author in authors):
        raise ValueError("dictionary recipe authors must be a non-empty text list")
    result = publish_spherical_dictionary(
        output_root=output_root,
        dictionary_name=_required_text(recipe, "name"),
        phase={
            "name": _required_text(phase, "name"),
            "formula": _required_text(phase, "formula"),
            "space_group_number": phase.get("space_group_number"),
            "setting": target_setting,
            "source_setting": _required_text(phase, "setting"),
            "source_structure_id": _required_text(phase_source, "identifier"),
            "crystal_system": "orthorhombic",
            "point_group": source_phase.get("point_group"),
            "lattice_parameters": {"values": lattice, "units": "angstrom, degree"},
            "symmetry_operators": "standard space-group 62 Pnma setting",
            "reference_frame": source_frame,
            "setting_notes": _required_text(_mapping(phase_source.get("simulation_setting"), "simulation_setting"), "reason"),
        },
        source={
            "kind": "spherical-scalar-field",
            "source_field_id": field_id,
            "source_file": _relative_to_root(npz_path),
            "source_file_sha256": _required_text(source_field, "npz_sha256"),
            "source_ledger": _relative_to_root(ledger_path),
            "source_ledger_sha256": _required_text(source_field, "ledger_sha256"),
            "source_structure_sha256": source_sha256,
            "source_structure_uri": _required_text(phase_source, "uri"),
            "intensity_channel": intensity_channel,
            "generation_physics": {
                "generation_method": "kinematical master-pattern S2 field",
                "software_name": "kikuchi-lab / ebsdsim",
                "accelerating_voltage_kv": ledger_source.get("energy_kev"),
                "master_pattern_product_id": ledger_source.get("product_id"),
                "postprocessing_steps": "nearest-direction downsample only; no smoothing or blur",
            },
            "downsampling": {
                "method": "nearest-direction",
                "maximum_angular_error_degrees": max_error_deg,
                "interpolation": "none",
                "spatial_filter": "none",
            },
        },
        recipe={
            "schema_version": recipe["schema_version"],
            "name": recipe["name"],
            "sampling": sampling,
            "orientation_convention": orientations["convention"],
            "claim_boundary": _required_text(recipe, "claim_boundary"),
        },
        canonical_directions=directions,
        canonical_signal=intensity,
        entries=entries,
        validation_entry_id=validation_entry_id,
        license_id=_required_text(recipe, "license"),
        citation_text=_required_text(phase_source, "citation"),
        dictionary_version=_required_text(recipe, "dictionary_version"),
        created_at=_required_text(recipe, "created_at"),
        authors=tuple(authors),
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
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
