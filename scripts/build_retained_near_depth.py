#!/usr/bin/env python3
"""Render a near-depth bundle from an already-published kinematical master.

This deliberately reconstructs only the reflector geometry needed for the
presentation layer.  It validates and reuses the immutable stored
two-hemisphere master rather than calculating diffraction a second time.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from kikuchipy.simulations import KikuchiPatternSimulator

from kikuchi_lab.kinematical.contracts import KinematicalArrayProduct
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _enumerate_reflectors,
    _phase_from_record,
    _product_metadata,
    _select_reflectors,
)
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.near_depth.bundle import write_near_depth_bundle
from kikuchi_lab.near_depth.overlap import compute_overlap_field
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe
from kikuchi_lab.near_depth.render import render_near_depth, render_quiet_control
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-recipe", type=Path, required=True)
    parser.add_argument("--treatment-recipe", type=Path, required=True)
    parser.add_argument("--kinematical-run", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--figure-size", type=int)
    return parser.parse_args()


def _stored_master(
    run: Path,
    *,
    base_recipe: object,
    source: object,
) -> KinematicalArrayProduct:
    """Load one raw master and bind it to the exact stored run identity."""
    manifest_path = run / "manifest.json"
    master_path = run / "products" / "kinematical-master-stereographic.npy"
    saved_recipe_path = run / "recipes" / "kinematical.json"
    if not manifest_path.is_file() or not master_path.is_file() or not saved_recipe_path.is_file():
        raise FileNotFoundError("kinematical run lacks manifest, saved recipe, or master array")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    saved_recipe = json.loads(saved_recipe_path.read_text(encoding="utf-8"))
    if saved_recipe != base_recipe.to_dict():
        raise ValueError("stored kinematical recipe differs from the requested base recipe")
    try:
        expected = manifest["run_identity"]["products"]["master-stereographic"]
    except (KeyError, TypeError) as error:
        raise ValueError("kinematical manifest lacks master product identity") from error
    master = np.load(master_path, allow_pickle=False)
    product = KinematicalArrayProduct.from_array(
        "master-stereographic",
        master,
        metadata=_product_metadata(
            source,
            base_recipe,
            projection="stereographic",
            intensity_meaning="kinematical band intensity proportional to |F_hkl|^2",
        ),
    )
    if product.product_id != expected.get("product_id"):
        raise ValueError("stored master product identity does not verify")
    if product.array_sha256 != expected.get("array_sha256"):
        raise ValueError("stored master array checksum does not verify")
    return product


def main() -> None:
    args = _args()
    base_file = args.base_recipe.resolve()
    treatment_file = args.treatment_recipe.resolve()
    run = args.kinematical_run.resolve()
    base = load_kinematical_recipe(base_file)
    treatment = load_near_depth_recipe(treatment_file)
    if treatment.expected_kinematical_recipe_id != base.recipe_id:
        raise ValueError("near-depth treatment does not match the requested base recipe")
    expected_base = (treatment_file.parent / treatment.source_kinematical_recipe).resolve()
    if expected_base != base_file:
        raise ValueError("near-depth treatment references a different base recipe path")
    source = load_structure_record((base_file.parent / base.source_record).resolve())
    verify_structure(source)
    master = _stored_master(run, base_recipe=base, source=source)
    projection_ledger_path = run / "diagnostics" / "projection-ledger.json"
    if not projection_ledger_path.is_file():
        raise FileNotFoundError("kinematical run lacks its projection ledger")
    projection_ledger = json.loads(projection_ledger_path.read_text(encoding="utf-8"))

    reflectors = _enumerate_reflectors(_phase_from_record(source), base)
    master_reflectors = _select_reflectors(
        reflectors, base.master_relative_factor, base.energy_kev
    )
    context = SimpleNamespace(
        master_simulator=KikuchiPatternSimulator(master_reflectors),
        overlay_simulators={
            style.name: KikuchiPatternSimulator(
                _select_reflectors(
                    reflectors, style.overlay_relative_factor, base.energy_kev
                )
            )
            for style in base.styles
        },
    )
    simulation = SimpleNamespace(
        master_stereographic=master,
        projection_ledger=projection_ledger,
    )
    overlap = compute_overlap_field(
        context.master_simulator.reflectors,
        size=master.intensity.shape[-1],
        relative_factor=treatment.overlap_relative_factor,
        weight_exponent=treatment.weight_exponent,
        normalization_percentile=treatment.normalization_percentile,
    )
    effective_size = treatment.figure_size_px if args.figure_size is None else args.figure_size
    quiet = render_quiet_control(
        context, simulation, base, figure_size_px=effective_size
    )
    render = render_near_depth(
        context,
        simulation,
        base,
        treatment,
        overlap,
        quiet,
        figure_size_px=effective_size,
    )
    bundle = write_near_depth_bundle(
        args.output_root.resolve(),
        render,
        overlap,
        simulation,
        treatment,
        base,
        source,
    )
    print(
        json.dumps(
            {
                "run_id": bundle.run_id,
                "path": str(bundle.path),
                "base_recipe_id": base.recipe_id,
                "treatment_recipe_id": treatment.recipe_id,
                "master_reflector_count": int(master_reflectors.size),
                "overlap_signed_reflector_count": int(
                    np.count_nonzero(
                        np.abs(context.master_simulator.reflectors.structure_factor)
                        >= treatment.overlap_relative_factor
                        * np.abs(context.master_simulator.reflectors.structure_factor).max()
                    )
                ),
                "master_reused": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
